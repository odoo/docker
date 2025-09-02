# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import secrets

from odoo import api, fields, models


# ----------------------------------------------------------
# Models for client
# ----------------------------------------------------------
class IotBox(models.Model):
    _name = 'iot.box'
    _description = 'IoT Box'

    name = fields.Char('Name', readonly=True)
    identifier = fields.Char(string='Identifier (Mac Address)', readonly=True)
    device_ids = fields.One2many('iot.device', 'iot_id', string="Devices")
    device_count = fields.Integer(compute='_compute_device_count')
    ip = fields.Char('Domain Address', readonly=True)
    ip_url = fields.Char('IoT Box Home Page', readonly=True, compute='_compute_ip_url')
    drivers_auto_update = fields.Boolean('Automatic drivers update', help='Automatically update drivers when the IoT Box boots', default=True)
    version = fields.Char('Image Version', readonly=True)
    is_websocket_active = fields.Boolean("Is Websocket active?", readonly=True, default=False)
    company_id = fields.Many2one('res.company', 'Company')

    def _compute_ip_url(self):
        for box in self:
            if not box.ip:
                box.ip_url = False
            else:
                url = 'https://%s' if box.get_base_url()[:5] == 'https' else 'http://%s:8069'
                box.ip_url = url % box.ip

    def _compute_device_count(self):
        for box in self:
            box.device_count = len(box.device_ids)


class IotDevice(models.Model):
    _name = 'iot.device'
    _description = 'IOT Device'

    iot_id = fields.Many2one('iot.box', string='IoT Box', required=True, ondelete='cascade')
    name = fields.Char('Name')
    identifier = fields.Char(string='Identifier', readonly=True)
    type = fields.Selection([
        ('printer', 'Printer'),
        ('camera', 'Camera'),
        ('keyboard', 'Keyboard'),
        ('scanner', 'Barcode Scanner'),
        ('device', 'Device'),
        ('payment', 'Payment Terminal'),
        ('scale', 'Scale'),
        ('display', 'Display'),
        ('fiscal_data_module', 'Fiscal Data Module'),
        ], readonly=True, default='device', string='Type',
        help="Type of device.")
    manufacturer = fields.Char(string='Manufacturer', readonly=True)
    connection = fields.Selection([
        ('network', 'Network'),
        ('direct', 'USB'),
        ('bluetooth', 'Bluetooth'),
        ('serial', 'Serial'),
        ('hdmi', 'HDMI'),
        ], readonly=True, string="Connection",
        help="Type of connection.")
    report_ids = fields.Many2many('ir.actions.report', string='Reports')
    iot_ip = fields.Char(related="iot_id.ip")
    company_id = fields.Many2one('res.company', 'Company', related="iot_id.company_id")
    connected = fields.Boolean(string='Status', help='If device is connected to the IoT Box', readonly=True)
    keyboard_layout = fields.Many2one('iot.keyboard.layout', string='Keyboard Layout')
    display_url = fields.Char('Display URL', help="URL of the page that will be displayed by the device, leave empty to use the customer facing display of the POS.")
    manual_measurement = fields.Boolean('Manual Measurement', compute="_compute_manual_measurement", help="Manually read the measurement from the device")
    is_scanner = fields.Boolean(string='Is Scanner', compute="_compute_is_scanner", inverse="_set_scanner",
        help="Manually switch the device type between keyboard and scanner")
    subtype = fields.Selection([
        ('receipt_printer', 'Receipt Printer'),
        ('label_printer', 'Label Printer'),
        ('office_printer', 'Office Printer'),
        ('', '')],
        default='', help='Subtype of device.')

    @api.depends('iot_id')
    def _compute_display_name(self):
        for i in self:
            i.display_name = f"[{i.iot_id.name}] {i.name}"

    @api.depends('type')
    def _compute_is_scanner(self):
        for device in self:
            device.is_scanner = True if device.type == 'scanner' else False

    def _set_scanner(self):
        for device in self:
            device.type = 'scanner' if device.is_scanner else 'keyboard'

    @api.depends('manufacturer')
    def _compute_manual_measurement(self):
        for device in self:
            device.manual_measurement = device.manufacturer == 'Adam'

    def write(self, vals):
        return_value = super().write(vals)
        if 'report_ids' in vals:
            self.env['iot.channel'].update_is_open()
        return return_value


class KeyboardLayout(models.Model):
    _name = 'iot.keyboard.layout'
    _description = 'Keyboard Layout'

    name = fields.Char('Name')
    layout = fields.Char('Layout')
    variant = fields.Char('Variant')


class IotChannel(models.AbstractModel):
    _name = "iot.channel"
    _description = "The Websocket Iot Channel"

    SYSTEM_PARAMETER_KEY = 'iot.ws_channel'

    def _create_channel_if_not_exist(self):
        iot_channel = f'iot_channel-{secrets.token_hex(16)}'
        self.env['ir.config_parameter'].sudo().set_param(self.SYSTEM_PARAMETER_KEY, iot_channel)
        return iot_channel

    def get_iot_channel(self, check=False):
        """
        Get the IoT channel name.
        To facilitate multi-company, the channel is unique for every company and IoT

        :param check: If False, it will force to return the channel name even if it is unused.
        """
        if (self.env.is_system() or self.env.user._is_internal()) and (not check or self.update_is_open()):
            iot_channel_key_value = self.env['ir.config_parameter'].sudo().get_param(self.SYSTEM_PARAMETER_KEY)
            return iot_channel_key_value or self._create_channel_if_not_exist()
        return ''

    def update_is_open(self):
        """
        Wherever the IoT Channel should be open or not.
        For performance reasons, we only open the channel if there is at least one IoT device with a report set.

        :return: True if the channel should be open, False otherwise
        """
        is_open = bool(self.env['iot.device'].search_count([('report_ids', '!=', False)], limit=1))
        if not is_open:
            self.env["iot.box"].search([]).write({"is_websocket_active": False})
        return is_open

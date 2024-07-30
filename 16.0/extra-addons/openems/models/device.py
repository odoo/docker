from odoo import api, fields, models, exceptions, _
from datetime import datetime
from odoo.exceptions import ValidationError
import random
import re
import string

class Device(models.Model):
    _name = "openems.device"
    _description = "OpenEMS Edge Device"
    _inherit = "mail.thread"
    _order = "name_number asc"
    _sql_constraints = [
        ("unique_name", "unique(name)", "Name needs to be unique"),
        ("unique_stock_production_lot_id", "unique(stock_production_lot_id)",
         "Serial number needs to be unique")
    ]

    name = fields.Char(required=True)
    active = fields.Boolean("Active", default=True, tracking=True)
    comment = fields.Char(tracking=True)
    internalnote = fields.Text("Internal note", tracking=True)
    tag_ids = fields.Many2many("openems.device_tag", string="Tags", tracking=True)
    monitoring_url = fields.Char(
        "Online-Monitoring", compute="_compute_monitoring_url", store=False
    )
    stock_production_lot_id = fields.Many2one("stock.lot")
    first_setup_protocol_date = fields.Datetime(
        "First Setup Protocol Date", compute="_compute_first_setup_protocol"
    )
    manual_setup_date = fields.Datetime("Manual Setup Date")

    @api.depends("setup_protocol_ids", "manual_setup_date")
    def _compute_first_setup_protocol(self):
        for rec in self:
            if rec.manual_setup_date:
                rec.first_setup_protocol_date = rec.manual_setup_date
            elif len(rec.setup_protocol_ids) > 0:
                rec.first_setup_protocol_date = rec.setup_protocol_ids[
                    (len(rec.setup_protocol_ids) - 1)
                ]["create_date"]
            else:
                rec.first_setup_protocol_date = None

    @api.depends("name")
    def _compute_monitoring_url(self):
        # Corrected the parameter key to 'edge_monitoring_url'
        base_url = self.env["ir.config_parameter"].sudo().get_param("edge_monitoring_url", default='#')
        for rec in self:
            if isinstance(rec.name, str) and rec.name:
                # Ensuring there is a '/' between base_url and rec.name if it's not already present
                separator = '' if base_url.endswith('/') else '/'
                rec.monitoring_url = base_url + separator + rec.name + "/live"
            else:
                rec.monitoring_url = base_url

    producttype = fields.Selection(
        [
            ("openems-edge", "OpenEMS Edge"),
        ],
        "Product type",
        tracking=True,
    )
    emshardware = fields.Selection([], "EMS Hardware", tracking=True)
    oem = fields.Selection(
        [
            ("openems", "OpenEMS"),
        ],
        "OEM Branding",
        default="openems",
    )

    # Settings
    openems_config = fields.Text("OpenEMS Config Full")
    openems_config_components = fields.Text("OpenEMS Config")
    openems_version = fields.Char("OpenEMS Version", tracking=True)

    # Security
    setup_password = fields.Char(
        "Installation Key",
        help="Password for commissioning by the installer",
    )
    apikey = fields.Char("API-Key", required=True, tracking=True)

    # 'openems_sum_state_level' is updated by OpenEMS Backend
    openems_sum_state_level = fields.Selection(
        [("ok", "Ok"), ("info", "Info"), ("warning", "Warning"), ("fault", "Fault")],
        "OpenEMS State",
    )
    # 'openems_is_connected' is updated by OpenEMS Backend
    openems_is_connected = fields.Boolean("OpenEMS Is connected")

    # System Status
    lastmessage = fields.Datetime("Last message")
    lastupdate = fields.Datetime("Last data update")

    # Verknüpfungen
    systemmessage_ids = fields.One2many(
        "openems.systemmessage", "device_id", string="System Messages"
    )
    user_role_ids = fields.One2many(
        "openems.device_user_role", "device_id", string="Roles", tracking=True
    )
    alerting_settings = fields.One2many(
        "openems.alerting", "device_id", string="Alerting", tracking=True
    )
    openems_config_update_ids = fields.One2many(
        "openems.openemsconfigupdate", "device_id", string="OpenEMS Config Updates"
    )
    setup_protocol_ids = fields.One2many(
        "openems.setup_protocol", "device_id", "Setup Protocols"
    )

    # Helper fields
    name_number = fields.Integer(compute="_compute_name_number", store="True")

    @api.depends("name")
    def _compute_name_number(self):
        for rec in self:
            rec.name_number = int(rec.name[4:]) if rec.name.startswith("edge") else -1

    def _get_openems_state_number(self, string):
        state = 0
        if string == "info":
            state = 1
        elif string == "warning":
            state = 2
        elif string == "fault":
            state = 3
        return state

    def write(self, vals):
        """Prohibit to change name field after creation."""
        if 'name' in vals:
            for record in self:
                if record.id and record.name != vals['name']:
                    self.env.cr.execute("""
                        SELECT EXISTS (
                            SELECT 1 FROM openems_device 
                            WHERE name = %s AND id != %s
                        )
                    """, (vals['name'], record.id))
                    exists = self.env.cr.fetchone()[0]
                    if exists:
                        # This means there's already a device with the intended new name
                        raise exceptions.UserError(
                            "The name '{}' is already in use or does not follow the required pattern.".format(
                                vals['name']))
    
                    # If you simply want to prevent name changes, the following UserError suffices
                    raise exceptions.UserError("The name of the device cannot be changed after creation.")
        return super(Device, self).write(vals)

    @api.model
    def create(self, vals):
        
        # Generate setup password if not provided
        if 'setup_password' not in vals or not vals['setup_password']:
            vals['setup_password'] = self._generate_unique_setup_password()

        # Generate API key if not provided
        if 'apikey' not in vals or not vals['apikey']:
            vals['apikey'] = self._generate_api_key()

        return super(Device, self).create(vals)

    def _generate_unique_setup_password(self):
        is_unique = False
        setup_password = ''
        while not is_unique:
            # Generate a random setup password
            raw_password = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
            setup_password = '-'.join([raw_password[i:i + 4] for i in range(0, len(raw_password), 4)])
            # Check if the generated setup password already exists
            existing = self.search_count([('setup_password', '=', setup_password)])
            # If the password does not exist, it is unique, and we can exit the loop
            if existing == 0:
                is_unique = True
        return setup_password

    def _generate_api_key(self):
        # Initialize a flag to indicate whether the generated key is unique
        is_unique = False
        api_key = ''
        while not is_unique:
            # Generate a random API key
            api_key = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
            # Check if the generated API key already exists
            existing = self.search_count([('apikey', '=', api_key)])
            # If the key does not exist, it is unique, and we can exit the loop
            if existing == 0:
                is_unique = True
        return api_key

    @api.onchange('setup_password')
    def _check_setup_password_format(self):
        for record in self:
            if not record.setup_password:
                continue
            if not re.match(r"^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$", record.setup_password):
                raise ValidationError("The device ID must be formatted as XXXX-XXXX-XXXX-XXXX")

    @api.onchange('apikey')
    def _check_api_key_uniqueness(self):
        for record in self:
            if record.apikey:
                # Prepare the domain for searching duplicates
                domain = [('apikey', '=', record.apikey)]
                # If the record is already saved (has a valid database ID), exclude it from the search
                if record.id and isinstance(record.id, (int,)):
                    domain.append(('id', '!=', record.id))
                # Check if any other records with the same API key exist
                existing = self.search_count(domain)
                # If there are duplicates, raise a ValidationError
                if existing:
                    raise ValidationError(
                        _("The API key already exists and must be unique. Please choose a different API key."))


class DeviceTag(models.Model):
    _name = "openems.device_tag"
    _description = "OpenEMS Edge Device Tag"
    name = fields.Char(required=True)


class DeviceUserRole(models.Model):
    _name = "openems.device_user_role"
    _description = "OpenEMS Edge Device User Role"
    _sql_constraints = [
        (
            "device_user_uniq",
            "unique(device_id, user_id)",
            "User already exists for this device.",
        ),
    ]
    device_id = fields.Many2one("openems.device", string="OpenEMS Edge")
    user_id = fields.Many2one("res.users", string="User")
    role = fields.Selection(
        [
            ("admin", "Admin"),
            ("installer", "Installer"),
            ("owner", "Owner"),
            ("guest", "Guest"),
        ],
        default="guest",
        required=True,
    )


class OpenemsConfigUpdate(models.Model):
    _name = "openems.openemsconfigupdate"
    _description = "OpenEMS Edge Device Configuration Update"
    _order = "create_date desc"

    device_id = fields.Many2one("openems.device", string="OpenEMS Edge")
    teaser = fields.Text("Update Details Teaser")
    details = fields.Html("Update Details")


class Systemmessage(models.Model):
    _name = "openems.systemmessage"
    _description = "OpenEMS Edge Systemmessage"
    _order = "create_date desc"

    timestamp = fields.Datetime("Creation date")
    device_id = fields.Many2one("openems.device", string="OpenEMS Edge")
    text = fields.Text("Message")
    text_teaser = fields.Char(compute="_compute_text_teaser")

    @api.depends("text")
    def _compute_text_teaser(self):
        for rec in self:
            # get up to 100 characters from first line
            rec.text_teaser = rec.text.splitlines()[0][0:100] if rec.text else False

class Alerting(models.Model):
    _name = "openems.alerting"
    _description = "OpenEMS Edge AlertingSettings"
    _sql_constraints = [
        (
            "device_user_uniq",
            "unique(device_id, user_id)",
            "User already has Alerting Settings.",
        ),
    ]

    device_id = fields.Many2one("openems.device", string="OpenEMS Edge")
    user_id = fields.Many2one("res.users", string="User")

    offline_delay = fields.Integer(string="Offline Notification", default=1440)
    warning_delay = fields.Integer(string="Warning Notification", default=1440)
    fault_delay = fields.Integer(string="Fault Notification", default=1440)

    offline_last_notification = fields.Datetime(string="Last Offline notification sent")
    sum_state_last_notification = fields.Datetime(string="Last SumState notification sent")

    device_name = fields.Text(compute="_compute_device_name", store="True")
    user_login = fields.Text(compute="_compute_user_login", store="True")

    user_role = fields.Selection(
        [("admin", "Admin"), ("installer", "Installer"), ("owner", "Owner"), ("guest", "Guest"),],
        compute="_compute_user_role", store="False")

    @api.depends("device_id")
    def _compute_device_name(self):
        for rec in self:
            rec.device_name = rec.device_id.name;

    @api.depends("user_id")
    def _compute_user_login(self):
        for rec in self:
            rec.user_login = rec.user_id.login;

    @api.depends("user_id", "device_id")
    def _compute_user_role(self):
        for rec in self:
            user_role: DeviceUserRole = rec.user_id.device_role_ids.search([('device_id','=',rec.device_id.id)])
            if user_role:
                return user_role.role
            else:
                return rec.user_id.global_role

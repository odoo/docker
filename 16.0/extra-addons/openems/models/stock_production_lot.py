from odoo import fields, models, api


class ProductionLot(models.Model):
    _inherit = "stock.lot"

    device_id = fields.Many2one(
        'openems.device', compute='compute_device_id', inverse='device_inverse')
    device_ids = fields.One2many('openems.device', 'stock_production_lot_id')

    @api.depends('device_ids')
    def compute_device_id(self):
        if len(self.device_ids) > 0:
            self.device_id = self.device_ids[0]

    def device_inverse(self):
        if len(self.device_ids) > 0:
            if len(self.device_id.stock_production_lot_id) > 0:
                raise ValueError("A serial number has already been assigned to the device")

            device = self.env['openems.device'].browse(self.device_ids[0].id)
            device.stock_production_lot_id = False
        self.device_id.stock_production_lot_id = self

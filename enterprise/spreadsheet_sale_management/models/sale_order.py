# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    spreadsheet_template_id = fields.Many2one(
        'sale.order.spreadsheet',
        related='sale_order_template_id.spreadsheet_template_id',
    )
    spreadsheet_ids = fields.One2many(
        'sale.order.spreadsheet',
        'order_id',
        string="Spreadsheets",
        export_string_translation=False,
    )
    spreadsheet_id = fields.Many2one(
        'sale.order.spreadsheet',
        export_string_translation=False,
        compute='_compute_spreadsheet_id',
    )

    @api.depends('spreadsheet_ids')
    def _compute_spreadsheet_id(self):
        for order in self:
            order.spreadsheet_id = order.spreadsheet_ids[:1]

    def action_open_sale_order_spreadsheet(self):
        self.ensure_one()
        if not self.spreadsheet_id:
            self.spreadsheet_template_id.copy({"order_id": self.id})
        return self.spreadsheet_id.action_open_spreadsheet()
    
    def unlink(self):
        for order in self:
            if order.spreadsheet_ids:
                order.spreadsheet_ids.unlink()
        return super().unlink()

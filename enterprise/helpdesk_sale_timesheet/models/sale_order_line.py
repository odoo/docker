# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    color = fields.Integer('Color', compute="_compute_color")

    @api.depends('remaining_hours_available', 'remaining_hours', 'state')
    def _compute_color(self):
        for line in self:
            if line.state == 'cancel' or line.remaining_hours < 0:
                line.color = 1
            elif not line.remaining_hours_available or line.remaining_hours > 0:
                line.color = 0
            else:
                line.color = 2

# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _prepare_down_payment_lines_values(self, order):
        """ Override. Down payments aren't sent to external tax calculators and will have their tax_ids cleared. This
        overrides the standard behavior to base these down payments on the total, not subtotal, just like standard
        down payments."""
        if not order.is_tax_computed_externally:
            return super()._prepare_down_payment_lines_values(order)

        line = self._prepare_base_downpayment_line_values(order)
        if self.advance_payment_method == 'percentage':
            line["price_unit"] = order.amount_total * (self.amount / 100)
        else:
            line["price_unit"] = self.fixed_amount

        line["price_unit"] = min(line["price_unit"], order.amount_total)
        # False to use the default account, because this single down payment line can relate to multiple products.
        return [line], [False]

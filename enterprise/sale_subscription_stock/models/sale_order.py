# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    display_recurring_stock_delivery_warning = fields.Boolean(compute='_compute_recurring_stock_products')

    def _upsell_context(self):
        context = super()._upsell_context()
        context["skip_procurement"] = True
        return context

    @api.depends('state', 'is_subscription', 'start_date', 'next_invoice_date')
    def _compute_recurring_stock_products(self):
        self.display_recurring_stock_delivery_warning = False
        for order in self:
            if order.state == 'sale' and order.is_subscription and order.next_invoice_date <= order.start_date:
                has_stock_sub_lines = bool(len(order.order_line._get_stock_subscription_lines()))
                order.display_recurring_stock_delivery_warning = has_stock_sub_lines

    def _handle_post_invoice_hook_exception(self):
        super()._handle_post_invoice_hook_exception()
        for order in self:
            post_invoice_fail_summary = _("Delivery creation failed")
            post_invoice_fail_note = _(
                "A system error prevented the automatic creation of delivery orders for this subscription."
                " To ensure your delivery is processed, please trigger it manually by using the"
                " \"Subscription: Generate delivery\" action."
            )
            order.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_warning').id,
                summary=post_invoice_fail_summary,
                note=post_invoice_fail_note,
                user_id=order.subscription_id.user_id.id
            )

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command
from odoo.tools import _, get_timedelta


class SaleSubscriptionPlan(models.Model):
    _name = 'sale.subscription.plan'
    _description = 'Subscription Plan'

    active = fields.Boolean(default=True)
    name = fields.Char(translate=True, required=True, default="Monthly")
    company_id = fields.Many2one('res.company')

    # Billing Period, use billing_period property for access to the timedelta
    billing_period_value = fields.Integer(string="Billing Period ", required=True, default=1)
    billing_period_unit = fields.Selection([("week", "Weeks"), ("month", "Months"), ('year', 'Years')],
                                           string="Unit", required=True, default='month')

    billing_period_display = fields.Char(compute='_compute_billing_period_display', string="Billing Period", search='_search_billing_period_display')
    billing_period_display_sentence = fields.Char(compute='_compute_billing_period_display_sentence', string="Billing Period Display")

    billing_first_day = fields.Boolean(string="Align to Period Start", default=False, help="Align all subscription invoices on the first day of each billing period.")

    # Self Service
    user_closable = fields.Boolean(string="Closable", default=False,
                                   help="Customer can close their subscriptions.")
    user_extend = fields.Boolean("Renew", default=False,
                                 help="Customer can create a renewal quotation for their subscription.")
    user_quantity = fields.Boolean("Add Products", default=False,
                                   help="Allow customers to create an Upsell quote to adjust the quantity of products in their subscription."
                                   "Only products that are listed as \"optional products\" can be modified.")
    related_plan_id = fields.Many2many("sale.subscription.plan", "sale_subscription_plan_related_plan",
                                       "plan_id", "related_plan_id", string="Optional Plans",
                                       help="Allow your customers to switch from this plan to "
                                            "another on quotation (new subscription or renewal)")
    user_closable_options = fields.Selection([
        ("at_date", "At date"),
        ("end_of_period", "End of period")
    ], string="Closeable Plan Options", required=True, default='at_date')

    # Invoicing
    auto_close_limit = fields.Integer(string="Automatic Closing", default=15,
                                      help="Unpaid subscription after the due date majored by this number of days will be automatically closed by "
                                      "the subscriptions expiration scheduled action. \n"
                                      "If the chosen payment method has failed to renew the subscription after this time, "
                                      "the subscription is automatically closed.")

    auto_close_limit_display = fields.Char(string="Automatic Closing After", compute="_compute_auto_close_limit_display")

    invoice_mail_template_id = fields.Many2one('mail.template', string='Invoice Email Template',
                                               domain=[('model', '=', 'account.move')],
                                               default=lambda self: self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False),
                                               help="Email template used to send invoicing email automatically.\n"
                                                    "Leave it empty if you don't want to send email automatically.")

    product_subscription_pricing_ids = fields.One2many('sale.subscription.pricing', 'plan_id', string="Recurring Pricing",
                                                       domain=['|', ('product_template_id', '=', None), ('product_template_id.active', '=', True)])

    # UX
    active_subs_count = fields.Integer(compute="_compute_active_subs_count", string="Subscriptions")
    subscription_line_count = fields.Integer(compute="_compute_active_subscription_line_count", string="Subscription Count")

    _sql_constraints = [
        (
            'check_for_valid_billing_period_value', 'CHECK(billing_period_value > 0)',
            'Recurring period must be a positive number. Please ensure the input is a valid positive numeric value.')
    ]

    def write(self, values):
        if "related_plan_id" in values:
            old_related = {plan.id: plan.related_plan_id for plan in self}
        res = super().write(values)
        if "related_plan_id" in values:
            for plan in self:
                if to_remove := old_related[plan.id] - plan.related_plan_id:
                    to_remove.related_plan_id = [Command.unlink(plan.id)]
                if to_add := plan.related_plan_id - old_related[plan.id]:
                    to_add.related_plan_id = [Command.link(plan.id)]
        return res

    def _search_billing_period_display(self, operator, value):
        if operator not in ['=', 'in']:
            raise NotImplementedError
        plan_ids = self.env['sale.subscription.plan']
        for plan in self.env['sale.subscription.plan'].search([]):
            if value in plan.billing_period_display:
                plan_ids += plan
        return [('id', 'in', plan_ids.ids)]

    def _compute_active_subs_count(self):
        self.active_subs_count = 0
        res = self.env['sale.order'].read_group(
            [('plan_id', 'in', self.ids), ('is_subscription', '=', True), ('subscription_state', 'in', ['3_progress', '4_paused'])],
            ['__count'], ['plan_id'],
        )
        for template in res:
            if template['plan_id']:
                self.browse(template['plan_id'][0]).active_subs_count = template['plan_id_count']

    def _compute_active_subscription_line_count(self):
        self.subscription_line_count = 0
        line_counts = self.env['sale.order.line'].read_group(
          [('order_id.is_subscription', '=', True), ('subscription_plan_id', 'in', self.ids), ('order_id.subscription_state', 'in', ('3_progress', '4_paused'))],
          ['__count'],
          ['subscription_plan_id']
        )
        line_counts = {r['subscription_plan_id'][0]: r['subscription_plan_id_count'] for r in line_counts}
        for plan in self:
            plan.subscription_line_count = line_counts.get(plan.id, 0)

    def action_open_active_sub(self):
        return {
            'name': _('Subscriptions'),
            'view_mode': 'list,form',
            'domain': [('plan_id', 'in', self.ids), ('is_subscription', '=', True), ('subscription_state', 'in', ['3_progress', '4_paused'])],
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
        }

    def action_open_active_subscription_lines(self):
        subscription_items_plan = self.env['sale.order'].search([('plan_id', 'in', self.ids), ('is_subscription', '=', True), ('subscription_state', 'in', ['3_progress', '4_paused'])]).order_line
        return {
            'name': _('Subscription Items'),
            'view_mode': 'list',
            'views': [(self.env.ref('sale_subscription.sale_subscription_sale_order_line_list').id, 'list')],
            'search_view_id': [self.env.ref('sale_subscription.sale_subscription_sales_order_line_filter').id],
            'domain': [('id', 'in', subscription_items_plan.ids)],
            'context': {'create': False},
            'res_model': 'sale.order.line',
            'type': 'ir.actions.act_window',
        }

    @property
    def billing_period(self):
        if not self.billing_period_unit or not self.billing_period_value:
            return False
        return get_timedelta(self.billing_period_value, self.billing_period_unit)

    @api.depends_context('lang')
    @api.depends('billing_period_value', 'billing_period_unit')
    def _compute_billing_period_display(self):
        labels = dict(self._fields['billing_period_unit']._description_selection(self.env))
        for plan in self:
            plan.billing_period_display = f"{plan.billing_period_value} {labels[plan.billing_period_unit]}"

    @api.depends_context('lang')
    @api.depends('billing_period_value', 'billing_period_unit')
    def _compute_billing_period_display_sentence(self):
        for plan in self:
            value = plan.billing_period_value
            if plan.billing_period_unit == 'week':
                sentence = _('per %d weeks', value) if value > 1 else _('per week')
            elif plan.billing_period_unit == 'month':
                sentence = _('per %d months', value) if value > 1 else _('per month')
            elif plan.billing_period_unit == 'year':
                sentence = _('per %d years', value) if value > 1 else _('per year')
            else:
                raise ValueError(f"Invalid Billing Period Unit {plan.billing_period_unit!r}")
            plan.billing_period_display_sentence = sentence

    @api.depends('auto_close_limit')
    def _compute_auto_close_limit_display(self):
        for plan in self:
            plan.auto_close_limit_display = self.env._('%s days', plan.auto_close_limit)

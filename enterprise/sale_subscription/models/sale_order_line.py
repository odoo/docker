# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from collections import defaultdict

from odoo import fields, models, api, _, Command
from odoo.tools import float_is_zero, format_date

INTERVAL_FACTOR = {
    'day': 30.437,  # average number of days per month over the year,
    'week': 30.437 / 7.0,
    'month': 1.0,
    'year': 1.0 / 12.0,
}


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    recurring_invoice = fields.Boolean(related="product_template_id.recurring_invoice")
    recurring_monthly = fields.Monetary(compute='_compute_recurring_monthly', string="Monthly Recurring Revenue")
    parent_line_id = fields.Many2one('sale.order.line', compute='_compute_parent_line_id', store=True, precompute=True, index='btree_not_null')
    last_invoiced_date = fields.Date(compute='_compute_last_invoiced_date', index=True, store=True)
    pricelist_id = fields.Many2one(related="order_id.pricelist_id")
    subscription_start_date = fields.Date(related="order_id.start_date")
    subscription_end_date = fields.Date(related="order_id.end_date")
    next_invoice_date = fields.Date(related="order_id.next_invoice_date")
    product_template_variant_value_ids = fields.Many2many(related="product_id.product_template_variant_value_ids")
    subscription_plan_id = fields.Many2one(related="order_id.plan_id")

    @property
    def upsell_total(self):
        for line in self:
            if line.order_id.subscription_state != '7_upsell':
                return 0
            if line.parent_line_id:
                additional_qty = line.product_uom_qty if line.state in ('draft', 'sent') else 0
                return line.parent_line_id.product_uom_qty + additional_qty
            return line.product_uom_qty

    def _check_line_unlink(self):
        """ Override. Check whether a line can be deleted or not."""
        undeletable_lines = super()._check_line_unlink()
        not_subscription_lines = self.filtered(lambda line: not (line.order_id.is_subscription and line.recurring_invoice))
        return not_subscription_lines and undeletable_lines

    @api.depends('order_id.next_invoice_date', 'recurring_invoice')
    def _compute_invoice_status(self):
        skip_line_status_compute = self.env.context.get('skip_line_status_compute')
        if skip_line_status_compute:
            return
        super(SaleOrderLine, self)._compute_invoice_status()
        today = fields.Date.today()
        for line in self:
            currency_id = line.order_id.currency_id or self.env.company.currency_id
            next_invoice_date = line.order_id.next_invoice_date
            last_invoiced_date = line.last_invoiced_date
            if not line.order_id.is_subscription or not line.recurring_invoice:
                continue
            # Subscriptions and upsells
            recurring_free = currency_id.compare_amounts(line.order_id.recurring_monthly, 0) < 1
            if recurring_free:
                # free subscription lines are never to invoice whatever the dates
                line.invoice_status = 'no'
                continue
            to_invoice_check = next_invoice_date and line.state == 'sale' and next_invoice_date >= today
            if line.order_id.end_date:
                to_invoice_check = to_invoice_check and line.order_id.end_date > today
            if to_invoice_check:
                # future and free lines are automtically invoiced
                future_line = line.order_id.start_date and line.order_id.start_date > today or (currency_id.is_zero(line.price_subtotal))
                if future_line:
                    line.invoice_status = 'no'
                elif last_invoiced_date and last_invoiced_date <= today and next_invoice_date:
                    line.invoice_status = 'invoiced'

    @api.depends('order_id.subscription_state', 'order_id.start_date')
    def _compute_discount(self):
        """ For upsells : this method compute the prorata ratio for upselling when the current and possibly future
                        period have already been invoiced.
                        The algorithm work backward by trying to remove one period at a time from the end to have a number of
                        complete period before computing the prorata for the current period.
                        For the current period, we use the remaining number of days / by the number of day in the current period.
        """
        today = fields.Date.today()
        other_lines = self.env['sale.order.line']
        line_per_so = defaultdict(lambda: self.env['sale.order.line'])
        for line in self:
            if not line.recurring_invoice:
                other_lines += line  # normal sale line are handled by super
            else:
                line_per_so[line.order_id._origin.id] += line

        for so_id, lines in line_per_so.items():
            order_id = self.env['sale.order'].browse(so_id)
            parent_id = order_id.subscription_id
            if not parent_id.next_invoice_date or order_id.subscription_state != '7_upsell':
                # We don't apply discount
                continue
            start_date = max(order_id.start_date or today, order_id.first_contract_date or today)
            end_date = parent_id.next_invoice_date
            if start_date >= end_date:
                ratio = 0
            else:
                recurrence = parent_id.plan_id.billing_period
                complete_rec = 0
                while end_date - recurrence >= start_date:
                    complete_rec += 1
                    end_date -= recurrence
                ratio = (end_date - start_date).days / ((start_date + recurrence) - start_date).days + complete_rec
            # If the parent line had a discount, we reapply it to keep the same conditions.
            # E.G. base price is 200€, parent line has a 10% discount and upsell has a 25% discount.
            # We want to apply a final price equal to 200 * 0.75 (prorata) * 0.9 (discount) = 135 or 200*0,675
            # We need 32.5 in the discount
            add_comment = False
            line_to_discount, discount_comment = lines._get_renew_discount_info()
            for line in line_to_discount:
                if line.parent_line_id and line.parent_line_id.discount:
                    line.discount = (1 - ratio * (1 - line.parent_line_id.discount / 100)) * 100
                else:
                    line.discount = (1 - ratio) * 100
                # Add prorata reason for discount if necessary
                if ratio != 1 and "(*)" not in line.name:
                    line.name += "(*)"
                    add_comment = True
            if add_comment and not any((l.display_type == 'line_note' and '(*)' in l.name) for l in order_id.order_line):
                order_id.order_line = [Command.create({
                    'display_type': 'line_note',
                    'sequence': 999,
                    'name': discount_comment,
                    'product_uom_qty': 0,
                })]

        return super(SaleOrderLine, other_lines)._compute_discount()

    @api.depends('order_id.plan_id', 'parent_line_id')
    def _compute_price_unit(self):
        line_to_recompute = self.env['sale.order.line']
        for line in self:
            # Recompute order lines if part of a regular sale order. (not is_subscription or upsells)
            # This check avoids breaking other module's tests which trigger this function.
            if not line.order_id.subscription_state:
                line_to_recompute |= line
            elif line.parent_line_id:
                # Carry custom price of recurring products from previous subscription after renewal.
                line.price_unit = line.parent_line_id.price_unit
            elif line.order_id.state in ['draft', 'sent'] or line.product_id.recurring_invoice or not line.price_unit:
                # Recompute prices for subscription products or regular products when these are first inserted.
                line_to_recompute |= line
        super(SaleOrderLine, line_to_recompute)._compute_price_unit()

    def _lines_without_price_recomputation(self):
        res = super()._lines_without_price_recomputation()
        return res.filtered(lambda line: not line.recurring_invoice)

    def _compute_pricelist_item_id(self):
        recurring_lines = self.filtered('recurring_invoice')
        super(SaleOrderLine, self - recurring_lines)._compute_pricelist_item_id()
        recurring_lines.pricelist_item_id = False

    @api.depends('recurring_invoice', 'invoice_lines.deferred_start_date', 'invoice_lines.deferred_end_date',
                 'order_id.next_invoice_date', 'order_id.last_invoice_date')
    def _compute_qty_to_invoice(self):
        return super()._compute_qty_to_invoice()

    @api.depends('order_id.end_date', 'order_id.last_invoice_date', 'order_id.next_invoice_date',
                 'order_id.subscription_state', 'recurring_invoice', 'recurring_monthly')
    def _compute_amount_to_invoice(self):
        # EXTENDS 'sale'
        super()._compute_amount_to_invoice()
        for line in self:
            order = line.order_id
            today = fields.Date.context_today(order)

            is_invoice_due = (
                not order.last_invoice_date
                or (order.next_invoice_date <= today and order.last_invoice_date <= today)
            )
            if not is_invoice_due:
                line.amount_to_invoice = 0.0
                continue

            is_order_active = (
                order.subscription_state in ('3_progress', '4_paused')
                and (not order.end_date or order.next_invoice_date < order.end_date)
            )
            if line.recurring_invoice and is_order_active and not float_is_zero(line.price_subtotal, precision_rounding=line.currency_id.rounding):
                recurring_monthly_tax_incl = line.recurring_monthly / line.price_subtotal * line.price_total
                line.amount_to_invoice = recurring_monthly_tax_incl

    @api.depends('invoice_lines.deferred_end_date', 'invoice_lines.move_id.state')
    def _compute_last_invoiced_date(self):
        relevant_move_lines = self.env['account.move.line']._read_group(
            [
                ('sale_line_ids', 'in', self.ids),
                ('move_id.state', '=', 'posted'),
                ('move_id.move_type', 'in', ['out_invoice', 'out_refund']),
                ('deferred_end_date', '!=', False)
            ],
            aggregates=['id:recordset'],
            groupby=['sale_line_ids']
        )
        self.last_invoiced_date = False
        for line, move_lines in relevant_move_lines:
            line.last_invoiced_date = move_lines._get_max_invoiced_date()

    def _get_invoice_lines(self):
        self.ensure_one()
        if not self.recurring_invoice:
            return super()._get_invoice_lines()
        else:
            last_invoice_date = self.order_id.last_invoice_date or self.order_id.start_date
            invoice_line = self.invoice_lines.filtered(
                lambda line: line.date and last_invoice_date and line.date > last_invoice_date)
            return invoice_line

    def _get_subscription_qty_to_invoice(self, last_invoiced_date=False, next_invoice_date=False):
        """
        Compute the quantity to invoice for the current period or for a fixed period.
        :param last_invoiced_date: date after which the contract is not already invoiced
        :param next_invoice_date: next knowned invoice date
        :return: qty to invoice per line
        :rtype: dict
        """
        result = {}
        qty_invoiced = self._get_subscription_qty_invoiced(last_invoiced_date, next_invoice_date)
        for line in self:
            if line.state != 'sale':
                continue
            if line.product_id.invoice_policy == 'order':
                result[line.id] = line.product_uom_qty - qty_invoiced.get(line.id, 0.0)
            else:
                result[line.id] = line.qty_delivered - qty_invoiced.get(line.id, 0.0)
        return result

    def _get_deferred_date(self, last_invoiced_date=None, next_invoice_date=None):
        """" Get deferred dates of a sale.order.line. This util method is useful when we need to know the current deferred dates of a line.
        If you want to compute future period date, check _get_invoice_line_parameters
        return: (date, date): deferred_start_date, deferred_end_date
        """
        self.ensure_one()
        if last_invoiced_date and next_invoice_date:
            # trivial case where the values are known. Taking care of it here to allow overrides
            return last_invoiced_date, next_invoice_date
        deferred_start_date = self.last_invoiced_date and self.last_invoiced_date + relativedelta(days=1) or self.order_id.start_date
        if self._is_postpaid_line():
            deferred_end_date = deferred_start_date + self.order_id.plan_id.billing_period - relativedelta(days=1)
        else:
            # We invoice in the future. Regular line are based on next invoice date value to be resilient
            # on missing link between sale order line and acount move lines
            # warning this is not working if the recurrence is updated without renewal
            last_period_start = self.order_id.next_invoice_date and self.order_id.next_invoice_date - self.order_id.plan_id.billing_period
            deferred_start_date = self.last_invoiced_date or last_period_start
            next_invoice_date = self.order_id.next_invoice_date
            deferred_end_date = self.last_invoiced_date or next_invoice_date and next_invoice_date - relativedelta(days=1)
        return deferred_start_date, deferred_end_date

    def _get_subscription_qty_invoiced(self, last_invoiced_date=None, next_invoice_date=None):
        """
        Compute the quantity invoiced for the current period or for a fixed period.
        :param last_invoiced_date: date after which the contract is not already invoiced
        :param next_invoice_date: next knowned invoice date
        :return: qty to invoice per line
        :rtype: dict
        """
        result = {}
        amount_sign = {'out_invoice': 1, 'out_refund': -1}
        for line in self:
            if not line.recurring_invoice or line.order_id.state != 'sale':
                continue
            qty_invoiced = 0.0
            if not line.invoice_lines:
                continue
            period_start, period_end = line._get_deferred_date(last_invoiced_date=last_invoiced_date, next_invoice_date=next_invoice_date)
            if not period_start or not period_end:
                continue
            # The related_invoice_lines have their subscription_{start,end}_date between start_date and day_before_end_date
            # But sometimes, migrated contract and account_move_line don't have these value set.
            # We fall back on the  l.move_id.invoice_date which could be wrong if the invoice is posted during another
            # period than the subscription.
            period = period_end if line._is_postpaid_line() else period_start
            related_invoice_lines = line.invoice_lines.filtered(
                lambda l: l.move_id.state != 'cancel' and
                          l.deferred_start_date and l.deferred_end_date and
                          period == l.deferred_end_date
            )
            for invoice_line in related_invoice_lines:
                line_sign = amount_sign.get(invoice_line.move_id.move_type, 1)
                qty_invoiced += line_sign * invoice_line.product_uom_id._compute_quantity(invoice_line.quantity, line.product_uom)
            result[line.id] = qty_invoiced
        return result

    @api.depends('recurring_invoice', 'invoice_lines', 'invoice_lines.deferred_start_date', 'invoice_lines.deferred_end_date')
    def _compute_qty_invoiced(self):
        other_lines = self.env['sale.order.line']
        subscription_qty_invoiced = self._get_subscription_qty_invoiced()
        for line in self:
            if not line.recurring_invoice:
                other_lines |= line
                continue
            line.qty_invoiced = subscription_qty_invoiced.get(line.id, 0.0)
        super(SaleOrderLine, other_lines)._compute_qty_invoiced()

    @api.depends('recurring_invoice', 'price_subtotal')
    def _compute_recurring_monthly(self):
        for line in self:
            if not line.recurring_invoice or not line.order_id.plan_id.billing_period:
                line.recurring_monthly = 0
            else:
                line.recurring_monthly = line.price_subtotal * INTERVAL_FACTOR[line.order_id.plan_id.billing_period_unit] / line.order_id.plan_id.billing_period_value

    @api.depends('order_id.subscription_id', 'order_id.subscription_id.order_line', 'product_id', 'product_uom', 'price_unit', 'order_id', 'order_id.plan_id')
    def _compute_parent_line_id(self):
        """
        Compute the link between a SOL and the line in the parent order. The matching is done based on several
        fields values like the price_unit, the uom, etc. The method does not depend on pricelist_id or currency_id
        on purpose because '_compute_price_unit' depends on 'parent_line_id' and it triggered side effects
        when we added these dependencies.
        """
        parent_line_ids = self.order_id.subscription_id.order_line
        for line in self:
            if not line.order_id.subscription_id or not line.product_id.recurring_invoice:
                continue
            # We use a rounding to avoid -326.40000000000003 != -326.4 for new records.
            matching_line_ids = parent_line_ids.filtered(
                lambda l:
                (l.order_id, l.product_id, l.product_uom, l.order_id.currency_id, l.order_id.plan_id,
                 l.order_id.currency_id.round(l.price_unit) if l.order_id.currency_id else round(l.price_unit, 2)) ==
                (line.order_id.subscription_id, line.product_id, line.product_uom, line.order_id.currency_id, line.order_id.plan_id,
                 line.order_id.currency_id.round(line.price_unit) if line.order_id.currency_id else round(line.price_unit, 2)
                ) and l.id in parent_line_ids.ids
            )
            if matching_line_ids:
                line.parent_line_id = matching_line_ids._origin[-1]
                parent_line_ids -= matching_line_ids._origin[-1]
            else:
                line.parent_line_id = False

    def _get_invoice_line_parameters(self):
        """ Util to compute the relevant next period to invoice for a line dependent on his pre-paid or post-paid status
        This methods computes:
            new_period_start, new_period_stop: the date corresponding to the current invoicing period
            ratio: when we are invoicing a fraction of period, we need to compute the how much will be charged based on the prorata temporis
            number_of_days: the number of days in the current period when we are not invoicing a full period.
        :return: (new_period_start, new_period_stop, ratio, number_of_days)
        """
        self.ensure_one()
        today = fields.Date.today()
        start_date = self.order_id.start_date or today
        first_contract_date = self.order_id.first_contract_date or start_date

        if self.order_id.subscription_state == '7_upsell':
            # We start at the beginning of the upsell as it's a part of recurrence
            new_period_start = max(start_date, first_contract_date)
            new_period_stop = self.order_id.next_invoice_date
        else:
            # We need to invoice the next period: last_invoice_date will be today once this invoice is created. We use get_timedelta to avoid gaps
            # We always use next_invoice_date as the recurrence are synchronized with the invoicing periods.
            # Next invoice date is required and is equal to start_date at the creation of a subscription
            if self._is_postpaid_line():
                # fallback on self.order_id.last_invoice_date to allow invoicing correctly the first period after an upsell.
                new_period_start = self.last_invoiced_date and self.last_invoiced_date + relativedelta(days=1) or self.order_id.last_invoice_date
                theoretical_stop = new_period_start and new_period_start + self.order_id.plan_id.billing_period - relativedelta(days=1)
                new_period_stop = min(date for date in [today, theoretical_stop, self.order_id.end_date] if date)
                return new_period_start, new_period_stop, 1, None
            else:
                new_period_start = self.order_id.next_invoice_date or max(start_date, first_contract_date)
                new_period_stop = new_period_start + self.order_id.plan_id.billing_period

        if not self.order_id.plan_id.billing_first_day or self.order_id.plan_id.billing_period_unit == 'week':
            # Never apply billing_first_day for weekly plan.
            return new_period_start, new_period_stop - relativedelta(days=1), 1, None
        elif self.order_id.plan_id.billing_period_unit == 'month':
            next_date_1st = new_period_stop + relativedelta(day=1)
        elif self.order_id.plan_id.billing_period_unit == 'year':
            next_date_1st = new_period_stop + relativedelta(day=1, month=1)

        number_of_days = (next_date_1st - new_period_start).days
        ratio = number_of_days / (new_period_stop - new_period_start).days

        return new_period_start, next_date_1st - relativedelta(days=1), ratio, number_of_days

    def _prepare_invoice_line(self, **optional_values):
        self.ensure_one()
        res = super()._prepare_invoice_line(**optional_values)
        if self.display_type:
            return res
        elif self.order_id.plan_id and (self.recurring_invoice or self.order_id.subscription_state == '7_upsell'):
            lang_code = self.order_id.partner_id.lang
            parent_order_id = self.order_id.subscription_id.id if self.order_id.subscription_state == '7_upsell' else self.order_id.id
            duration = self.order_id.plan_id.billing_period_display

            new_period_start, new_period_stop, ratio, number_of_days = self._get_invoice_line_parameters()

            if ratio != 1 and self.product_id.type == 'service':
                duration = _('%s days', number_of_days)
                res['price_unit'] = res['price_unit'] * ratio

            description = res.get('name') or self.name
            if self.recurring_invoice:
                format_start = format_date(self.env, new_period_start, lang_code=lang_code)
                format_next = format_date(self.env, new_period_stop, lang_code=lang_code)
                start_to_next = _("%(start)s to %(next)s", start=format_start, next=format_next)
                description += f"\n{duration} {start_to_next}"

            qty_to_invoice = self._get_subscription_qty_to_invoice(last_invoiced_date=new_period_start, next_invoice_date=new_period_stop)
            res.update({
                'name': description,
                'quantity': qty_to_invoice.get(self.id, 0.0),
                'deferred_start_date': new_period_start,
                'deferred_end_date': new_period_stop,
                'subscription_id': parent_order_id,
            })
        elif self.order_id.is_subscription and not res.get('subscription_id'):
            # This is needed in case we only need to invoice this line or Downpayments
            res.update({
                'subscription_id': self.order_id.id,
            })
        return res

    def _reset_subscription_qty_to_invoice(self):
        """ Define the qty to invoice on subscription lines equal to product_uom_qty for recurring lines
            It allows avoiding using the _compute_qty_to_invoice with a context_today
        """
        today = fields.Date.today()
        # TODO add under-delivered message
        for line in self:
            if not line.recurring_invoice or line._is_postpaid_line() or line.order_id.start_date and line.order_id.start_date > today:
                continue
            line.qty_to_invoice = line.product_uom_qty

    def _reset_subscription_quantity_post_invoice(self):
        """ Update the Delivered quantity value of recurring line according to the periods
        """
        # arj todo: reset only timesheet things. So reset nothing in standard but override in sale-subscription_timesheet (to be recreated...)
        return

    def _get_recurring_invoiceable_condition(self, automatic_invoice, date_from):
        """ Compute if the recurring line can be invoiced for the current period.
        """
        self.ensure_one()
        if automatic_invoice:
            # We don't invoice line before their SO's next_invoice_date
            return self.order_id.next_invoice_date and self.order_id.next_invoice_date <= date_from and self.order_id.start_date and self.order_id.start_date <= date_from
        elif self._is_postpaid_line():
            return True
        else:
            # We don't invoice line past their SO's end_date
            return not self.order_id.end_date or (self.order_id.next_invoice_date and self.order_id.next_invoice_date < self.order_id.end_date)

    ####################
    # Business Methods #
    ####################

    def _get_renew_discount_info(self):
        order = self.order_id
        if len(order) != 1:
            return [], ""
        today = fields.Date.today()
        start_date = max(today, order.first_contract_date or today)
        next_invoice_date = order.next_invoice_date or order.subscription_id.next_invoice_date
        end_date = next_invoice_date - relativedelta(days=1)
        if start_date >= end_date:
            line_name = _('(*) These recurring products are entirely discounted as the next period has not been invoiced yet.')
        else:
            format_start = format_date(self.env, start_date)
            format_end = format_date(self.env, end_date)
            line_name = _('(*) These recurring products are discounted according to the prorated period from %(start)s to %(end)s',
                start=format_start, end=format_end)
        return self.filtered_domain(self._need_renew_discount_domain()), line_name

    def _need_renew_discount_domain(self):
        return [('recurring_invoice', '=', True), ('product_id.type', '=', 'service')]

    def _get_renew_upsell_values(self, subscription_state, period_end=None):
        # TODO master: remove period_end from signature
        order_lines = []
        description_needed, description_name = [], ""
        if subscription_state == '7_upsell':
            description_needed, description_name = self._get_renew_discount_info()
        for line in self:
            if not line.recurring_invoice:
                continue
            if subscription_state == '7_upsell' and line._is_postpaid_line():
                continue
            partner_lang = line.order_id.partner_id.lang
            line = line.with_context(lang=partner_lang) if partner_lang else line
            product = line.product_id
            order_lines.append((0, 0, {
                'parent_line_id': line.id,
                'name': line.name + "(*)" if line in description_needed else line.name,
                'product_id': product.id,
                'product_uom': line.product_uom.id,
                'product_uom_qty': 0 if subscription_state == '7_upsell' else line.product_uom_qty,
                'price_unit': line.price_unit,
            }))

        if description_needed and description_name:
            order_lines.append((0, 0,
                {
                    'display_type': 'line_note',
                    'sequence': 999,
                    'name': description_name,
                    'product_uom_qty': 0
                }
            ))

        return order_lines

    def _subscription_update_line_data(self, subscription):
        """
        Prepare a dictionary of values to add or update lines on a subscription.
        :return: order_line values to create or update the subscription
        """
        update_values = []
        create_values = []
        dict_changes = {}
        for line in self:
            sub_line = line.parent_line_id
            if sub_line:
                # We have already a subscription line, we need to modify the product quantity
                if len(sub_line) > 1:
                    # we are in an ambiguous case
                    # to avoid adding information to a random line, in that case we create a new line
                    # we can simply duplicate an arbitrary line to that effect
                    sub_line[0].copy({'name': line.display_name, 'product_uom_qty': line.product_uom_qty})
                elif line.product_uom_qty != 0:
                    dict_changes.setdefault(sub_line.id, sub_line.product_uom_qty)
                    # upsell, we add the product to the existing quantity
                    dict_changes[sub_line.id] += line.product_uom_qty
            elif line.recurring_invoice:
                # we create a new line in the subscription:
                create_values.append(Command.create({
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'price_unit': line.price_unit,
                    'discount': 0,
                    'order_id': subscription.id
                }))
        update_values += [(1, sub_id, {'product_uom_qty': dict_changes[sub_id]}) for sub_id in dict_changes]
        return create_values, update_values

    # === PRICE COMPUTING HOOKS === #

    def _get_pricelist_price(self):
        if self.recurring_invoice:
            pricing = self.env['sale.subscription.pricing']._get_first_suitable_recurring_pricing(self.product_id, self.order_id.plan_id, self.order_id.pricelist_id)
            if pricing:
                return pricing.currency_id._convert(pricing.price, self.currency_id, self.company_id, fields.date.today())
            return super()._get_pricelist_price() or self.price_unit
        return super()._get_pricelist_price()

    # === UTILS === #
    def _is_postpaid_line(self):
        self.ensure_one()
        return self.product_id.invoice_policy == 'delivery'

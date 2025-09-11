# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
import json

from odoo import _, api, fields, models, Command
from odoo.tools import SQL
from odoo.addons.web.controllers.utils import clean_action


class BankRecWidget(models.Model):
    _inherit = 'bank.rec.widget'

    selected_batch_payment_ids = fields.Many2many(
        comodel_name='account.batch.payment',
        compute='_compute_selected_batch_payment_ids',
    )

    def _fetch_available_amls_in_batch_payments(self, batch_payments=None):
        self.ensure_one()
        st_line = self.st_line_id

        amls_domain = st_line._get_default_amls_matching_domain()
        query = self.env['account.move.line']._where_calc(amls_domain)
        rows = self.env.execute_query(SQL(
            '''
                SELECT
                    pay.batch_payment_id,
                    ARRAY_AGG(account_move_line.id) AS aml_ids
                FROM %s
                JOIN account_payment pay ON pay.id = account_move_line.payment_id
                JOIN account_batch_payment batch ON batch.id = pay.batch_payment_id
                WHERE %s
                    AND %s
                    AND pay.batch_payment_id IS NOT NULL
                    AND batch.state != 'reconciled'
                GROUP BY pay.batch_payment_id
            ''',
            query.from_clause,
            query.where_clause or SQL("TRUE"),
            SQL("pay.batch_payment_id IN %s", tuple(batch_payments.ids)) if batch_payments else SQL("TRUE")
        ))
        return {r[0]: r[1] for r in rows}

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('company_id', 'line_ids.source_batch_payment_id')
    def _compute_selected_batch_payment_ids(self):
        for wizard in self:
            batch_payment_x_amls = defaultdict(set)
            new_batches = wizard.line_ids.filtered(lambda x: x.flag == 'new_batch')
            new_batch_payments = new_batches.source_batch_payment_id
            new_amls = wizard.line_ids.filtered(lambda x: x.flag == 'new_aml')
            for new_aml in new_amls:
                if new_aml.source_batch_payment_id:
                    batch_payment_x_amls[new_aml.source_batch_payment_id].add(new_aml.source_aml_id.id)

            selected_batch_payment_ids = []
            if batch_payment_x_amls:
                batch_payments = wizard.line_ids.source_batch_payment_id
                available_amls_in_batch_payments = wizard._fetch_available_amls_in_batch_payments(batch_payments=batch_payments)
                selected_batch_payment_ids = [
                    x.id
                    for x in batch_payments
                    if batch_payment_x_amls[x] == set(available_amls_in_batch_payments.get(x.id, []))
                ]
            if new_batch_payments:
                selected_batch_payment_ids += new_batch_payments.ids

            wizard.selected_batch_payment_ids = [Command.set(selected_batch_payment_ids)]

    @api.depends('company_id', 'line_ids.source_aml_id', 'line_ids.source_batch_payment_id')
    def _compute_selected_aml_ids(self):
        super()._compute_selected_aml_ids()
        for wizard in self:
            new_batches = self.line_ids.filtered(lambda x: x.flag == 'new_batch')
            for batch in new_batches.source_batch_payment_id:
                wizard.selected_aml_ids += self._get_amls_from_batch_payments(batch)

    # -------------------------------------------------------------------------
    # HELPERS RPC
    # -------------------------------------------------------------------------

    def _prepare_embedded_views_data(self):
        # EXTENDS 'account_accountant'
        results = super()._prepare_embedded_views_data()
        st_line = self.st_line_id

        context = {
            'search_view_ref': 'account_accountant_batch_payment.view_account_batch_payment_search_bank_rec_widget',
            'list_view_ref': 'account_accountant_batch_payment.view_account_batch_payment_list_bank_rec_widget',
        }

        dynamic_filters = []

        # == Dynamic filter for the same journal ==
        journal = st_line.journal_id
        dynamic_filters.append({
            'name': 'same_journal',
            'description': journal.display_name,
            'domain': [('journal_id', '=', journal.id)],
        })
        context['search_default_same_journal'] = True

        # == Dynamic Currency filter ==
        if self.transaction_currency_id != self.company_currency_id:
            context['search_default_currency_id'] = self.transaction_currency_id.id

        # Stringify the domain.
        for dynamic_filter in dynamic_filters:
            dynamic_filter['domain'] = str(dynamic_filter['domain'])

        results['batch_payments'] = {
            'domain': [],
            'dynamic_filters': dynamic_filters,
            'context': context,
        }
        return results

    # -------------------------------------------------------------------------
    # LINES METHODS
    # -------------------------------------------------------------------------

    def _lines_prepare_new_aml_line(self, aml, **kwargs):
        # EXTENDS account_accountant
        return super()._lines_prepare_new_aml_line(
            aml,
            source_batch_payment_id=aml.payment_id.batch_payment_id.id,
            **kwargs,
        )

    def _get_amls_from_batch_payments(self, batch_payments):
        amls_domain = self.st_line_id._get_default_amls_matching_domain()
        amls = self.env['account.move.line']
        for batch in batch_payments:
            for payment in batch.payment_ids:
                liquidity_lines, _counterpart_lines, _writeoff_lines = payment._seek_for_lines()
                amls |= liquidity_lines.filtered_domain(amls_domain)
        return amls

    def _lines_prepare_new_batch_line(self, batch_payment, **kwargs):
        self.ensure_one()
        return {
            'source_batch_payment_id': batch_payment.id,
            'flag': 'new_batch',
            'currency_id': batch_payment.payment_ids.currency_id.id if len(batch_payment.payment_ids.currency_id) == 1 else False,
            'amount_currency': -batch_payment.amount_residual_currency,
            'balance': -batch_payment.amount_residual,
            'source_amount_currency': -batch_payment.amount_residual_currency,
            'source_balance': -batch_payment.amount_residual,
            'source_batch_payment_name': _("Includes %(count)s payment(s)", count=str(len(batch_payment.payment_ids.filtered(lambda p: p.state == 'in_process')))),
            'date': batch_payment.date,
            'name': batch_payment.name,
            **kwargs,
        }

    def _lines_load_new_batch_payments(self, batch_payments, reco_model=None):
        """ Create counterpart lines for the batch payments passed as parameter."""
        line_ids_commands = []
        kwargs = {'reconcile_model_id': reco_model.id} if reco_model else {}
        for batch in batch_payments:
            aml_line_vals = self._lines_prepare_new_batch_line(batch, **kwargs)
            line_ids_commands.append(Command.create(aml_line_vals))

        if not line_ids_commands:
            return

        self.line_ids = line_ids_commands

    def _get_key_mapping_aml_and_exchange_diff(self, line):
        # EXTENDS account_accountant
        if line.flag in ('new_batch', 'exchange_diff') and line.source_batch_payment_id:
            return 'source_batch_payment_id', line.source_batch_payment_id.id
        return super()._get_key_mapping_aml_and_exchange_diff(line)

    def _lines_get_exchange_diff_values(self, line):
        # EXTENDS account_accountant
        if line.flag != 'new_batch':
            return super()._lines_get_exchange_diff_values(line)
        exchange_diff_values = []
        currency_x_exchange = {}
        for currency, balance, amount_currency in [
            (aml.currency_id, -aml.amount_residual, -aml.amount_residual_currency)
            for aml in self._get_amls_from_batch_payments(line.source_batch_payment_id)
        ] + [
            (payment.currency_id, -payment.amount_company_currency_signed, -payment.amount)
            for payment in line.source_batch_payment_id.payment_ids.filtered(lambda p: not p.move_id)
        ]:
            account, exchange_diff_balance = self._lines_get_account_balance_exchange_diff(
                currency,
                balance,
                amount_currency,
            )
            if exchange_diff_balance != 0.0:
                currency_exch_amounts = currency_x_exchange.get((currency, account), {
                        'amount_currency': 0.0,
                        'balance': 0.0,
                    })
                currency_exch_amounts['amount_currency'] += exchange_diff_balance if currency == self.company_currency_id else 0.0
                currency_exch_amounts['balance'] += exchange_diff_balance
                currency_x_exchange[currency, account] = currency_exch_amounts

        for (currency, account), exch_amounts in currency_x_exchange.items():
            if not currency.is_zero(exch_amounts['balance']):
                exchange_diff_values.append({
                    'flag': 'exchange_diff',
                    'source_batch_payment_id': line.source_batch_payment_id.id,
                    'name': _("Exchange Difference: %(batch_name)s - %(currency)s", batch_name=line.source_batch_payment_id.name, currency=currency.name),
                    'account_id': account.id,
                    'currency_id': currency.id,
                    'amount_currency': exch_amounts['amount_currency'],
                    'balance': exch_amounts['balance'],
                })
        return exchange_diff_values

    def _validation_lines_vals(self, line_ids_create_command_list, aml_to_exchange_diff_vals, to_reconcile):
        batch_lines = self.line_ids.filtered(lambda x: x.flag == 'new_batch')
        valid_payment_states = batch_lines.source_batch_payment_id._valid_payment_states()
        for line in batch_lines:
            for payment in line.source_batch_payment_id.payment_ids.filtered(lambda p: p.state in valid_payment_states):
                account2amount = defaultdict(float)
                account2lines = defaultdict(list)
                term_lines = iter(payment.invoice_ids.line_ids.filtered(lambda l: l.display_type == 'payment_term').sorted('date'))
                remaining = payment.amount_signed
                while remaining and (term_line := next(term_lines, None)):
                    current = min(remaining, term_line.currency_id._convert(
                        from_amount=term_line.amount_currency,
                        to_currency=payment.currency_id,
                    ))
                    remaining -= current
                    account2amount[term_line.account_id] -= current
                    account2lines[term_line.account_id].append(term_line.id)
                if remaining:
                    account2amount[payment.partner_id.property_account_receivable_id] -= remaining
                for account, amount in account2amount.items():
                    line_ids_create_command_list.append(Command.create(line._get_aml_values(
                        sequence=len(line_ids_create_command_list) + 1,
                        partner_id=payment.partner_id.id,
                        account_id=account.id,
                        currency_id=payment.currency_id.id,
                        amount_currency=amount,
                        balance=payment.currency_id._convert(from_amount=amount, to_currency=self.env.company.currency_id),
                    )))
                    if lines := self.env['account.move.line'].browse(account2lines[account]):
                        to_reconcile.append((len(line_ids_create_command_list), lines))
        batch_lines.source_batch_payment_id.payment_ids.filtered(lambda p: not p.move_id and p.state in valid_payment_states).action_validate()
        self.line_ids -= batch_lines
        super()._validation_lines_vals(line_ids_create_command_list, aml_to_exchange_diff_vals, to_reconcile)

    # -------------------------------------------------------------------------
    # ACTIONS
    # -------------------------------------------------------------------------

    def _process_restore_lines_ids(self, initial_commands):
        commands = []
        for command in super()._process_restore_lines_ids(initial_commands):
            match command:
                case (Command.CREATE, _, values) if values.get('flag') == 'new_batch':
                    # Refresh the batch values (i.e. we jumped to the batch from the widget and rejected some payments)
                    batch = self.env['account.batch.payment'].browse(values['source_batch_payment_id'])
                    commands.append(Command.create(self._lines_prepare_new_batch_line(batch)))
                case _:
                    commands.append(command)
        return commands

    def _action_validate(self):
        # EXTENDS account_accountant
        self.ensure_one()
        batches = self.line_ids.filtered(lambda x: x.flag == 'new_batch').source_batch_payment_id
        batches_to_expand = batches.filtered('payment_ids.move_id')
        self._action_expand_batch_payments(batches_to_expand)
        super()._action_validate()

    def _action_add_new_batched_amls(self, batch_payments, reco_model=None, allow_partial=True):
        self.ensure_one()
        existing_batches = self.line_ids.filtered(lambda x: x.flag == 'new_batch').source_batch_payment_id
        batch_payments = batch_payments - existing_batches
        if not batch_payments:
            return
        existing_batch_new_amls = self.line_ids.filtered(lambda x: x.flag == 'new_aml' and x.source_batch_payment_id in batch_payments)
        self._action_remove_lines(existing_batch_new_amls)
        self._lines_load_new_batch_payments(batch_payments, reco_model=reco_model)
        added_lines = self.line_ids.filtered(lambda x: x.flag == 'new_batch' and x.source_batch_payment_id in batch_payments)
        self._lines_recompute_exchange_diff(added_lines)
        self._lines_check_apply_partial_matching()
        self._lines_add_auto_balance_line()
        self._action_clear_manual_operations_form()

    def _action_add_new_batch_payments(self, batch_payments):
        self.ensure_one()
        mounted_batches = self.line_ids.filtered(lambda x: x.flag == 'new_batch').source_batch_payment_id
        self._action_add_new_batched_amls(batch_payments - mounted_batches, allow_partial=False)

    def _js_action_add_new_batch_payment(self, batch_payment_id):
        self.ensure_one()
        batch_payment = self.env['account.batch.payment'].browse(batch_payment_id)
        self._action_add_new_batch_payments(batch_payment)

    def _action_remove_new_batch_payments(self, batch_payments):
        self.ensure_one()
        lines = self.line_ids.filtered(lambda x: x.flag in ('new_aml', 'new_batch') and x.source_batch_payment_id in batch_payments)
        self._action_remove_lines(lines)

    def _js_action_remove_new_batch_payment(self, batch_payment_id):
        self.ensure_one()
        batch_payment = self.env['account.batch.payment'].browse(batch_payment_id)
        self._action_remove_new_batch_payments(batch_payment)

    def _action_remove_lines(self, lines):
        self.ensure_one()
        if not lines:
            return
        has_new_batch = any(line.flag == 'new_batch' for line in lines)
        has_new_aml = any(line.flag == 'new_aml' for line in lines)
        super()._action_remove_lines(lines)
        if has_new_batch and not has_new_aml:
            # If the lines to delete does not contains new_amls,
            # the super method will not do the following computations.
            self._lines_check_apply_partial_matching()
            self._lines_add_auto_balance_line()

    def _action_expand_batch_payments(self, batch_payments):
        self.ensure_one()
        if not batch_payments:
            return
        batch_lines = self.line_ids.filtered(lambda x: x.flag == 'new_batch' and x.source_batch_payment_id in batch_payments)
        if not batch_lines:
            return
        batch_unlink_commands = []
        for batch_line in batch_lines:
            batch_unlink_commands.append(Command.unlink(batch_line.id))
        self.line_ids = batch_unlink_commands
        self._remove_related_exchange_diff_lines(batch_lines)
        self._action_add_new_amls(self._get_amls_from_batch_payments(batch_payments), allow_partial=False)

    def _js_action_redirect_to_move(self, form_index):
        self.ensure_one()
        line = self.line_ids.filtered(lambda x: x.index == form_index)
        if line.source_batch_payment_id:
            self.return_todo_command = clean_action(line.source_batch_payment_id._get_records_action(), self.env)
        else:
            return super()._js_action_redirect_to_move(form_index)

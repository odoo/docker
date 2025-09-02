# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo.exceptions import UserError
from odoo.tools import float_repr, SQL

from odoo import api, fields, models, release, _


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        company = self.env.company
        args = []
        if not company.company_registry:
            args.append(_('the Company ID'))
        if not (company.phone or company.mobile):
            args.append(_('the phone or mobile number'))
        if not (company.zip or company.city):
            args.append(_('the city or zip code'))

        if args:
            warnings['account_saft.company_data_warning'] = {
                'alert_type': 'warning',
                'args': _(', ').join(args),
            }

    ####################################################
    # ACTIONS
    ####################################################

    def action_fill_company_details(self, options, params):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Missing company details.'),
            'res_model': 'res.company',
            'views': [(False, 'form')],
            'res_id': self.env.company.id,
        }

    def _saft_get_account_type(self, account_type):
        """To be overridden if specific account types are needed.
        Some countries need to specify an account type, unique to the saf-t report.

        :return: False if no account type needed, otherwise a string with the account type"""
        return False

    @api.model
    def _saft_fill_report_general_ledger_accounts(self, report, options, values):
        res = {
            'account_vals_list': [],
        }

        accounts_results = self._query_values(report, options)
        rslts_array = tuple((account, res_col_gr[options['single_column_group']]) for account, res_col_gr in accounts_results)
        init_bal_res = self._get_initial_balance_values(report, tuple(account.id for account, results in rslts_array), options)
        initial_balances_map = {}
        initial_balance_gen = ((account, init_bal_dict.get(options['single_column_group'])) for account, init_bal_dict in init_bal_res.values())
        for account, initial_balance in initial_balance_gen:
            initial_balances_map[account.id] = initial_balance
        for account, results in rslts_array:
            account_init_bal = initial_balances_map[account.id]
            account_un_earn = results.get('unaffected_earnings', {})
            account_balance = results.get('sum', {})
            opening_balance = account_init_bal.get('balance', 0.0) + account_un_earn.get('balance', 0.0)
            closing_balance = account_balance.get('balance', 0.0)
            res['account_vals_list'].append({
                'account': account,
                'account_type': dict(self.env['account.account']._fields['account_type']._description_selection(self.env))[account.account_type],
                'saft_account_type': self._saft_get_account_type(account.account_type),
                'opening_balance': opening_balance,
                'closing_balance': closing_balance,
            })

        values.update(res)

    def _saft_fill_report_general_ledger_entries(self, report, options, values):
        res = {
            'total_debit_in_period': 0.0,
            'total_credit_in_period': 0.0,
            'journal_vals_list': [],
            'move_vals_list': [],
            'tax_detail_per_line_map': {},
        }
        # Fill 'total_debit_in_period', 'total_credit_in_period', 'move_vals_list'.
        query = report._get_report_query(options, 'strict_range')
        tax_name = self.env['account.tax']._field_to_sql('tax', 'name')
        journal_name = self.env['account.journal']._field_to_sql('journal', 'name')
        uom_name = self.env['uom.uom']._field_to_sql('uom', 'name')
        product_name = self.env['product.template']._field_to_sql('product_template', 'name')
        account_code = self.env['account.account']._field_to_sql('account', 'code')
        query = SQL(
            '''
            SELECT
                account_move_line.id,
                account_move_line.display_type,
                account_move_line.date,
                account_move_line.name,
                account_move_line.account_id,
                account_move_line.partner_id,
                account_move_line.currency_id,
                account_move_line.amount_currency,
                account_move_line.debit,
                account_move_line.credit,
                account_move_line.balance,
                account_move_line.tax_line_id,
                account_move_line.quantity,
                account_move_line.price_unit,
                account_move_line.product_id,
                account_move_line.product_uom_id,
                account_move.id                             AS move_id,
                account_move.name                           AS move_name,
                account_move.move_type                      AS move_type,
                account_move.create_date                    AS move_create_date,
                account_move.invoice_date                   AS move_invoice_date,
                account_move.invoice_origin                 AS move_invoice_origin,
                account_move.statement_line_id              AS move_statement_line_id,
                tax.id                                      AS tax_id,
                %(tax_name)s                                AS tax_name,
                tax.amount                                  AS tax_amount,
                tax.amount_type                             AS tax_amount_type,
                journal.id                                  AS journal_id,
                journal.code                                AS journal_code,
                %(journal_name)s                            AS journal_name,
                journal.type                                AS journal_type,
                account.account_type                        AS account_type,
                %(account_code)s                            AS account_code,
                currency.name                               AS currency_code,
                %(product_name)s                            AS product_name,
                product.default_code                        AS product_default_code,
                %(uom_name)s                                AS product_uom_name
            FROM %(table_references)s
            JOIN account_move ON account_move.id = account_move_line.move_id
            JOIN account_journal journal ON journal.id = account_move_line.journal_id
            JOIN account_account account ON account.id = account_move_line.account_id
            JOIN res_currency currency ON currency.id = account_move_line.currency_id
            LEFT JOIN product_product product ON product.id = account_move_line.product_id
            LEFT JOIN product_template product_template ON product_template.id = product.product_tmpl_id
            LEFT JOIN uom_uom uom ON uom.id = account_move_line.product_uom_id
            LEFT JOIN account_tax tax ON tax.id = account_move_line.tax_line_id
            WHERE %(search_condition)s
            ORDER BY account_move_line.date, account_move_line.id
            ''',
            tax_name=tax_name,
            journal_name=journal_name,
            account_code=account_code,
            product_name=product_name,
            uom_name=uom_name,
            table_references=query.from_clause,
            search_condition=query.where_clause,
        )
        self._cr.execute(query)

        journal_vals_map = {}
        move_vals_map = {}
        inbound_types = self.env['account.move'].get_inbound_types(include_receipts=True)
        while True:
            batched_line_vals = self._cr.dictfetchmany(10**4)
            if not batched_line_vals:
                break
            for line_vals in batched_line_vals:
                line_vals['rate'] = abs(line_vals['amount_currency']) / abs(line_vals['balance']) if line_vals['balance'] else 1.0
                line_vals['tax_detail_vals_list'] = []

                journal_vals_map.setdefault(line_vals['journal_id'], {
                    'id': line_vals['journal_id'],
                    'name': line_vals['journal_name'],
                    'code': line_vals['journal_code'],
                    'type': line_vals['journal_type'],
                    'move_vals_map': {},
                })
                journal_vals = journal_vals_map[line_vals['journal_id']]

                move_vals = {
                    'id': line_vals['move_id'],
                    'name': line_vals['move_name'],
                    'type': line_vals['move_type'],
                    'sign': -1 if line_vals['move_type'] in inbound_types else 1,
                    'invoice_date': line_vals['move_invoice_date'],
                    'invoice_origin': line_vals['move_invoice_origin'],
                    'date': line_vals['date'],
                    'create_date': line_vals['move_create_date'],
                    'partner_id': line_vals['partner_id'],
                    'journal_type': line_vals['journal_type'],
                    'statement_line_id': line_vals['move_statement_line_id'],
                    'line_vals_list': [],
                }
                move_vals_map.setdefault(line_vals['move_id'], move_vals)
                journal_vals['move_vals_map'].setdefault(line_vals['move_id'], move_vals)

                computed_line_name = f"[{line_vals['product_default_code']}] {line_vals['product_name']}" if line_vals['product_default_code'] else line_vals['product_name'] or ''
                line_vals['name'] = computed_line_name if not line_vals['name'] else line_vals['name']
                move_vals = move_vals_map[line_vals['move_id']]
                move_vals['line_vals_list'].append(line_vals)

                # Track the total debit/period of the whole period.
                res['total_debit_in_period'] += line_vals['debit']
                res['total_credit_in_period'] += line_vals['credit']

                res['tax_detail_per_line_map'][line_vals['id']] = line_vals

        # Fill 'journal_vals_list'.
        for journal_vals in journal_vals_map.values():
            journal_vals['move_vals_list'] = list(journal_vals.pop('move_vals_map').values())
            res['journal_vals_list'].append(journal_vals)
            res['move_vals_list'] += journal_vals['move_vals_list']

        values.update(res)

    @api.model
    def _saft_fill_report_tax_details_values(self, report, options, values):
        tax_vals_map = {}

        query = report._get_report_query(options, 'strict_range')
        tax_details_query = self.env['account.move.line']._get_query_tax_details(query.from_clause, query.where_clause)
        tax_name = self.env['account.tax']._field_to_sql('tax', 'name')
        tax_description = self.env['account.tax']._field_to_sql('tax', 'description')
        self._cr.execute(SQL('''
            SELECT
                tax_detail.base_line_id,
                tax_line.currency_id,
                tax.id AS tax_id,
                tax.type_tax_use AS tax_type,
                tax.amount_type AS tax_amount_type,
                %(tax_name)s AS tax_name,
                %(tax_description)s AS tax_description,
                tax.amount AS tax_amount,
                tax.create_date AS tax_create_date,
                SUM(tax_detail.tax_amount) AS amount,
                SUM(tax_detail.tax_amount) AS amount_currency
            FROM (%(tax_details_query)s) AS tax_detail
            JOIN account_move_line tax_line ON tax_line.id = tax_detail.tax_line_id
            JOIN account_tax tax ON tax.id = tax_detail.tax_id
            GROUP BY tax_detail.base_line_id, tax_line.currency_id, tax.id
        ''', tax_name=tax_name, tax_description=tax_description, tax_details_query=tax_details_query))
        for tax_vals in self._cr.dictfetchall():
            line_vals = values['tax_detail_per_line_map'][tax_vals['base_line_id']]
            line_vals['tax_detail_vals_list'].append({
                **tax_vals,
                'rate': line_vals['rate'],
                'currency_code': line_vals['currency_code'],
            })
            tax_vals_map.setdefault(tax_vals['tax_id'], {
                'id': tax_vals['tax_id'],
                'name': tax_vals['tax_name'],
                'description': tax_vals['tax_description'],
                'amount': tax_vals['tax_amount'],
                'amount_type': tax_vals['tax_amount_type'],
                'type': tax_vals['tax_type'],
                'create_date': tax_vals['tax_create_date']
            })

        # Fill 'tax_vals_list'.
        values['tax_vals_list'] = list(tax_vals_map.values())

    @api.model
    def _saft_fill_report_partner_ledger_values(self, options, values):
        res = {
            'customer_vals_list': [],
            'supplier_vals_list': [],
            'partner_detail_map': defaultdict(lambda: {
                'type': False,
                'addresses': [],
                'contacts': [],
            }),
        }

        all_partners = self.env['res.partner']

        # Fill 'customer_vals_list' and 'supplier_vals_list'
        report = self.env.ref('account_reports.partner_ledger_report')
        new_options = report.get_options(options)
        new_options['account_type'] = [
            {'id': 'trade_receivable', 'selected': True},
            {'id': 'non_trade_receivable', 'selected': True},
            {'id': 'trade_payable', 'selected': True},
            {'id': 'non_trade_payable', 'selected': True},
        ]
        handler = self.env['account.partner.ledger.report.handler']
        partners_results = handler._query_partners(new_options)
        partner_vals_list = []
        rslts_array = tuple((partner, res_col_gr[options['single_column_group']]) for partner, res_col_gr in partners_results)
        init_bal_res = handler._get_initial_balance_values(tuple(partner.id for partner, results in rslts_array if partner), options)

        initial_balances_map = {}
        initial_balance_gen = ((partner_id, init_bal_dict.get(options['single_column_group'])) for partner_id, init_bal_dict in init_bal_res.items())

        for partner_id, initial_balance in initial_balance_gen:
            initial_balances_map[partner_id] = initial_balance
        for partner, results in rslts_array:
            # Ignore Falsy partner.
            if not partner:
                continue

            all_partners |= partner
            partner_init_bal = initial_balances_map[partner.id]

            opening_balance = partner_init_bal.get('balance', 0.0)
            closing_balance = results.get('balance', 0.0)
            partner_vals_list.append({
                'partner': partner,
                'opening_balance': opening_balance,
                'closing_balance': closing_balance,
            })

        if all_partners:
            domain = [('partner_id', 'in', tuple(all_partners.ids))]
            query = report._get_report_query(new_options, 'strict_range', domain=domain)
            self._cr.execute(SQL(
                '''
                SELECT
                    account_move_line.partner_id,
                    SUM(account_move_line.balance)
                FROM %(table_references)s
                JOIN account_account account ON account.id = account_move_line.account_id
                WHERE %(search_condition)s
                AND account.account_type IN ('asset_receivable', 'liability_payable')
                GROUP BY account_move_line.partner_id
                ''',
                table_references=query.from_clause,
                search_condition=query.where_clause,
            ))

            for partner_id, balance in self._cr.fetchall():
                res['partner_detail_map'][partner_id]['type'] = 'customer' if balance >= 0.0 else 'supplier'

        for partner_vals in partner_vals_list:
            partner_id = partner_vals['partner'].id
            if res['partner_detail_map'][partner_id]['type'] == 'customer':
                res['customer_vals_list'].append(partner_vals)
            elif res['partner_detail_map'][partner_id]['type'] == 'supplier':
                res['supplier_vals_list'].append(partner_vals)

        # Fill 'partner_detail_map'.
        all_partners |= values['company'].partner_id
        partner_addresses_map = defaultdict(dict)
        partner_contacts_map = defaultdict(lambda: self.env['res.partner'])

        def _track_address(current_partner, partner):
            if partner.zip and partner.city or (options.get('saft_allow_empty_address') and partner != values['company'].partner_id):
                address_key = (partner.zip, partner.city)
                partner_addresses_map[current_partner][address_key] = partner

        def _track_contact(current_partner, partner):
            partner_contacts_map[current_partner] |= partner

        for partner in all_partners:
            _track_address(partner, partner)
            # For individual partners, they are their own ContactPerson.
            # For company partners, the child contact with lowest ID is the ContactPerson.
            # For the current company, all child contacts are ContactPersons
            # (to give users flexibility to indicate several ContactPersons).
            if partner.is_company:
                children = partner.child_ids.filtered(lambda p: p.type == 'contact' and p.active and not p.is_company).sorted('id')
                if partner == values['company'].partner_id:
                    if not children:
                        values['errors']['missing_company_contact'] = {
                            'message': _('Please define one or more Contacts belonging to your company.'),
                            'action_text': _('View Company Partner'),
                            'action': partner._get_records_action(name=_("Define Contact(s)")),
                            'level': 'danger',
                        }
                    for child in children:
                        _track_contact(partner, child)
                elif children:
                    _track_contact(partner, children[0])
            else:
                _track_contact(partner, partner)

        no_partner_address = self.env['res.partner']
        for partner in all_partners:
            res['partner_detail_map'][partner.id].update({
                'partner': partner,
                'addresses': list(partner_addresses_map[partner].values()),
                'contacts': partner_contacts_map[partner],
            })
            if not res['partner_detail_map'][partner.id]['addresses']:
                no_partner_address |= partner

        if no_partner_address:
            values['errors']['missing_partner_zip_city'] = {
                'message': _('Some partners are missing at least one address (Zip/City).'),
                'action_text': _('View Partners'),
                'action': no_partner_address._get_records_action(name=_("Partners to be checked")),
            }

        # Add newly computed values to the final template values.
        values.update(res)

    @api.model
    def _saft_prepare_report_values(self, report, options):
        def format_float(amount, digits=2):
            return float_repr(amount or 0.0, precision_digits=digits)

        def format_date(date_str, formatter):
            date_obj = fields.Date.to_date(date_str)
            return date_obj.strftime(formatter)

        if len(options["column_groups"]) > 1:
            raise UserError(_("SAF-T is only compatible with one column group."))

        report._init_currency_table(options)

        company = self.env.company
        options["single_column_group"] = tuple(options["column_groups"].keys())[0]

        template_values = {
            'company': company,
            'xmlns': '',
            'file_version': 'undefined',
            'accounting_basis': 'undefined',
            'today_str': fields.Date.to_string(fields.Date.context_today(self)),
            'software_version': release.version,
            'date_from': options['date']['date_from'],
            'date_to': options['date']['date_to'],
            'format_float': format_float,
            'format_date': format_date,
            'errors': {},
        }
        self._saft_fill_report_general_ledger_accounts(report, options, template_values)
        self._saft_fill_report_general_ledger_entries(report, options, template_values)
        self._saft_fill_report_tax_details_values(report, options, template_values)
        self._saft_fill_report_partner_ledger_values(options, template_values)
        return template_values

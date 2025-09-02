# Part of Odoo. See LICENSE file for full copyright and licensing details.
from lxml import etree
import warnings

from odoo import _, fields, models
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools import SQL
from odoo.tools.misc import format_date
from odoo.tools.float_utils import float_repr


class EstonianTaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_ee.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Estonian Tax Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        # Add XML export button
        options.setdefault('buttons', []).append({
            'name': _('XML'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'export_to_xml',
            'file_export_type': _('XML'),
        })

    def action_open_l10n_ee_modules(self, options, params):
        module = 'l10n_ee' if params.get('upgrade_l10n_ee') else 'l10n_ee_rounding'
        return {
            'type': 'ir.actions.act_window',
            'name': _('Modules'),
            'res_model': 'ir.module.module',
            'view_mode': 'kanban, form',
            'views': [(False, 'kanban'), (False, 'form')],
            'domain': [('name', '=', module)],
        }

    def action_open_account_update_tax_tags_module(self, options):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Modules'),
            'res_model': 'ir.module.module',
            'view_mode': 'kanban, form',
            'views': [(False, 'kanban'), (False, 'form')],
            'domain': [('name', '=', 'account_update_tax_tags')],
        }

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        """ Define if and which warning should be shown. A warning is displayed
        if the Estonia Accounting module is not updated or if the bridge module
        Estonia - Rounding is not installed.
        """
        l10n_ee_module = self.env['ir.module.module']._get('l10n_ee')
        l10n_ee_rounding_module = self.env['ir.module.module']._get('l10n_ee_rounding')
        upgrade_l10n_ee = l10n_ee_module.installed_version != l10n_ee_module.latest_version
        install_l10n_ee_rounding = l10n_ee_rounding_module.state != 'installed'
        if upgrade_l10n_ee:
            warnings['l10n_ee_reports.upgrade_l10n_ee_report_warning'] = {
                'alert_type': 'warning',
                'upgrade_l10n_ee': True,
            }
        elif install_l10n_ee_rounding:
            warnings['l10n_ee_reports.install_l10n_ee_rounding_warning'] = {
                'alert_type': 'warning',
                'install_l10n_ee_rounding': True,
            }

    def action_audit_cell(self, options, params):
        # OVERRIDES 'account_reports'
        """ The lines of the Estonian VAT report are rounded to the unit and use the
        aggregation engine for the computation. To facilitate the auditing of tax
        lines, 'balance_from_tags' is added to the report, using the tax_tags engine.
        """
        report_line = self.env['account.report.line'].browse(params['report_line_id'])

        if set(report_line.expression_ids.mapped('label')) == {'balance', 'balance_from_tags'}:
            params['expression_label'] = 'balance_from_tags'

        return report_line.report_id.action_audit_cell(options, params)

    ####################################################
    # EXPORT
    ####################################################

    def export_to_xml(self, options):
        """ Create export of the Normal period filling of the VAT return forms KMD
        and KMD INF. Requires the sender company's company registry number to be set.
        """
        report = self.env['account.report'].browse(options['report_id'])
        date_to = fields.Date.from_string(options['date'].get('date_to'))

        if options['date']['period_type'] != 'tax_period' and options['tax_periodicity']['periodicity'] != 'monthly':
            raise UserError(_('Choose a month to export the VAT Report'))

        sender_company = report._get_sender_company_for_export(options)
        if not sender_company.company_registry:
            raise RedirectWarning(
                message=_("No company registry number associated with your company. Please define one."),
                action={
                    'name': _("Company: %s", sender_company.name),
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'res.company',
                    'views': [[False, 'form']],
                    'target': 'new',
                    'res_id': sender_company.id,
                    'context': {'create': False},
                },
                button_text=_("Go to Company"),
            )

        xml_data = {
            'tax_payer_reg_code': sender_company.company_registry,
            # Not needed when uploaded personally, since you logged in at the Estonian government platform with your ID
            'submitter_person_code': '',
            'year': date_to.year,
            'month': date_to.month,
            'declaration_type': 1,  # Normal period
            'sale_lines': [],
            'purchase_lines': [],
        }

        # Tax report (KMD report)
        kmd_lines = report._get_lines(options)
        tax_line_prefix = 'l10n_ee.tax_report_line_'
        tax_line_numbers = ('1', '1_1', '2', '2_1', '3', '3_1', '3_1_1', '3_2', '3_2_1',
                            '5', '5_1', '5_2', '5_3', '5_3_cars', '5_4', '5_4_cars',
                            '6', '6_1', '7', '7_1', '8', '9', '10', '11')
        tax_line_mapping = {
            self.env.ref(tax_line_prefix + line_number).id: f'line_{line_number}' for line_number in tax_line_numbers
        }
        colexpr_to_idx = {col['expression_label']: idx for idx, col in enumerate(options.get('columns', []))}
        currency = self.env.company.currency_id

        for line in kmd_lines:
            if 'report_line_id' not in line['columns'][0]:
                continue
            line_id = line['columns'][0]['report_line_id']
            if line_id not in tax_line_mapping:
                continue
            xml_variable = tax_line_mapping[line_id]
            balance = line['columns'][colexpr_to_idx['balance']]['no_format']
            if balance and xml_variable.endswith('_cars'):  # line indicating number of cars
                xml_data[xml_variable] = f"{balance:.0f}"
            elif balance:
                xml_data[xml_variable] = float_repr(currency.round(balance), currency.decimal_places)

        # Loop through Part A and then Part B of the KMD INF, adding the lines to the sales or purchase subsection
        report_export_mapping = {
            'kmd_inf_report_part_a': 'sale_lines',
            'kmd_inf_report_part_b': 'purchase_lines'
        }
        for kmd_inf_part, export_section in report_export_mapping.items():
            # In case the module is not upgraded in stable, this ensures the xml is generated without errors
            kmd_inf_report = self.env.ref(f'l10n_ee_reports.{kmd_inf_part}', raise_if_not_found=False) or self.env.ref('l10n_ee_reports.kmd_inf_report')
            kmd_inf_report_options = kmd_inf_report.get_options(previous_options={**options, 'unfold_all': True})
            kmd_inf_lines = kmd_inf_report._get_lines(kmd_inf_report_options)

            for line in kmd_inf_lines:
                # The grouping lines do not need to be included in the KMD INF, since they do not represent invoice values.
                if not line['groupby']:
                    annex_line = {}
                    for col in line['columns']:
                        label = col['expression_label']
                        value = col['no_format']
                        if col['figure_type'] == 'monetary':
                            if value:
                                value = float_repr(currency.round(value), currency.decimal_places)
                        elif col['figure_type'] == 'date':
                            value = format_date(self.env, value, date_format='yyyy-MM-dd')
                        annex_line[label] = value
                    xml_data[export_section].append(annex_line)

        xml_content = self.env['ir.qweb']._render('l10n_ee_reports.vat_report_xml', values=xml_data)
        tree = etree.fromstring(xml_content)
        formatted_xml = etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='UTF-8')

        return {
            'file_name': report.get_default_report_filename(options, 'xml'),
            'file_content': formatted_xml,
            'file_type': 'xml',
        }


class EstonianKmdInfReportCustomHandler(models.AbstractModel):
    _name = 'l10n_ee.kmd.inf.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Estonian KMD INF Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        if report == self.env.ref('l10n_ee_reports.kmd_inf_report_part_a', raise_if_not_found=False):
            # Part A grouped lines display no information, hence part A should be unfolded by default
            options['unfold_all'] = options['export_mode'] == 'print' or previous_options.get('unfold_all', True) if previous_options else True

    def _custom_line_postprocessor(self, report, options, lines):
        """ Change label for grouping lines in the result of the report's _get_lines(),
        indicating the VAT rate and the special procedure of the line.
        """
        lines = super()._custom_line_postprocessor(report, options, lines)
        if report == self.env.ref('l10n_ee_reports.kmd_inf_report_part_a', raise_if_not_found=False):
            for line in lines:
                if not line['groupby']:
                    row_names = {
                        '5': 'VAT 5%',
                        '5erikord': 'VAT 5% special procedure §41/42',
                        '9': 'VAT 9%',
                        '9erikord': 'VAT 9% special procedure §41/42',
                        '20': 'VAT 20%',
                        '20erikord': 'VAT 20% special procedure §41/42',
                        '22': 'VAT 22%',
                        '22erikord': 'VAT 22% special procedure §41/42'
                    }
                    line['name'] = row_names[line['columns'][5]['no_format']]  # column 'tax_rate'
                    comments = line['columns'][7]['no_format']  # column 'comments'
                    line['name'] += ' special procedure §41^1' if '2' in comments else ''
        return lines

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings):
        warning_partners = self._get_warning_partners(report, options)
        if warning_partners:
            warnings['l10n_ee_reports.kmd_inf_listing_missing_partners_warning'] = {
                'alert_type': 'warning',
                'count': len(warning_partners),
                'ids': warning_partners,
            }

    ####################################################
    # WARNING
    ####################################################

    def action_warning_partners(self, options, params):
        view_id = (
                self.env.ref('l10n_ee_reports.res_partner_kmd_inf_warning_view_tree', raise_if_not_found=False) or
                self.env.ref('base.view_partner_tree')  # In case the DB was not updated.
        ).id
        return {
            'name': _('Missing partners'),
            'res_model': 'res.partner',
            'views': [(view_id, 'list')],
            'domain': [('id', 'in', params['ids'])],
            'type': 'ir.actions.act_window',
        }

    def _get_warning_partners(self, report, options):
        """
        Returns a list of partner IDs that should potentially have been included in the report. Those are partners
        with a move with taxable supply at 22%, 20%, 9% or 5% in the selected period and no VAT, if:
        - For part A, if there is no country_id or if country_id is EE
        - For part B, if there is no country_id
        """
        query = report._get_report_query(options, 'strict_range')

        if report == self.env.ref('l10n_ee_reports.kmd_inf_report_part_a', raise_if_not_found=False):
            move_type = "('out_invoice', 'out_refund')"
            add_where_clause = "AND (res_partner.country_id IS NULL OR res_country.code = 'EE')"
        else:
            move_type = "('in_invoice', 'in_refund')"
            add_where_clause = "AND res_partner.country_id IS NULL"

        tax_group_xmlids = ['tax_group_vat_22', 'tax_group_vat_20', 'tax_group_vat_9', 'tax_group_vat_5']
        tax_group_ids = [tax_group.id for xmlid in tax_group_xmlids
                         if (tax_group := self.env.ref(f"account.{self.env.company.id}_{xmlid}", raise_if_not_found=False))]

        sql_query = SQL("""
            SELECT DISTINCT account_move_line__move_id.commercial_partner_id
            FROM %(table_references)s
            LEFT JOIN res_partner ON res_partner.id = account_move_line__move_id.commercial_partner_id
            LEFT JOIN res_country ON res_country.id = res_partner.country_id
            LEFT JOIN account_tax ON account_move_line.tax_line_id = account_tax.id
            LEFT JOIN account_tax_group ON account_tax_group.id = account_tax.tax_group_id
            WHERE %(search_condition)s
                AND account_tax_group.id = ANY(%(tax_group_ids)s)
                AND account_move_line__move_id.move_type IN %(move_type)s
                AND res_partner.vat IS NULL
                %(add_where_clause)s
        """,
            table_references=query.from_clause,
            search_condition=query.where_clause,
            tax_group_ids=tax_group_ids,
            move_type=SQL(move_type),
            add_where_clause=SQL(add_where_clause),
        )
        self.env.cr.execute(sql_query)
        return [r[0] for r in self.env.cr.fetchall()]

    ####################################################
    # RETURN RESULT FUNCTION
    ####################################################

    def build_result_dict_kmd_inf_a(self, query_res_lines, current_groupby):
        if current_groupby == 'id':
            res = query_res_lines[0]
            return {
                'partner_reg_code': res['buyer_reg_code'],
                'partner_name': res['buyer_name'],
                'invoice_number': res['invoice_number'],
                'invoice_date': res['invoice_date'],
                'invoice_total': res['invoice_total'],
                'tax_rate': res['tax_rate'],
                'sum_for_rate_in_period': res['sum_rate_period'],
                'comments': res['comments'],
            }
        return {
            'partner_reg_code': None,
            'partner_name': None,
            'invoice_number': None,
            'invoice_date': None,
            'invoice_total': 0,
            'tax_rate': 0,
            'sum_for_rate_in_period': 0,
            'comments': None,
        }

    def build_result_dict_kmd_inf_b(self, query_res_lines, current_groupby):
        if current_groupby:
            res = query_res_lines[0]
            return {
                'partner_reg_code': res['seller_reg_code'],
                'partner_name': res['seller_name'],
                'invoice_number': res['invoice_number'],
                'invoice_date': res['invoice_date'],
                'invoice_total': res['invoice_total'],
                'vat_in_period': res['vat_in_period'],
                'comments': res['comments'],
            }
        return {
            'partner_reg_code': None,
            'partner_name': None,
            'invoice_number': None,
            'invoice_date': None,
            'invoice_total': 0,
            'vat_in_period': 0,
            'comments': None,
        }

    ####################################################
    # CUSTOM ENGINES
    ####################################################

    def _report_custom_engine_kmd_inf_a(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        """ Part A contains information about invoices issued.

            Only invoices containing supply taxable at the rate of 22%, 20%, 9% or 5% are included. Different lines are
            used for supply taxable under the general procedure, the special procedure provided for in § 41 and § 42 of
            the Value-Added Tax Act (special code 1) and the special procedure provided for in § 41^1 (special code 2).
            Furthermore, if the invoice contains the supply taxable at the rate of 0% or tax-exempt supply or if the
            invoice contains the supply that is taxable at two or more different tax rates, special code 3 is used.
        """
        return self._report_custom_engine_kmd_inf(options, current_groupby, next_groupby, 'a')

    def _report_custom_engine_kmd_inf_b(self, expressions, options, date_scope, current_groupby, next_groupby, offset=0, limit=None, warnings=None):
        """ Part B contains information about invoices received.

            Only invoices containing supply declared in field 5 of the Form KMD are included. Each line corresponds to
            one invoice. Special code 11 is used for partial deduction of input value added tax according to § 29 (4),
            § 30 or § 32 of the VAT Act. Special code 12 is used for the acquisition of goods subject to VAT under the
            special arrangements provided for in § 41^1 of the VAT Act.
        """
        return self._report_custom_engine_kmd_inf(options, current_groupby, next_groupby, 'b')

    def _report_custom_engine_kmd_inf(self, options, current_groupby, next_groupby, kmd_inf_part):
        """ Builds the query and dictionary necessary to display the report lines for the KMD INF.

        The query for part A and part B are built separately, as they have different columns and group by.
        In both cases, only invoices containing a 22%, 9% or 5% tax (and 20% until end of 2025) are displayed.
        Invoices from/to foreign companies not having a register code in Estonia are excluded. Both parts also
        include a column displaying the company registry number of the partner as well as their name, number of
        invoice, date of invoice, and the special code providing comments in the form of one or more code.
        """
        # Build parameters for query
        report = self.env['account.report'].browse(options['report_id'])
        report._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))
        query = report._get_report_query(options, 'strict_range')

        # Additional lines in the query depending on the group by
        if current_groupby == 'id':
            # At the lowest level, we want to group invoice lines by the tax (excluding 0%) and by whether it
            # is under one of the two types of special procedure. So we combine the lines of the same tax and type
            # under the same move_line_id as a grouping key.
            select_from_groupby = "MIN(account_move_line.id) AS grouping_key,"
            groupby_clause = ''
        elif current_groupby:
            select_from_groupby = f"account_move_line.{current_groupby} AS grouping_key,"
            groupby_clause = f", account_move_line.{current_groupby}"
        else:
            select_from_groupby = SQL()
            groupby_clause = SQL()

        if kmd_inf_part == 'a':
            # In part A, the invoice total without VAT and the taxable supply presented in the fields 1, 1^1,
            # 2 and 2^1 of Form KMD (VAT report) are displayed. We exclude partners whose Tax ID is / and exclude
            # foreigners who have a Tax ID not starting by EE.
            xmlids = ['tax_report_line_1_tag', 'tax_report_line_1_1_tag', 'tax_report_line_2_tag', 'tax_report_line_2_1_tag']

            sql_query = SQL("""
                WITH multiple_tax_moves AS (
                    SELECT account_move_line.move_id
                    FROM account_move_line
                    LEFT JOIN account_move_line_account_tax_rel AS move_tax_rel ON move_tax_rel.account_move_line_id = account_move_line.id
                    LEFT JOIN account_tax ON account_tax.id = move_tax_rel.account_tax_id
                    WHERE account_move_line.display_type = 'product'
                    GROUP BY account_move_line.move_id
                    HAVING COUNT(DISTINCT account_tax.amount) > 1
                        OR SUM(CASE WHEN account_tax.amount = 0 OR account_tax.amount IS NULL THEN 1 ELSE 0 END) > 0
                )

                SELECT
                    %(select_from_groupby)s
                    res_partner.company_registry AS buyer_reg_code,
                    res_partner.name AS buyer_name,
                    account_move_line__move_id.name AS invoice_number,
                    account_move_line__move_id.invoice_date AS invoice_date,
                    account_move_line__move_id.amount_untaxed_signed AS invoice_total,
                    -- the balance of outgoing moves are inverted, so multiply sum by -1
                    -SUM(
                        -- if special code is 2, column sum_rate_period should not be filled
                        CASE WHEN tag.id = ANY(%(tag_ids)s) AND (base_tax.l10n_ee_kmd_inf_code <> '2' OR base_tax.l10n_ee_kmd_inf_code IS NULL)
                        THEN account_move_line.balance
                        ELSE 0 END
                    ) AS sum_rate_period,
                    -- special code depends on the tax's l10n_ee_kmd_inf_code and on number of distinct tax rates in the move
                    CONCAT_WS(
                        ', ',
                        STRING_AGG(DISTINCT base_tax.l10n_ee_kmd_inf_code, ', '),
                        CASE WHEN account_move_line__move_id.id IN (SELECT move_id FROM multiple_tax_moves) THEN '3' END
                    ) AS comments,
                    base_tax.tax_rate

                FROM %(table_references)s

                LEFT JOIN res_partner ON res_partner.id = account_move_line__move_id.commercial_partner_id
                LEFT JOIN res_country ON res_country.id = res_partner.country_id
                LEFT JOIN account_account_tag_account_move_line_rel AS tag_move_line_rel ON tag_move_line_rel.account_move_line_id = account_move_line.id
                LEFT JOIN account_account_tag AS tag ON tag.id = tag_move_line_rel.account_account_tag_id
                LEFT JOIN account_move_line_account_tax_rel AS move_tax_rel ON account_move_line.id = move_tax_rel.account_move_line_id
                LEFT JOIN (
                    SELECT
                        tax.id,
                        tax.l10n_ee_kmd_inf_code,
                        CASE WHEN tax.l10n_ee_kmd_inf_code = '1' THEN CONCAT(tax.amount::INTEGER, 'erikord') ELSE (tax.amount::INTEGER)::VARCHAR END AS tax_rate
                    FROM account_tax as tax
                    LEFT JOIN account_tax_group AS tax_group ON tax_group.id = tax.tax_group_id
                ) base_tax ON move_tax_rel.account_tax_id = base_tax.id

                WHERE
                    %(search_condition)s
                    AND account_move_line__move_id.move_type IN ('out_invoice', 'out_refund')
                    AND tax_rate != '0'
                    AND res_partner.is_company
                    AND res_partner.vat != '/'
                    AND (res_country.code = 'EE' OR res_partner.vat ILIKE %(country_code)s)

                GROUP BY
                    res_partner.id,
                    account_move_line__move_id.id,
                    tax_rate,
                    l10n_ee_kmd_inf_code
                    %(groupby_clause)s
            """,
                select_from_groupby=SQL(select_from_groupby),
                tag_ids=self._get_tag_ids_from_report_lines(xmlids),
                table_references=query.from_clause,
                search_condition=query.where_clause,
                country_code='EE%',
                groupby_clause=SQL(groupby_clause),
        )
        else:
            # In part B, the invoice total with VAT and the input VAT amount presented in the field 5 of Form KMD are
            # displayed. We exclude only partners whose Tax ID does not start by EE.
            xmlids = ['tax_report_line_5_tag', 'tax_report_line_5_1_tag', 'tax_report_line_5_2_tag', 'tax_report_line_5_3_tag', 'tax_report_line_5_4_tag']

            sql_query = SQL("""
                SELECT
                    %(select_from_groupby)s
                    res_partner.company_registry AS seller_reg_code,
                    res_partner.name AS seller_name,
                    COALESCE(account_move_line__move_id.ref, account_move_line__move_id.name) AS invoice_number,
                    account_move_line__move_id.invoice_date AS invoice_date,
                    -- invoice_total (part B) needs to be positive for bills (negative for refunds) and include reverse charge taxes (remove amount from negative repartition lines)
                    -account_move_line__move_id.amount_total_signed - SUM(
                        CASE WHEN account_tax.l10n_ee_kmd_inf_code = '12' AND tax_repartition.factor_percent < 0 THEN account_move_line.balance ELSE 0 END
                    ) AS invoice_total,
                    -- input vat in period only includes lines with tax tags corresponding to field 5 of KMD form
                   SUM(CASE WHEN account_move_line.display_type = 'tax' AND tag.id = ANY(%(tag_ids)s) THEN account_move_line.balance ELSE 0 END) AS vat_in_period,
                   STRING_AGG(DISTINCT account_tax.l10n_ee_kmd_inf_code, ', ') AS comments

                FROM %(table_references)s

                LEFT JOIN res_partner ON res_partner.id = account_move_line__move_id.commercial_partner_id
                LEFT JOIN res_country ON res_country.id = res_partner.country_id
                LEFT JOIN account_account_tag_account_move_line_rel AS tag_move_line_rel ON tag_move_line_rel.account_move_line_id = account_move_line.id
                LEFT JOIN account_account_tag AS tag ON tag.id = tag_move_line_rel.account_account_tag_id
                LEFT JOIN account_tax ON account_move_line.tax_line_id = account_tax.id
                LEFT JOIN account_tax_repartition_line AS tax_repartition ON account_move_line.tax_repartition_line_id = tax_repartition.id

                WHERE
                    %(search_condition)s
                    AND account_move_line__move_id.move_type IN ('in_invoice', 'in_refund')
                    AND (res_country.code = 'EE' OR res_partner.vat ILIKE %(country_code)s)

                GROUP BY
                    res_partner.id,
                    account_move_line__move_id.id
                    %(groupby_clause)s

                HAVING
                    SUM(CASE WHEN account_move_line.display_type = 'tax' AND tag.id = ANY(%(tag_ids)s) THEN account_move_line.balance ELSE 0 END) != 0
            """,
                select_from_groupby=SQL(select_from_groupby),
                tag_ids=self._get_tag_ids_from_report_lines(xmlids),
                table_references=query.from_clause,
                search_condition=query.where_clause,
                country_code='EE%',
                groupby_clause=SQL(groupby_clause),
            )

        self.env.cr.execute(sql_query)
        query_res_lines = self.env.cr.dictfetchall()

        build_functions = {
            'a': self.build_result_dict_kmd_inf_a,
            'b': self.build_result_dict_kmd_inf_b
        }
        # Group result per grouping key and call function to build result dictionaries
        if not current_groupby:
            return build_functions[kmd_inf_part](query_res_lines, current_groupby)

        result = []
        all_res_per_grouping_key = {}
        for query_res in query_res_lines:
            grouping_key = query_res['grouping_key']
            all_res_per_grouping_key.setdefault(grouping_key, []).append(query_res)

        for grouping_key, query_res_lines in all_res_per_grouping_key.items():
            result.append((grouping_key, build_functions[kmd_inf_part](query_res_lines, current_groupby)))

        return result

    def _report_custom_engine_kmd_inf_common(self, options, current_groupby, next_groupby, kmd_inf_part):
        # Deprecated function kept in stable
        warnings.warn(
            _("This version of the KMD INF report is deprecated. Upgrade the module 'Estonia - Accounting' to have access to the updated report."),
            DeprecationWarning
        )

        return {
            'partner_reg_code': None,
            'partner_name': None,
            'invoice_number': None,
            'invoice_date': None,
            'invoice_total': None,
            'tax_rate': None,
            'sum_for_rate_in_period': None,
            'vat_in_period': None,
            'comments': None,
        }

    ####################################################
    # HELPER FUNCTIONS
    ####################################################

    def _get_tag_ids_from_report_lines(self, report_lines_xmlids):
        return list({
            tag_id
            for xmlid in report_lines_xmlids
            for tag_id in self.env.ref(f'l10n_ee.{xmlid}')._get_matching_tags().ids
        })

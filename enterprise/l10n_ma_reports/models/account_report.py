from odoo import api, fields, models, _
from odoo.tools import  date_utils

L10N_MA_CUSTOMS_VAT_ICE = '20727020'


class MoroccanTaxReportCustomHandler(models.AbstractModel):
    _name = 'l10n_ma.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Moroccan Tax Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options.setdefault('buttons', []).append({
            'name': _('XML'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'l10n_ma_reports_export_vat_to_xml',
            'file_export_type': _('XML'),
        })

    @api.model
    def _l10n_ma_prepare_vat_report_header_values(self, company, bills, period_type, date_from):
        template_vals = {
            'errors': {},
            'year': str(date_from.year),
        }
        if period_type == 'trimester':
            template_vals['period'] = date_utils.get_quarter_number(date_from)
            template_vals['regime_code'] = '2'
        else:
            template_vals['period'] = date_from.month
            template_vals['regime_code'] = '1'

        template_vals['vat_id'] = company.vat

        #  Check for different errors in the report
        errored_vendors = bills.partner_id.filtered(lambda p: (not p.vat or not p.company_registry) and p.country_code == 'MA')
        self._check_l10n_ma_report_errors(errored_vendors, period_type, template_vals, company)
        return template_vals

    def _check_l10n_ma_report_errors(self, errored_vendors, period_type, template_vals, company):
        if errored_vendors:
            template_vals['errors']['partner_vat_ice_missing'] = {
                'message': _('There are partners located in Morocco without any ICE and/or Tax ID specified.'
                             ' The resulting XML will not contain the associated vendor bills.'),
                'action_text': _('View Partner(s)'),
                'action': errored_vendors._get_records_action(name=_('Invalid Partner(s)')),
            }

        if period_type not in {'monthly', 'trimester'}:
            template_vals['errors']['period_invalid'] = {
                'message': _('This report only supports monthly and quarterly periods.'),
                'level': 'danger',
            }

        if not company.vat:
            template_vals['errors']['company_vat_missing'] = {
                'message': _('Company %s has no VAT number and it is required to generate the XML file.', company.name),
                'action_text': _('View Company/ies'),
                'action': company.partner_id._get_records_action(name=_('Invalid Company/ies')),
                'level': 'danger',
            }

    @api.model
    def _l10n_ma_prepare_vat_report_bill_values(self, bills, prorata_value):
        template_vals = {
            'bills': [],
        }

        if prorata_value:
            template_vals['prorata'] = prorata_value.value

        def group_taxes_ma(base_line, tax_data):
            tax = tax_data['tax']
            return {
                'amount': tax.amount,
                'amount_type': tax.amount_type,
            }

        index = 1
        for bill in bills:
            # In the case of a foreign partner we will fall back to the default value, if he is from morocco, he needs
            # to have a vat and ice number otherwise the move is ignored
            if not ((bill.partner_id.vat and bill.partner_id.company_registry) or bill.partner_id.country_code != 'MA'):
                continue

            tax_aggregates = bill._prepare_invoice_aggregated_taxes(grouping_key_generator=group_taxes_ma)
            bill_payments = bill._get_reconciled_payments()
            sign = -1 if bill.is_inbound() else 1
            payment_date = ''
            if bill_payments:
                payment_date = bill_payments.sorted(lambda p: p.date)[-1].date.strftime('%Y-%m-%d')

            for amount_details, tax_values in tax_aggregates['tax_details'].items():
                if amount_details['amount_type'] != 'percent':
                    continue
                template_vals['bills'].append({
                    'name': bill.name,
                    'sequence': index,
                    'base_amount': tax_values['base_amount'] * sign,
                    'tax_amount': tax_values['tax_amount'] * sign,
                    'total_amount': (tax_values['tax_amount'] + tax_values['base_amount']) * sign,
                    'partner_vat': bill.partner_id.vat if bill.partner_id.country_code == 'MA' else bill.partner_id.l10n_ma_customs_vat or L10N_MA_CUSTOMS_VAT_ICE,
                    'partner_name': bill.partner_id.name,
                    'partner_ice': bill.partner_id.company_registry or L10N_MA_CUSTOMS_VAT_ICE,
                    'tax_rate': amount_details['amount'] * sign,
                    'payment_method': bill.l10n_ma_reports_payment_method or '7',
                    'payment_date':  payment_date,
                    'invoice_date': bill.invoice_date.strftime('%Y-%m-%d'),
                })
                index += 1
        return template_vals

    @api.model
    def _l10n_ma_prepare_vat_report_values(self, options):
        date_from = fields.Date.from_string(options['date'].get('date_from'))
        date_to = fields.Date.from_string(options['date'].get('date_to'))
        period_type = options['tax_periodicity']['periodicity']
        company = self.env.company

        prorata_expression = self.env.ref('l10n_ma.l10n_ma_vat_d_prorata_pro')
        prorata_value = self.env['account.report.external.value'].search([
            ('target_report_expression_id', '=', prorata_expression.id),
            ('company_id', '=', company.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ], limit=1, order='date desc')

        bills = self.env['account.move'].search([
            ('move_type', 'in', self.env['account.move'].get_purchase_types()),
            ('invoice_date', '>=', date_from),
            ('invoice_date', '<=', date_to),
            ('state', '=', 'posted'),
        ])

        template_vals = self._l10n_ma_prepare_vat_report_header_values(company, bills, period_type, date_from)
        template_vals |= self._l10n_ma_prepare_vat_report_bill_values(bills, prorata_value)
        return template_vals

    @api.model
    def l10n_ma_reports_export_vat_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        template_values = self._l10n_ma_prepare_vat_report_values(options)
        return report._generate_file_data_with_error_check(
            options,
            self.env['ir.qweb']._render,
            {'values': template_values, 'template': 'l10n_ma_reports.l10n_ma_tax_report_template', 'file_type': 'xml'},
            template_values['errors'],
        )

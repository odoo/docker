from lxml import etree, objectify
from stdnum.cz.dic import compact

from odoo import fields, models, release, _
from odoo.tools import float_round


class CzechTaxReportCustomHandler(models.AbstractModel):
    _name = "l10n_cz.tax.report.handler"
    _inherit = "account.tax.report.handler"
    _description = "Czech Tax Report Custom Handler"

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options.setdefault('buttons', []).append({
            'name': _('XML'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'export_to_xml',
            'file_export_type': _('XML'),
        })

    def export_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        sender_company = report._get_sender_company_for_export(options)

        report_options = {**report.get_options({}), 'export_mode': 'file'}
        report_lines = report._get_lines(report_options)

        values = {}
        for line in report_lines:
            if not line['code']:
                continue
            values[line['code']] = {}
            for col in line['columns']:
                values[line['code']][col['expression_label']] = float_round(col['no_format'], precision_digits=0) if col['no_format'] is not None else 0

        data = {
            'odoo_version': release.version,
            'company_name': sender_company.name,
            'company_vat': compact(sender_company.vat),
            'sender_company': sender_company,
            'date': fields.Date.today(),
            **values,
        }
        xml_content = self.env['ir.qweb']._render('l10n_cz_reports.cz_tax_report_template', values=data)
        tree = objectify.fromstring(xml_content)
        formatted_xml = etree.tostring(tree, pretty_print=True, xml_declaration=True, encoding='UTF-8')

        return {
            'file_name': report.get_default_report_filename(options, 'xml'),
            'file_content': formatted_xml,
            'file_type': 'xml',
        }

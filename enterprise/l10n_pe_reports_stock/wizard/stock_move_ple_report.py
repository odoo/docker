import base64
import csv
import re

from dateutil.relativedelta import relativedelta
from io import StringIO
from werkzeug.urls import url_encode

from odoo import api, fields, models
from odoo.tools import groupby
from odoo.exceptions import UserError


class StockMovePleReport(models.TransientModel):
    _name = 'l10n_pe.stock.ple.wizard'
    _description = 'Wizard to generate Stock Move PLE reports for PE'

    @api.model
    def default_get(self, fields_list):
        results = super().default_get(fields_list)
        if self.env.company.country_code != 'PE':
            raise UserError('This option is only available for Peruvian companies.')
        date_from = fields.Date.today().replace(day=1)
        results['date_from'] = date_from
        results['date_to'] = date_from + relativedelta(months=1, days=-1)
        return results

    date_from = fields.Date(
        required=True,
        help="Choose a date from to get the PLE reports at that date",
    )
    date_to = fields.Date(
        required=True,
        help="Choose a date to get the PLE reports at that date",
    )
    report_data = fields.Binary('Report file', readonly=True, attachment=False)
    report_filename = fields.Char(string='Filename', readonly=True)
    mimetype = fields.Char(string='Mimetype', readonly=True)

    def get_ple_report_12_1(self):
        return self.get_ple_report('1201')

    def get_ple_report_13_1(self):
        return self.get_ple_report('1301')

    def get_ple_report(self, report_number):
        data = self._get_ple_report_content(report_number)
        has_data = "1" if data else "0"
        filename = "LE%s%s%02d00%s00001%s11.txt" % (
            self.env.company.vat, self.date_from.year, self.date_from.month, report_number, has_data)
        self.write({
            'report_data': base64.b64encode(data.encode()),
            'report_filename': filename,
            'mimetype': 'application/txt',
        })
        return {
            'type': 'ir.actions.act_url',
            'url':  '/web/content/?' + url_encode({
                'model': self._name,
                'id': self.id,
                'filename_field': 'report_filename',
                'field': 'report_data',
                'download': 'true'
            }),
            'target': 'new'
        }

    @api.model
    def _get_serie_folio(self, number):
        values = {"serie": "", "folio": ""}
        number_matchs = list(re.finditer("\\d+", number or ""))
        if number_matchs:
            last_number_match = number_matchs[-1]
            values["serie"] = number[: last_number_match.start()].replace("-", "") or ""
            values["folio"] = last_number_match.group() or ""
        return values

    def _get_ple_report_content(self, report):
        def _get_stock_valuation(category):
            cost_method = self.env['product.category'].browse(category).property_cost_method
            return {'average': '1', 'fifo': '2', 'standard': '3'}.get(cost_method, '')

        data = []
        period = '%s%s00' % (self.date_from.year, str(self.date_from.month).zfill(2))
        lines_data = self._get_ple_reports_data()
        count = 0
        for _move_id, line_vals in groupby(lines_data, lambda line: line["move_id"]):
            # Only consider the first line.
            # If an entry was invoiced in 2 or more records, only get the values from the first invoice
            line = line_vals[0]
            serie_folio = self._get_serie_folio(line['move_name'] or line['move_name_p'] or '')
            date = (line['invoice_date'] or line['invoice_date_p'] or line['date']).strftime('%d/%m/%Y') if (line['invoice_date'] or line['invoice_date_p'] or line['date']) else ''
            values = {
                'period': period,
                'cuo': str(line['svl_name'] or count).replace('/', '').zfill(6),
                'number': 'M1',  # The first digit should be 'M' to denote entries for movements or adjustments within the month. Therefore, 'M1' indicates this is the first such entry.
                'establishment': line['l10n_pe_anexo_establishment_code'] or '0000',
                'catalogue': '1',  # Only supported 1 because We use Unspsc
                'type_of_existence': (line['l10n_pe_type_of_existence'] or '99').zfill(2),
                'default_code': (line['default_code'] or '').replace('_', '')[:24],
                'catalogue_used': '1',  # Only supported 1 because We use Unspsc
                'unspsc': line['unspsc_code'],
                'date': date,
                'document_type': line['document_type'] or line['document_type_p'] or '00',
                'serie': serie_folio['serie'].replace(' ', '').replace('/', '') or '0',
                'folio': serie_folio['folio'].replace(' ', '') or '0',
                'operation_type': (line['l10n_pe_operation_type'] or '99').zfill(2),
                'product': line['product_name']['en_US'],
                'uom': line['l10n_pe_edi_measure_unit_code'],
            }
            count += 1
            if report == '1201':
                values.update({
                    'qty_in': line['quantity'] if line['quantity'] > 0 else '0.00',
                    'qty_out': line['quantity'] if line['quantity'] <= 0 else '0.00',
                    'state': '1',
                })
                data.append(values)
                continue
            values.update({
                'valuation': _get_stock_valuation(line['category']),
                'qty_in': line['quantity'] if line['quantity'] > 0 else '0.00',
                'cost_in': line['unit_cost'] if line['unit_cost'] > 0 else '0.00',
                'value_in': line['value'] if line['value'] > 0 else '0.00',
                'qty_out': abs(line['quantity']) if line['quantity'] <= 0 else '0.00',
                'cost_out': (line['unit_cost'] or '0.00') if line['unit_cost'] <= 0 else '0.00',
                'value_out': line['value'] if line['value'] <= 0 else '0.00',
                'remaining': abs(line['remaining_qty']),
                'unit_cost_final': abs((line['remaining_value'] or 0) / (line['remaining_qty'] or 1)) or '0.00',
                'value': abs(line['remaining_value'] or 0),
                'state': '1',
            })
            data.append(values)
        if not data:
            return ''
        csv.register_dialect("pipe_separator", delimiter="|", skipinitialspace=True, lineterminator='|\n')
        output = StringIO()
        writer = csv.DictWriter(output, dialect="pipe_separator", fieldnames=data[0].keys())
        writer.writerows(data)
        txt_result = output.getvalue()
        return txt_result

    def _get_ple_reports_data(self):
        domain = [
            ('state', '=', 'done'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('company_id', '=', self.env.company.id),
            '|',
            ('location_id.usage', 'in', ('supplier', 'customer', 'inventory', 'production')),
            ('location_dest_id.usage', 'in', ('supplier', 'customer', 'inventory', 'production')),
        ]

        query = self.env['stock.move']._where_calc(domain)
        query.left_join('stock_move', 'picking_id', 'stock_picking', 'id', 'picking')
        query.left_join('stock_move', 'location_id', 'stock_location', 'id', 'location')
        query.left_join('stock_move__location', 'warehouse_id', 'stock_warehouse', 'id', 'warehouse')
        query.left_join('stock_move', 'product_uom', 'uom_uom', 'id', 'uom')
        query.left_join('stock_move', 'product_id', 'product_product', 'id', 'product')
        query.left_join('stock_move__product', 'product_tmpl_id', 'product_template', 'id', 'template')
        query.left_join('stock_move__product__template', 'categ_id', 'product_category', 'id', 'category')
        query.left_join('stock_move__product__template', 'unspsc_code_id', 'product_unspsc_code', 'id', 'unspsc')
        query.join('stock_move', 'id', 'stock_valuation_layer', 'stock_move_id', 'svl')
        query.left_join('stock_move__svl', 'account_move_id', 'account_move', 'id', 'account_move')

        # Section to get the invoice related for SO
        query.left_join('stock_move', 'sale_line_id', 'sale_order_line', 'id', 'sol')
        query.left_join('stock_move__sol', 'id', 'sale_order_line_invoice_rel', 'order_line_id', 'solr')
        query.left_join('stock_move__sol__solr', 'invoice_line_id', 'account_move_line', 'id', 'aml')
        query.left_join('stock_move__sol__solr__aml', 'move_id', 'account_move', 'id', 'am')

        # Section to get the invoice related for PO
        query.left_join('stock_move', 'purchase_line_id', 'purchase_order_line', 'id', 'pol')
        query.left_join('stock_move__pol', 'id', 'account_move_line', 'purchase_line_id', 'aml_p')
        query.left_join('stock_move__pol__aml_p', 'move_id', 'account_move', 'id', 'am_p')

        query.left_join('stock_move__sol__solr__aml__am', 'l10n_latam_document_type_id', 'l10n_latam_document_type', 'id', 'doctype')
        query.left_join('stock_move__pol__aml_p__am_p', 'l10n_latam_document_type_id', 'l10n_latam_document_type', 'id', 'doctype_p')
        query.order = "stock_move.id, stock_move__svl.id"

        qu = query.select('stock_move.id',
                          'stock_move.date',
                          'stock_move__picking.id AS picking_id',
                          'stock_move.id AS move_id',
                          'stock_move__svl__account_move.name AS svl_name',
                          'stock_move__location__warehouse.l10n_pe_anexo_establishment_code',
                          'stock_move__product__template__category.id AS category',
                          'stock_move__product.default_code',
                          'stock_move__product__template.l10n_pe_type_of_existence',
                          'stock_move__product__template__unspsc.code AS unspsc_code',
                          'stock_move__sol__solr__aml__am.invoice_date',
                          'stock_move__pol__aml_p__am_p.invoice_date AS invoice_date_p',
                          'stock_move__sol__solr__aml__am__doctype.code AS document_type',
                          'stock_move__pol__aml_p__am_p__doctype_p.code AS document_type_p',
                          'stock_move__sol__solr__aml__am.name AS move_name',
                          'stock_move__pol__aml_p__am_p.name AS move_name_p',
                          'stock_move__picking.l10n_pe_operation_type',
                          'stock_move__product__template.name AS product_name',
                          'stock_move__uom.l10n_pe_edi_measure_unit_code',
                          'stock_move__svl.quantity',
                          'stock_move__svl.unit_cost',
                          'stock_move__svl.value',
                          'stock_move__svl.remaining_qty',
                          'stock_move__svl.remaining_value',
                          )

        self.env.cr.execute(qu)
        return self._cr.dictfetchall()

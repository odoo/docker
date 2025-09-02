from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged, Form

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountInvoice(TestAccountReportsCommon):
    @classmethod
    @TestAccountReportsCommon.setup_chart_template('es_pymes')
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.account_revenue = self.env['account.account'].search(
            [('account_type', '=', 'income')], limit=1)
        self.company = self.env.user.company_id
        self.partner_es = self.env['res.partner'].create({
            'name': 'España',
            'country_id': self.env.ref('base.es').id,
        })
        self.partner_eu = self.env['res.partner'].create({
            'name': 'France',
            'country_id': self.env.ref('base.fr').id,
        })

    def create_invoice(self, partner_id):
        f = Form(self.env['account.move'].with_context(default_move_type="out_invoice"))
        f.partner_id = partner_id
        with f.invoice_line_ids.new() as line:
            line.product_id = self.env.ref("product.product_product_4")
            line.quantity = 1
            line.price_unit = 100
            line.name = 'something'
            line.account_id = self.account_revenue
        invoice = f.save()
        return invoice

    def test_mod347_default_include_domestic_invoice(self):
        invoice = self.create_invoice(self.partner_es)
        self.assertEqual(invoice.l10n_es_reports_mod347_invoice_type, 'regular')

    def test_mod347_exclude_intracomm_invoice(self):
        invoice = self.create_invoice(self.partner_eu)
        self.assertFalse(invoice.l10n_es_reports_mod347_invoice_type)

    @freeze_time('2019-12-31')
    def test_mod347_include_receipts(self):
        self.init_invoice(
            'out_receipt',
            partner=self.partner_es,
            amounts=[5000],
            invoice_date='2019-12-31',
            post=True,
        )

        report = self.env.ref('l10n_es_reports.mod_347')
        options = self._generate_options(
            report, "2019-12-31", "2019-12-31", default_options={"unfold_all": True}
        )

        lines = report._get_lines(options)
        lines = lines[1:3] + lines[-2:]
        self.assertLinesValues(
            lines,
            [0, 1],
            [
                ["Total number of persons and entities",                         1],
                ["España",                                                       1],
                ["B - Sales of goods and services greater than 3.005,06 €", 5000.0],
                ["España",                                                  5000.0],
            ],
            options,
        )

    @freeze_time('2019-12-31')
    def test_mod347_not_affected_by_payments(self):
        invoice = self.init_invoice(
            'out_invoice',
            partner=self.partner_es,
            amounts=[5000],
            invoice_date='2019-12-31',
            post=True,
        )

        report = self.env.ref('l10n_es_reports.mod_347')
        options = self._generate_options(
            report, "2019-12-31", "2019-12-31", default_options={"unfold_all": True}
        )

        expected_lines = [
            ["Total number of persons and entities",                         1],
            ["España",                                                       1],
            ["B - Sales of goods and services greater than 3.005,06 €", 5000.0],
            ["España",                                                  5000.0],
        ]

        lines = report._get_lines(options)
        lines = lines[1:3] + lines[-2:]
        self.assertLinesValues(
            lines,
            [0, 1],
            expected_lines,
            options,
        )

        self.env['account.payment.register'].with_context(
            active_ids=invoice.ids, active_model='account.move'
        ).create({})._create_payments()

        lines = report._get_lines(options)
        lines = lines[1:3] + lines[-2:]
        self.assertLinesValues(
            lines,
            [0, 1],
            expected_lines,
            options,
        )

    @freeze_time('2019-12-31')
    def test_vat_record_books_with_receipts(self):
        self.init_invoice(
            'out_receipt',
            partner=self.partner_es,
            amounts=[5000],
            invoice_date='2019-12-31',
            taxes=self.company_data['default_tax_sale'],
            post=True,
        )
        receipt = self.init_invoice(
            'out_receipt',
            amounts=[3000],
            invoice_date='2019-12-31',
            taxes=self.company_data['default_tax_sale'],
        )
        receipt.partner_id = False
        receipt.action_post()

        report = self.env.ref('account.generic_tax_report')
        options = self._generate_options(
            report, "2019-12-31", "2019-12-31", default_options={"unfold_all": True}
        )

        vat_record_books = self.env['l10n_es.libros.registro.export.handler'].export_libros_de_iva(options)['file_content']

        self._test_xlsx_file(vat_record_books, {
            0: ('Autoliquidación', '', 'Actividad', '', '', 'Tipo de Factura', 'Concepto de Ingreso', 'Ingreso Computable', 'Fecha Expedición', 'Fecha Operación', 'Identificación de la Factura', '', '', 'NIF Destinario', '', '', 'Nombre Destinario', 'Clave de Operación', 'Calificación de la Operación', 'Operación Exenta', 'Total Factura', 'Base Imponible', 'Tipo de IVA', 'Cuota IVA Repercutida', 'Tipo de Recargo eq.', 'Cuota Recargo eq.', 'Cobro (Operación Criterio de Caja de IVA y/o artículo 7.2.1º de Reglamento del IRPF)', '', '', '', 'Tipo Retención del IRPF', 'Importe Retenido del IRPF', 'Registro Acuerdo Facturación', 'Inmueble', '', 'Referencia Externa'),
            1: ('Ejercicio', 'Periodo', 'Código', 'Tipo', 'Grupo o Epígrafe del IAE', '', '', '', '', '', 'Serie', 'Número', 'Número-Final', 'Tipo', 'Código País', 'Identificación', '', '', '', '', '', '', '', '', '', '', 'Fecha', 'Importe', 'Medio Utilizado', 'Identificación Medio Utilizado', '', '', '', 'Situación', 'Referencia Catastral', ''),
            2: (2019, '4T', 'A', '01', '0000', 'F2', 'I01', 3000, '12/31/2019', '', '', 'INV/2019/00002', '', '', '', '', False, '01', 'S1', '', 3630, 3000, 21, 630, 0, 0, '', '', '', '', 0, 0, '', '', '', ''),
            3: (2019, '4T', 'A', '01', '0000', 'F1', 'I01', 5000, '12/31/2019', '', '', 'INV/2019/00001', '', '', '', '', 'España', '01', 'S1', '', 6050, 5000, 21, 1050, 0, 0, '', '', '', '', 0, 0, '', '', '', ''),
        })

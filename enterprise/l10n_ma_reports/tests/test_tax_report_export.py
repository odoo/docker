from odoo import Command
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountMaExport(TestAccountReportsCommon):
    @classmethod
    @TestAccountReportsCommon.setup_country('ma')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].write({
            'vat': '001561191000066',
        })

        cls.partner_ma = cls.env['res.partner'].create({
            'name': 'Ma customer',
            'vat': '002136093000040',
            'country_id': cls.env.ref('base.ma').id,
        })

        cls.product_a = cls.env['product.product'].create({
            'name': 'Product A',
        })

        cls.report = cls.env.ref('l10n_ma.tax_report_vat')
        cls.handler = cls.env['l10n_ma.tax.report.handler']

        cls.default_options = cls._generate_options(cls.report, '2019-01-01', '2019-02-01')
        cls.default_options['date']['period_type'] = 'month'  # 'month' or 'quarter' are required

    def _l10n_ma_generate_report(self, options=None):
        with freeze_time('2019-11-01 00:00:00'):
            return self.handler.l10n_ma_reports_export_vat_to_xml(options or self.default_options)

    def test_simple_export_tax_report(self):
        """ This will test a simple export with no moves data. """

        report = self._l10n_ma_generate_report()
        self._report_compare_with_test_file(report, test_xml="""
            <DeclarationReleveDeduction>
                <idf>001561191000066</idf>
                <annee>2019</annee>
                <periode>1</periode>
                <regime>1</regime>
                <releveDeductions>
                </releveDeductions>
            </DeclarationReleveDeduction>
        """)

        self.env.company.account_tax_periodicity = 'trimester'  # 'monthly' or 'trimester' are required
        options = self._generate_options(self.report, '2019-01-01', '2019-04-01')
        report = self._l10n_ma_generate_report(options)
        self._report_compare_with_test_file(report, test_xml="""
            <DeclarationReleveDeduction>
                <idf>001561191000066</idf>
                <annee>2019</annee>
                <periode>1</periode>
                <regime>2</regime>
                <releveDeductions>
                </releveDeductions>
            </DeclarationReleveDeduction>
        """)

    def test_export_tax_report_with_data(self):
        """ This will test a simple export with moves data. """
        self.partner_ma.company_registry = '123456789123456'

        self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_ma.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
            })],
        }).action_post()

        report = self._l10n_ma_generate_report()
        self._report_compare_with_test_file(report, test_xml="""
            <DeclarationReleveDeduction>
                <idf>001561191000066</idf>
                <annee>2019</annee>
                <periode>1</periode>
                <regime>1</regime>
                <releveDeductions>
                    <rd>
                        <ordre>1</ordre>
                        <num>BILL/2019/01/0001</num>
                        <des>BILL/2019/01/0001</des>
                        <mht>500.0</mht>
                        <tva>100.0</tva>
                        <ttc>600.0</ttc>
                        <refF>
                            <if>002136093000040</if>
                            <nom>Ma customer</nom>
                            <ice>123456789123456</ice>
                        </refF>
                        <tx>20.0</tx>
                        <mp>
                            <id>7</id>
                        </mp>
                        <dpai></dpai>
                        <dfac>2019-01-01</dfac>
                    </rd>
                </releveDeductions>
            </DeclarationReleveDeduction>
        """)

    def test_export_tax_report_local_partner_with_no_ice(self):
        """
            This test will try to export the xml with a partner missing the ice field. We will check the non critical
            error but also the content of the file to see if the move is well skipped
        """
        partner_ma_with_ice = self.env['res.partner'].create({
            'name': 'Ma customer with ice',
            'vat': '001561191000066',
            'country_id': self.env.ref('base.ma').id,
            'company_registry': '123456789123456',
        })

        self.env['account.move'].create([
            {
                'move_type': 'in_invoice',
                'date': '2019-01-01',
                'invoice_date': '2019-01-01',
                'partner_id': self.partner_ma.id,
                'currency_id': self.other_currency.id,
                'invoice_line_ids': [Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
                })],
            },
            {
                'move_type': 'in_invoice',
                'date': '2019-01-01',
                'invoice_date': '2019-01-01',
                'partner_id': partner_ma_with_ice.id,
                'currency_id': self.other_currency.id,
                'invoice_line_ids': [Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
                })],
            },
        ]).action_post()

        template_value = self.handler._l10n_ma_prepare_vat_report_values(self.default_options)
        self.assertTrue('partner_vat_ice_missing' in template_value['errors'])

        # This part is needed to avoid the assert of an error and having the content of the file.
        generator_params = {'values': template_value, 'template': 'l10n_ma_reports.l10n_ma_tax_report_template', 'file_type': 'xml'}
        content = self.env['ir.qweb']._render(**generator_params)

        generated_export_string = self.get_xml_tree_from_string(content)
        self.assertXmlTreeEqual(
            generated_export_string,
            self.get_xml_tree_from_string("""
                <DeclarationReleveDeduction>
                    <idf>001561191000066</idf>
                    <annee>2019</annee>
                    <periode>1</periode>
                    <regime>1</regime>
                    <releveDeductions>
                        <rd>
                            <ordre>1</ordre>
                            <num>BILL/2019/01/0002</num>
                            <des>BILL/2019/01/0002</des>
                            <mht>500.0</mht>
                            <tva>100.0</tva>
                            <ttc>600.0</ttc>
                            <refF>
                                <if>001561191000066</if>
                                <nom>Ma customer with ice</nom>
                                <ice>123456789123456</ice>
                            </refF>
                            <tx>20.0</tx>
                            <mp>
                                <id>7</id>
                            </mp>
                            <dpai></dpai>
                            <dfac>2019-01-01</dfac>
                        </rd>
                    </releveDeductions>
                </DeclarationReleveDeduction>
            """)
        )

    def test_export_tax_report_critical_error(self):
        """
            This test will check the export when having critical error, there is two potentials critical errors.
            - When the company has no vat
            - When the period selected of the report is not monthly or quarterly
        """
        self.env.company.vat = False
        self.partner_ma.company_registry = '123456789123456'

        self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_ma.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
            })],
        }).action_post()

        errors = self.handler._l10n_ma_prepare_vat_report_values(self.default_options)['errors']
        self.assertTrue('company_vat_missing' in errors)

        self.env.company.vat = '001561191000066'
        self.env.company.account_tax_periodicity = 'semester'
        options = self._generate_options(self.report, '2019-01-01', '2019-02-01')
        errors = self.handler._l10n_ma_prepare_vat_report_values(options)['errors']
        self.assertTrue('period_invalid' in errors)

    def test_export_tax_report_foreign_customer(self):
        # 'vat' value must be random to avoid the partner auto-completion feature that would overwrite the company_registry (ICE)
        foreign_customer = self.env['res.partner'].create({
            'name': 'Foreign customer with no ice',
            'vat': 'US12345',
            'country_id': self.env.ref('base.us').id,
        })

        self.env['account.move'].create({
            'move_type': 'in_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': foreign_customer.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
            })],
        }).action_post()

        report = self._l10n_ma_generate_report()
        self._report_compare_with_test_file(report, test_xml="""
            <DeclarationReleveDeduction>
                <idf>001561191000066</idf>
                <annee>2019</annee>
                <periode>1</periode>
                <regime>1</regime>
                <releveDeductions>
                    <rd>
                        <ordre>1</ordre>
                        <num>BILL/2019/01/0001</num>
                        <des>BILL/2019/01/0001</des>
                        <mht>500.0</mht>
                        <tva>100.0</tva>
                        <ttc>600.0</ttc>
                        <refF>
                            <if>20727020</if>
                            <nom>Foreign customer with no ice</nom>
                            <ice>20727020</ice>
                        </refF>
                        <tx>20.0</tx>
                        <mp>
                            <id>7</id>
                        </mp>
                        <dpai></dpai>
                        <dfac>2019-01-01</dfac>
                    </rd>
                </releveDeductions>
            </DeclarationReleveDeduction>
        """)

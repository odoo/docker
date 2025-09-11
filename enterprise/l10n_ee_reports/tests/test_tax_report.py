# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class EstonianTaxReportTest(AccountSalesReportCommon):

    @classmethod
    @AccountSalesReportCommon.setup_country('ee')
    def setUpClass(cls):
        super().setUpClass()

        cls.company.write({
            'vat': 'EE123456780',
            'company_registry': '12345678',
        })

        cls.partner_ee_1 = cls.env['res.partner'].create({
            'name': 'Partner EE 1',
            'country_id': cls.env.ref('base.ee').id,
            'company_registry': '98765432',
            'vat': 'EE023456783',
            'is_company': True,
        })

        cls.partner_ee_2 = cls.env['res.partner'].create({
            'name': 'Partner EE 2',
            'country_id': cls.env.ref('base.ee').id,
            'vat': 'EE113456787',
            'is_company': True,
        })

        cls.company_id = cls.env.company.id
        # Purchase Taxes
        cls.vat_in_22_g = cls.env['account.chart.template'].ref('l10n_ee_vat_in_22_g')
        cls.vat_in_22_s = cls.env['account.chart.template'].ref('l10n_ee_vat_in_22_s')
        cls.vat_in_9_g = cls.env['account.chart.template'].ref('l10n_ee_vat_in_9_g')
        cls.vat_in_5_g = cls.env['account.chart.template'].ref('l10n_ee_vat_in_5_g')
        cls.vat_in_0_g = cls.env['account.chart.template'].ref('l10n_ee_vat_in_0_g')
        cls.vat_in_0_eu_g = cls.env['account.chart.template'].ref('l10n_ee_vat_in_0_eu_g_22')
        cls.vat_in_0_eu_s = cls.env['account.chart.template'].ref('l10n_ee_vat_in_0_eu_s_22')
        cls.vat_in_22_car = cls.env['account.chart.template'].ref('l10n_ee_vat_in_22_car')
        cls.vat_in_22_car_part = cls.env['account.chart.template'].ref('l10n_ee_vat_in_22_car_part')
        cls.vat_in_22_assets = cls.env['account.chart.template'].ref('l10n_ee_vat_in_22_assets')
        cls.vat_in_imp_cus = cls.env['account.chart.template'].ref('l10n_ee_vat_in_imp_cus')
        cls.vat_in_22_imp_kms_38 = cls.env['account.chart.template'].ref('l10n_ee_vat_in_22_imp_kms_38')
        cls.vat_in_0_kms_41_2 = cls.env['account.chart.template'].ref('l10n_ee_vat_in_0_kms_41_2')
        cls.vat_in_22_s.l10n_ee_kmd_inf_code = '11'  # added to test if the special comments column is filled
        # Sales Taxes
        cls.vat_out_22_g = cls.env['account.chart.template'].ref('l10n_ee_vat_out_22_g')
        cls.vat_out_9_g = cls.env['account.chart.template'].ref('l10n_ee_vat_out_9_g')
        cls.vat_out_5_g = cls.env['account.chart.template'].ref('l10n_ee_vat_out_5_g')
        cls.vat_out_0_g = cls.env['account.chart.template'].ref('l10n_ee_vat_out_0_g')
        cls.vat_out_0_eu_g = cls.env['account.chart.template'].ref('l10n_ee_vat_out_0_eu_g')
        cls.vat_out_0_eu_s = cls.env['account.chart.template'].ref('l10n_ee_vat_out_0_eu_s')
        cls.vat_out_0_exp_g = cls.env['account.chart.template'].ref('l10n_ee_vat_out_0_exp_g')
        cls.vat_out_0_pas = cls.env['account.chart.template'].ref('l10n_ee_vat_out_0_pas')
        cls.vat_out_0_exp_s = cls.env['account.chart.template'].ref('l10n_ee_vat_out_0_exp_s')
        cls.vat_out_exempt = cls.env['account.chart.template'].ref('l10n_ee_vat_out_exempt')
        cls.vat_out_0_kms_41_2 = cls.env['account.chart.template'].ref('l10n_ee_vat_out_0_kms_41_2')
        cls.vat_out_22_erikord = cls.vat_out_22_g.copy({
            'name': '22% erikord',
            'l10n_ee_kmd_inf_code': '1',
        })

        cls.kmd_report = cls.env.ref('l10n_ee.tax_report')
        cls.kmd_inf_a_report = cls.env.ref('l10n_ee_reports.kmd_inf_report_part_a')
        cls.kmd_inf_b_report = cls.env.ref('l10n_ee_reports.kmd_inf_report_part_b')

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        res = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        res['company'].update({
            'country_id': cls.env.ref('base.ee').id,
            'vat': 'EE123456780',
            'company_registry': '12345678',
        })
        return res

    @classmethod
    def create_invoice(cls, post=True, **kwargs):
        move_type = kwargs.get('move_type')
        invoice_date = kwargs.get('invoice_date')
        journal_id = cls.company_data['default_journal_purchase'].id if move_type == 'in_invoice' else cls.company_data['default_journal_sale'].id

        invoice = cls.env['account.move'].create({
            'move_type': move_type,
            'journal_id': journal_id,
            'invoice_date': invoice_date,
            'date': kwargs.get('date', invoice_date),
            **kwargs,
            'invoice_line_ids': [
                Command.create({'quantity': 1.0, **line_vals})
                for line_vals in kwargs.get('invoice_line_ids', [])
            ],
        })
        if post:
            invoice.action_post()
        return invoice

    @freeze_time('2023-02-01')
    def test_generate_xml_purchase(self):
        self.create_invoice(
            move_type='in_invoice',
            partner_id=self.partner_ee_1.id,
            invoice_date='2023-01-11',
            ref='INV001',
            invoice_line_ids=[{'name': 'PT1', 'price_unit': 500, 'tax_ids': self.vat_in_22_g.ids}],
        )
        self.create_invoice(
            move_type='in_invoice',
            partner_id=self.partner_ee_2.id,
            invoice_date='2023-01-13',
            ref='INV002',
            invoice_line_ids=[
                {'name': 'PT1', 'price_unit': 500, 'tax_ids': self.vat_in_22_s.ids},
                {'name': 'PT2', 'price_unit': 300, 'tax_ids': self.vat_in_9_g.ids},
                {'name': 'PT3', 'price_unit': 200, 'tax_ids': self.vat_in_5_g.ids},
                {'name': 'PT4', 'price_unit': 150, 'tax_ids': self.vat_in_0_g.ids},
            ],
        )

        expected_xml = """
            <vatDeclaration>
                <taxPayerRegCode>12345678</taxPayerRegCode>
                <year>2023</year>
                <month>1</month>
                <declarationType>1</declarationType>
                <version>KMD4</version>
                <declarationBody>
                    <noSales>true</noSales>
                    <noPurchases>false</noPurchases>
                    <sumPerPartnerSales>false</sumPerPartnerSales>
                    <sumPerPartnerPurchases>false</sumPerPartnerPurchases>
                    <inputVatTotal>257.00</inputVatTotal>
                </declarationBody>
                <purchasesAnnex>
                    <purchaseLine>
                        <sellerName>Partner EE 2</sellerName>
                        <invoiceNumber>INV002</invoiceNumber>
                        <invoiceDate>2023-01-13</invoiceDate>
                        <invoiceSumVat>1297.00</invoiceSumVat>
                        <vatInPeriod>147.00</vatInPeriod>
                        <comments>11</comments>
                    </purchaseLine>
                    <purchaseLine>
                        <sellerRegCode>98765432</sellerRegCode>
                        <sellerName>Partner EE 1</sellerName>
                        <invoiceNumber>INV001</invoiceNumber>
                        <invoiceDate>2023-01-11</invoiceDate>
                        <invoiceSumVat>610.00</invoiceSumVat>
                        <vatInPeriod>110.00</vatInPeriod>
                    </purchaseLine>
                </purchasesAnnex>
            </vatDeclaration>
        """

        options = self.kmd_report.get_options({})
        actual_xml = self.env[self.kmd_report.custom_handler_model_name].export_to_xml(options)['file_content']

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_xml),
            self.get_xml_tree_from_string(expected_xml)
        )

    @freeze_time('2023-02-01')
    def test_generate_xml_sale(self):
        self.create_invoice(
            move_type='out_invoice',
            partner_id=self.partner_ee_1.id,
            invoice_date='2023-01-11',
            invoice_line_ids=[{'name': 'PT1', 'price_unit': 500, 'tax_ids': self.vat_out_22_g.ids}]
        )
        self.create_invoice(
            move_type='out_invoice',
            partner_id=self.partner_ee_2.id,
            invoice_date='2023-01-13',
            invoice_line_ids=[
                {'name': 'PT1', 'price_unit': 500, 'tax_ids': self.vat_out_22_g.ids},
                {'name': 'PT2', 'price_unit': 300, 'tax_ids': self.vat_out_9_g.ids},
                {'name': 'PT3', 'price_unit': 200, 'tax_ids': self.vat_out_5_g.ids},
                {'name': 'PT4', 'price_unit': 150, 'tax_ids': self.vat_out_0_g.ids},
            ],
        )

        expected_xml = """
            <vatDeclaration>
                <taxPayerRegCode>12345678</taxPayerRegCode>
                <year>2023</year>
                <month>1</month>
                <declarationType>1</declarationType>
                <version>KMD4</version>
                <declarationBody>
                    <noSales>false</noSales>
                    <noPurchases>true</noPurchases>
                    <sumPerPartnerSales>false</sumPerPartnerSales>
                    <sumPerPartnerPurchases>false</sumPerPartnerPurchases>
                    <transactions22>1000.00</transactions22>
                    <transactions9>300.00</transactions9>
                    <transactions5>200.00</transactions5>
                    <transactionsZeroVat>150.00</transactionsZeroVat>
                </declarationBody>
                <salesAnnex>
                    <saleLine>
                        <buyerName>Partner EE 2</buyerName>
                        <invoiceNumber>INV/2023/00002</invoiceNumber>
                        <invoiceDate>2023-01-13</invoiceDate>
                        <invoiceSum>1150.00</invoiceSum>
                        <taxRate>22</taxRate>
                        <sumForRateInPeriod>500.00</sumForRateInPeriod>
                        <comments>3</comments>
                    </saleLine>
                    <saleLine>
                        <buyerName>Partner EE 2</buyerName>
                        <invoiceNumber>INV/2023/00002</invoiceNumber>
                        <invoiceDate>2023-01-13</invoiceDate>
                        <invoiceSum>1150.00</invoiceSum>
                        <taxRate>9</taxRate>
                        <sumForRateInPeriod>300.00</sumForRateInPeriod>
                        <comments>3</comments>
                    </saleLine>
                    <saleLine>
                        <buyerName>Partner EE 2</buyerName>
                        <invoiceNumber>INV/2023/00002</invoiceNumber>
                        <invoiceDate>2023-01-13</invoiceDate>
                        <invoiceSum>1150.00</invoiceSum>
                        <taxRate>5</taxRate>
                        <sumForRateInPeriod>200.00</sumForRateInPeriod>
                        <comments>3</comments>
                    </saleLine>
                    <saleLine>
                        <buyerRegCode>98765432</buyerRegCode>
                        <buyerName>Partner EE 1</buyerName>
                        <invoiceNumber>INV/2023/00001</invoiceNumber>
                        <invoiceDate>2023-01-11</invoiceDate>
                        <invoiceSum>500.00</invoiceSum>
                        <taxRate>22</taxRate>
                        <sumForRateInPeriod>500.00</sumForRateInPeriod>
                    </saleLine>
                </salesAnnex>
            </vatDeclaration>
        """

        options = self.kmd_report.get_options({})
        actual_xml = self.env[self.kmd_report.custom_handler_model_name].export_to_xml(options)['file_content']

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_xml),
            self.get_xml_tree_from_string(expected_xml)
        )

    @freeze_time('2023-02-01')
    def test_generate_xml_mixed_all(self):
        self.create_invoice(
            move_type='in_invoice',
            partner_id=self.partner_ee_1.id,
            invoice_date='2023-01-11',
            ref='INV001',
            invoice_line_ids=[
                {'name': 'PT1', 'price_unit': 500, 'tax_ids': self.vat_in_22_g.ids},
                {'name': 'PT2', 'price_unit': 400, 'tax_ids': self.vat_in_0_kms_41_2.ids},
            ]
        )
        self.create_invoice(
            move_type='in_invoice',
            partner_id=self.partner_ee_2.id,
            invoice_date='2023-01-13',
            ref='INV002',
            invoice_line_ids=[
                {'name': 'PT1', 'price_unit': 500, 'tax_ids': self.vat_in_22_s.ids},
                {'name': 'PT2', 'price_unit': 300, 'tax_ids': self.vat_in_9_g.ids},
                {'name': 'PT3', 'price_unit': 200, 'tax_ids': self.vat_in_5_g.ids},
                {'name': 'PT4', 'price_unit': 150, 'tax_ids': self.vat_in_0_g.ids},
            ],
        )
        self.create_invoice(
            move_type='in_invoice',
            partner_id=self.partner_a.id,
            invoice_date='2023-01-20',
            ref='INV003',
            invoice_line_ids=[
                {'name': 'PT1', 'price_unit': 800, 'tax_ids': self.vat_in_0_eu_g.ids},
                {'name': 'PT2', 'price_unit': 700, 'tax_ids': self.vat_in_0_eu_s.ids},
                {'name': 'PT3', 'price_unit': 600, 'tax_ids': self.vat_in_22_car.ids},
                {'name': 'PT4', 'price_unit': 500, 'tax_ids': self.vat_in_22_car_part.ids},
                {'name': 'PT5', 'price_unit': 400, 'tax_ids': self.vat_in_22_assets.ids},
                {'name': 'PT6', 'price_unit': 300, 'tax_ids': self.vat_in_imp_cus.ids},
                {'name': 'PT7', 'price_unit': 200, 'tax_ids': self.vat_in_22_imp_kms_38.ids},
                {'name': 'PT8', 'price_unit': 100, 'tax_ids': self.vat_in_0_kms_41_2.ids},
            ],
        )
        self.create_invoice(
            move_type='out_invoice',
            partner_id=self.partner_ee_1.id,
            invoice_date='2023-01-11',
            invoice_line_ids=[
                {'name': 'PT1', 'price_unit': 500, 'tax_ids': self.vat_out_22_g.ids},
                {'name': 'PT2', 'price_unit': 400, 'tax_ids': self.vat_out_0_kms_41_2.ids},
                {'name': 'PT3', 'price_unit': 300, 'tax_ids': self.vat_out_22_erikord.ids},
            ],
        )
        self.create_invoice(
            move_type='out_invoice',
            partner_id=self.partner_ee_2.id,
            invoice_date='2023-01-13',
            invoice_line_ids=[
                {'name': 'PT1', 'price_unit': 500, 'tax_ids': self.vat_out_22_g.ids},
                {'name': 'PT2', 'price_unit': 300, 'tax_ids': self.vat_out_9_g.ids},
                {'name': 'PT3', 'price_unit': 200, 'tax_ids': self.vat_out_5_g.ids},
                {'name': 'PT4', 'price_unit': 150, 'tax_ids': self.vat_out_0_g.ids},
            ],
        )
        self.create_invoice(
            move_type='out_invoice',
            partner_id=self.partner_a.id,
            invoice_date='2023-01-25',
            invoice_line_ids=[
                {'name': 'PT1', 'price_unit': 800, 'tax_ids': self.vat_out_0_eu_g.ids},
                {'name': 'PT2', 'price_unit': 700, 'tax_ids': self.vat_out_0_eu_s.ids},
                {'name': 'PT3', 'price_unit': 600, 'tax_ids': self.vat_out_0_exp_g.ids},
                {'name': 'PT4', 'price_unit': 500, 'tax_ids': self.vat_out_0_pas.ids},
                {'name': 'PT5', 'price_unit': 400, 'tax_ids': self.vat_out_0_exp_s.ids},
                {'name': 'PT6', 'price_unit': 300, 'tax_ids': self.vat_out_exempt.ids},
                {'name': 'PT7', 'price_unit': 200, 'tax_ids': self.vat_out_0_kms_41_2.ids},
            ],
        )

        options_kmd = self.kmd_report.get_options({})
        options_kmd_inf_a = self.kmd_inf_a_report.get_options({})
        options_kmd_inf_b = self.kmd_inf_b_report.get_options({})

        self.assertLinesValues(
            self.kmd_inf_a_report._get_lines(options_kmd_inf_a),
            #    Name                                     Reg code       Buyer              Invoice number       Date             Invoice total    Tax rate        Taxable supply    Special code
            [    0,                                       1,             2,                 3,                   4,               5,               6,              7,                8],
            [
                ('Part A - Invoices Issued',              '',            '',                '',                  '',              '',              '',             '',               ''),
                ('INV/2023/00002',                        '',            '',                '',                  '',              '',              '',             '',               ''),
                ('VAT 22%',                               '',            'Partner EE 2',    'INV/2023/00002',    '01/13/2023',    1150,            '22',           500,              '3'),
                ('VAT 9%',                                '',            'Partner EE 2',    'INV/2023/00002',    '01/13/2023',    1150,            '9',            300,              '3'),
                ('VAT 5%',                                '',            'Partner EE 2',    'INV/2023/00002',    '01/13/2023',    1150,            '5',            200,              '3'),
                ('INV/2023/00001',                        '',            '',                '',                  '',              '',              '',             '',               ''),
                ('VAT 22%',                               '98765432',    'Partner EE 1',    'INV/2023/00001',    '01/11/2023',    1200,            '22',           500,              ''),
                ('VAT 22% special procedure §41^1',       '98765432',    'Partner EE 1',    'INV/2023/00001',    '01/11/2023',    1200,            '22',           '',               '2'),
                ('VAT 22% special procedure §41/42',      '98765432',    'Partner EE 1',    'INV/2023/00001',    '01/11/2023',    1200,            '22erikord',    300,              '1'),
            ],
            options_kmd_inf_a,
            currency_map={
                5: {'currency': self.env.company.currency_id},
                7: {'currency': self.env.company.currency_id},
            },
        )

        self.assertLinesValues(
            self.kmd_inf_b_report._get_lines(options_kmd_inf_b),
            #    Name                             Reg code       Seller             Invoice number    Date             Invoice total    VAT     Special code
            [    0,                               1,             2,                 3,                4,               5,               6,      7],
            [
                ('Part B - Invoices Received',    '',            '',                '',               '',              '',              '',     ''),
                ('BILL/2023/01/0002 (INV002)',    '',            'Partner EE 2',    'INV002',         '01/13/2023',    1297,            147,    '11'),
                ('BILL/2023/01/0001 (INV001)',    '98765432',    'Partner EE 1',    'INV001',         '01/11/2023',    1098,            198,    '12'),
            ],
            options_kmd_inf_b,
        )

        expected_xml = """
            <vatDeclaration>
                <taxPayerRegCode>12345678</taxPayerRegCode>
                <year>2023</year>
                <month>1</month>
                <declarationType>1</declarationType>
                <version>KMD4</version>
                <declarationBody>
                    <noSales>false</noSales>
                    <noPurchases>false</noPurchases>
                    <sumPerPartnerSales>false</sumPerPartnerSales>
                    <sumPerPartnerPurchases>false</sumPerPartnerPurchases>
                    <transactions22>3300.00</transactions22>
                    <transactions9>300.00</transactions9>
                    <transactions5>200.00</transactions5>
                    <transactionsZeroVat>3150.00</transactionsZeroVat>
                    <euSupplyInclGoodsAndServicesZeroVat>1500.00</euSupplyInclGoodsAndServicesZeroVat>
                    <euSupplyGoodsZeroVat>800.00</euSupplyGoodsZeroVat>
                    <exportZeroVat>1100.00</exportZeroVat>
                    <salePassengersWithReturnVat>500.00</salePassengersWithReturnVat>
                    <inputVatTotal>1316.00</inputVatTotal>
                    <importVat>344.00</importVat>
                    <fixedAssetsVat>88.00</fixedAssetsVat>
                    <carsVat>132.00</carsVat>
                    <carsPartialVat>55.00</carsPartialVat>
                    <euAcquisitionsGoodsAndServicesTotal>1500.00</euAcquisitionsGoodsAndServicesTotal>
                    <euAcquisitionsGoods>800.00</euAcquisitionsGoods>
                    <acquisitionOtherGoodsAndServicesTotal>500.00</acquisitionOtherGoodsAndServicesTotal>
                    <acquisitionImmovablesAndScrapMetalAndGold>500.00</acquisitionImmovablesAndScrapMetalAndGold>
                    <supplyExemptFromTax>300.00</supplyExemptFromTax>
                    <supplySpecialArrangements>600.00</supplySpecialArrangements>
                </declarationBody>
                <salesAnnex>
                    <saleLine>
                        <buyerName>Partner EE 2</buyerName>
                        <invoiceNumber>INV/2023/00002</invoiceNumber>
                        <invoiceDate>2023-01-13</invoiceDate>
                        <invoiceSum>1150.00</invoiceSum>
                        <taxRate>22</taxRate>
                        <sumForRateInPeriod>500.00</sumForRateInPeriod>
                        <comments>3</comments>
                    </saleLine>
                    <saleLine>
                        <buyerName>Partner EE 2</buyerName>
                        <invoiceNumber>INV/2023/00002</invoiceNumber>
                        <invoiceDate>2023-01-13</invoiceDate>
                        <invoiceSum>1150.00</invoiceSum>
                        <taxRate>9</taxRate>
                        <sumForRateInPeriod>300.00</sumForRateInPeriod>
                        <comments>3</comments>
                    </saleLine>
                    <saleLine>
                        <buyerName>Partner EE 2</buyerName>
                        <invoiceNumber>INV/2023/00002</invoiceNumber>
                        <invoiceDate>2023-01-13</invoiceDate>
                        <invoiceSum>1150.00</invoiceSum>
                        <taxRate>5</taxRate>
                        <sumForRateInPeriod>200.00</sumForRateInPeriod>
                        <comments>3</comments>
                    </saleLine>
                    <saleLine>
                        <buyerRegCode>98765432</buyerRegCode>
                        <buyerName>Partner EE 1</buyerName>
                        <invoiceNumber>INV/2023/00001</invoiceNumber>
                        <invoiceDate>2023-01-11</invoiceDate>
                        <invoiceSum>1200.00</invoiceSum>
                        <taxRate>22</taxRate>
                        <sumForRateInPeriod>500.00</sumForRateInPeriod>
                    </saleLine>
                    <saleLine>
                        <buyerRegCode>98765432</buyerRegCode>
                        <buyerName>Partner EE 1</buyerName>
                        <invoiceNumber>INV/2023/00001</invoiceNumber>
                        <invoiceDate>2023-01-11</invoiceDate>
                        <invoiceSum>1200.00</invoiceSum>
                        <taxRate>22</taxRate>
                        <comments>2</comments>
                    </saleLine>
                    <saleLine>
                        <buyerRegCode>98765432</buyerRegCode>
                        <buyerName>Partner EE 1</buyerName>
                        <invoiceNumber>INV/2023/00001</invoiceNumber>
                        <invoiceDate>2023-01-11</invoiceDate>
                        <invoiceSum>1200.00</invoiceSum>
                        <taxRate>22erikord</taxRate>
                        <sumForRateInPeriod>300.00</sumForRateInPeriod>
                        <comments>1</comments>
                    </saleLine>
                </salesAnnex>
                <purchasesAnnex>
                    <purchaseLine>
                        <sellerName>Partner EE 2</sellerName>
                        <invoiceNumber>INV002</invoiceNumber>
                        <invoiceDate>2023-01-13</invoiceDate>
                        <invoiceSumVat>1297.00</invoiceSumVat>
                        <vatInPeriod>147.00</vatInPeriod>
                        <comments>11</comments>
                    </purchaseLine>
                    <purchaseLine>
                        <sellerRegCode>98765432</sellerRegCode>
                        <sellerName>Partner EE 1</sellerName>
                        <invoiceNumber>INV001</invoiceNumber>
                        <invoiceDate>2023-01-11</invoiceDate>
                        <invoiceSumVat>1098.00</invoiceSumVat>
                        <vatInPeriod>198.00</vatInPeriod>
                        <comments>12</comments>
                    </purchaseLine>
                </purchasesAnnex>
            </vatDeclaration>
        """

        actual_xml = self.env[self.kmd_report.custom_handler_model_name].export_to_xml(options_kmd)['file_content']

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_xml),
            self.get_xml_tree_from_string(expected_xml)
        )

    @freeze_time('2023-02-01')
    def test_special_code_single_tax(self):
        """ Special code column (comments) should not appear when
        there are only invoices with invoice lines with a single
        tax
        """
        self.create_invoice(
            move_type='out_invoice',
            partner_id=self.partner_ee_1.id,
            invoice_date='2023-01-11',
            invoice_line_ids=[{'name': 'PT1', 'price_unit': 500, 'tax_ids': self.vat_out_22_g.ids}],
        )
        self.create_invoice(
            move_type='out_invoice',
            partner_id=self.partner_ee_1.id,
            invoice_date='2023-01-13',
            date='2023-01-11',
            invoice_line_ids=[{'name': 'PT1', 'price_unit': 500, 'tax_ids': self.vat_out_9_g.ids}],
        )

        expected_xml = """
            <vatDeclaration>
            <taxPayerRegCode>12345678</taxPayerRegCode>
            <year>2023</year>
            <month>1</month>
            <declarationType>1</declarationType>
            <version>KMD4</version>
            <declarationBody>
                <noSales>false</noSales>
                <noPurchases>true</noPurchases>
                <sumPerPartnerSales>false</sumPerPartnerSales>
                <sumPerPartnerPurchases>false</sumPerPartnerPurchases>
                <transactions22>500.00</transactions22>
                <transactions9>500.00</transactions9>
            </declarationBody>
            <salesAnnex>
                <saleLine>
                <buyerRegCode>98765432</buyerRegCode>
                <buyerName>Partner EE 1</buyerName>
                <invoiceNumber>INV/2023/00002</invoiceNumber>
                <invoiceDate>2023-01-13</invoiceDate>
                <invoiceSum>500.00</invoiceSum>
                <taxRate>9</taxRate>
                <sumForRateInPeriod>500.00</sumForRateInPeriod>
                </saleLine>
                <saleLine>
                <buyerRegCode>98765432</buyerRegCode>
                <buyerName>Partner EE 1</buyerName>
                <invoiceNumber>INV/2023/00001</invoiceNumber>
                <invoiceDate>2023-01-11</invoiceDate>
                <invoiceSum>500.00</invoiceSum>
                <taxRate>22</taxRate>
                <sumForRateInPeriod>500.00</sumForRateInPeriod>
                </saleLine>
            </salesAnnex>
            </vatDeclaration>
        """

        options = self.kmd_report.get_options({})
        actual_xml = self.env[self.kmd_report.custom_handler_model_name].export_to_xml(options)['file_content']

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_xml),
            self.get_xml_tree_from_string(expected_xml)
        )

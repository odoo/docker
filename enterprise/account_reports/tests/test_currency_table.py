from odoo import Command
from odoo.tests import tagged

from .common import TestAccountReportsCommon


@tagged('post_install', '-at_install')
class TestCurrencyTable(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].write({'name': "USD Company 1", 'sequence': 1, 'totals_below_sections': False})
        cls.company_usd_data = cls.company_data
        # Create additional companies (also adding them to env.companies)
        cls.company_usd_data_2 = cls.setup_other_company(name="USD Company 2", sequence=2, currency_id=cls.env.ref('base.USD').id)
        cls.company_eur_data = cls.setup_other_company(name="EUR Company 1", sequence=3, currency_id=cls.env.ref('base.EUR').id)
        cls.company_eur_data_2 = cls.setup_other_company(name="EUR Company 2", sequence=4, currency_id=cls.env.ref('base.EUR').id)
        cls.company_chf_data = cls.setup_other_company(name="CHF Company", sequence=5, currency_id=cls.env.ref('base.CHF').id)
        cls.company_mxn_data = cls.setup_other_company(name="MXN Company", sequence=5, currency_id=cls.env.ref('base.MXN').id)

        # Add equity account to the company data
        for company_data in (cls.company_usd_data, cls.company_usd_data_2, cls.company_eur_data, cls.company_eur_data_2, cls.company_chf_data, cls.company_mxn_data):
            company_data['equity_account'] = cls.env['account.account'].search([
                ('company_ids', '=', company_data['company'].id),
                ('account_type', '=', 'equity'),
            ], limit=1)

        cls.report = cls.env['account.report'].create({
            'name': "Currency Table Test",
            'filter_multi_company': 'selector',
            'currency_translation': 'cta',
            'column_ids': [Command.create({'name': "Balance", 'expression_label': 'balance'})],
            'line_ids': [
                Command.create({
                    'name': "Asset",
                    'groupby': 'company_id',
                    'expression_ids': [
                        Command.create({
                            'label': 'balance',
                            'engine': 'domain',
                            'formula': "[('account_id.internal_group', '=', 'asset')]",
                            'subformula': "sum",
                        }),
                    ],
                }),
                Command.create({
                    'name': "Income",
                    'groupby': 'company_id',
                    'expression_ids': [
                        Command.create({
                            'label': 'balance',
                            'engine': 'domain',
                            'formula': "[('account_id.internal_group', '=', 'income')]",
                            'subformula': "sum",
                        }),
                    ],
                }),
                Command.create({
                    'name': "Equity",
                    'groupby': 'company_id',
                    'expression_ids': [
                        Command.create({
                            'label': 'balance',
                            'engine': 'domain',
                            'formula': "[('account_id.internal_group', '=', 'equity')]",
                            'subformula': "sum",
                        }),
                    ],
                }),
            ],
        })

    def _generate_equity_move(self, company_data, date, amount):
        rslt = self.env['account.move'].create({
            'company_id': company_data['company'].id,
            'date': date,
            'line_ids': [
                Command.create({
                    'debit': 0,
                    'credit': amount,
                    'account_id': company_data['default_account_expense'].id,
                }),
                Command.create({
                    'debit': amount,
                    'credit': 0,
                    'account_id': company_data['equity_account'].id,
                }),
            ],
        })
        rslt.action_post()
        return rslt

    def test_currency_table_multicurrency(self):
        # USD OPERATIONS (domestic currency)
        self.init_invoice('out_invoice', company=self.company_usd_data['company'], invoice_date='2020-05-12', amounts=[10], post=True)
        self.init_invoice('out_invoice', company=self.company_usd_data_2['company'], invoice_date='2020-08-23', amounts=[25], post=True)
        self._generate_equity_move(self.company_usd_data, '2020-11-11', 42)
        self._generate_equity_move(self.company_usd_data, '2020-12-01', 88)
        self._generate_equity_move(self.company_usd_data_2, '2020-02-01', 11)

        # EUR OPERATIONS
        self.setup_other_currency('EUR', rates=[('2018-10-10', 7), ('2019-12-22', 11), ('2020-01-01', 2), ('2020-03-12', 5), ('2020-03-30', 20), ('2020-04-01', 4)])

        self.init_invoice('out_invoice', company=self.company_eur_data['company'], invoice_date='2019-12-25', amounts=[30], post=True)
        self.init_invoice('out_invoice', company=self.company_eur_data['company'], invoice_date='2020-01-15', amounts=[23], post=True)
        self.init_invoice('out_invoice', company=self.company_eur_data['company'], invoice_date='2020-02-20', amounts=[64], post=True)
        self.init_invoice('out_invoice', company=self.company_eur_data['company'], invoice_date='2020-03-30', amounts=[100], post=True)
        self._generate_equity_move(self.company_eur_data, '2020-03-15', 20)
        self._generate_equity_move(self.company_eur_data, '2020-03-31', 5)

        self.init_invoice('out_invoice', company=self.company_eur_data_2['company'], invoice_date='2019-12-22', amounts=[10], post=True)
        self.init_invoice('out_invoice', company=self.company_eur_data_2['company'], invoice_date='2020-03-14', amounts=[54], post=True)
        self.init_invoice('out_invoice', company=self.company_eur_data_2['company'], invoice_date='2020-04-10', amounts=[77], post=True)
        self._generate_equity_move(self.company_eur_data_2, '2020-05-21', 40)

        # CHF OPERATIONS
        self.setup_other_currency('CHF', rates=[('2018-03-01', 10), ('2019-01-01', 3), ('2020-03-30', 7), ('2020-05-10', 8), ('2020-12-25', 2)])

        self.init_invoice('out_invoice', company=self.company_chf_data['company'], invoice_date='2019-12-31', amounts=[50], post=True)
        self.init_invoice('out_invoice', company=self.company_chf_data['company'], invoice_date='2020-01-16', amounts=[58], post=True)
        self.init_invoice('out_invoice', company=self.company_chf_data['company'], invoice_date='2020-05-01', amounts=[99], post=True)
        self.init_invoice('out_invoice', company=self.company_chf_data['company'], invoice_date='2020-12-31', amounts=[22], post=True)
        self._generate_equity_move(self.company_chf_data, '2020-03-15', 20)

        # MXN OPERATIONS
        self.setup_other_currency('MXN', rates=[('2020-05-10', 2)])
        self.init_invoice('out_invoice', company=self.company_mxn_data['company'], invoice_date='2020-01-01', amounts=[10], post=True)
        self.init_invoice('out_invoice', company=self.company_mxn_data['company'], invoice_date='2020-07-01', amounts=[21], post=True)
        self._generate_equity_move(self.company_mxn_data, '2020-03-15', 2)

        # Test conversion : date range cta
        self.report.currency_translation = 'cta'
        cta_options_range = self._generate_options(self.report, '2019-12-22', '2020-12-31')

        self.assertLinesValues(
            self.report._get_lines(cta_options_range),
            [   0,                          1],
            [
                ("Asset",              239.80),
                ("USD Company 1",       10.00),
                ("USD Company 2",       25.00),
                # EUR closing rate: 2019=1/11 ; 2020=1/4
                ("EUR Company 1",       49.48),  # 30 / 11 + (23 + 64 + 100) / 4
                ("EUR Company 2",       33.66),  # 10 / 11 + (54 + 77) / 4
                # CHF closing rate: 2019=1/3 ; 2020=1/2
                ("CHF Company",        106.17),  # 50 / 3 + (58 + 99 + 22) / 2
                # MXN closing rate = 1/2
                ("MXN Company",         15.50),  # (10 + 21) / 2
                ("Income",            -203.15),
                ("USD Company 1",      -10.00),
                ("USD Company 2",      -25.00),
                # EUR average rate = (1/11 * 10 + 1/2 * 71 + 1/5 * 18 + 1/20 * 2 + 1/4 * 275) / 376 = 0.289518859
                ("EUR Company 1",      -62.83),  # (-30 -23 - 64 - 100) * 0.289518859
                ("EUR Company 2",      -40.82),  # (-10 -54 - 77) * 0.289518859
                # CHF average rate = (1/3 * 99 + 1/7 * 41 + 1/8 * 229 + 1/2 * 7) / 376 = 0.188782295
                ("CHF Company",        -43.23),  # (-50 -58 - 99 -22) * 0.188782295
                # MXN average rate = (1 * 140 + 1/2 * 236) / 376 = 0.686170213
                ("MXN Company",        -21.27),  # (-10 - 21) * 0.686170213
                ("Equity",             163.92),
                ("USD Company 1",      130.00),
                ("USD Company 2",       11.00),
                ("EUR Company 1",        4.25),  # 20 / 5 + 5 / 20
                ("EUR Company 2",       10.00),  # 40 / 4
                ("CHF Company",          6.67),  # 20 / 3
                ("MXN Company",          2.00),  # 2 / 1
            ],
            cta_options_range,
        )

        # Test conversion : single cta
        self.report.currency_translation = 'cta'
        self.report.filter_date_range = False
        cta_options_single = self._generate_options(self.report, '2020-12-31', '2020-12-31')

        self.assertLinesValues(
            self.report._get_lines(cta_options_single),
            [   0,                          1],
            [
                ("Asset",              239.80),
                ("USD Company 1",       10.00),
                ("USD Company 2",       25.00),
                # EUR closing rate: 2019=1/11 ; 2020=1/4
                ("EUR Company 1",       49.48),  # 30 / 11 + (23 + 64 + 100) / 4
                ("EUR Company 2",       33.66),  # 10 / 11 + (54 + 77) / 4
                # CHF closing rate: 2019=1/3 ; 2020=1/2
                ("CHF Company",        106.17),  # 50 / 3 + (58 + 99 + 22) / 2
                # MXN current rate = 1/2
                ("MXN Company",         15.50),  # (10 + 21) / 2
                ("Income",            -203.92),
                ("USD Company 1",      -10.00),
                ("USD Company 2",      -25.00),
                # EUR average rate = (1/2 * 71 + 1/5 * 18 + 1/20 * 2 + 1/4 * 275) / 366 = 0.294945355
                ("EUR Company 1",      -64.00),  # (-30 -23 - 64 - 100) * 0.294945355
                ("EUR Company 2",      -41.59),  # (-10 -54 - 77) * 0.294945355
                # CHF average rate = (1/3 * 89 + 1/7 * 41 + 1/8 * 229 + 1/2 * 7) / 366 = 0.184832813
                ("CHF Company",        -42.33),  # (-50 -58 - 99 -22) * 0.184832813
                # MXN average rate = (1 * 130 + 1/2 * 236) / 366 = 0.677595628
                ("MXN Company",        -21.01),  # (-10 - 21) * 0.677595628
                ("Equity",             163.92),
                ("USD Company 1",      130.00),
                ("USD Company 2",       11.00),
                ("EUR Company 1",        4.25),  # 20 / 5 + 5 / 20
                ("EUR Company 2",       10.00),  # 40 / 4
                ("CHF Company",          6.67),  # 20 / 3
                ("MXN Company",          2.00),  # 2 / 1
            ],
            cta_options_single,
        )

        # Test conversion : current : date range and single
        current_expected_lines = [
            # EUR current rate = 1/4
            # CHF current rate = 1/2
            ("Asset",              254.50),
            ("USD Company 1",       10.00),
            ("USD Company 2",       25.00),
            ("EUR Company 1",       54.25),  # (30 + 23 + 64 + 100) / 4
            ("EUR Company 2",       35.25),  # (10 + 54 + 77) / 4
            ("CHF Company",        114.50),  # (50 + 58 + 99 + 22) / 2
            ("MXN Company",         15.50),  # (10 + 21) / 2
            ("Income",            -254.50),
            ("USD Company 1",      -10.00),
            ("USD Company 2",      -25.00),
            ("EUR Company 1",      -54.25),  # (-30 -23 - 64 - 100) / 4
            ("EUR Company 2",      -35.25),  # (-10 -54 - 77) / 4
            ("CHF Company",       -114.50),  # (-50 -58 - 99 -22) / 2
            ("MXN Company",        -15.50),  # (-10 - 21) / 2
            ("Equity",             168.25),

            ("USD Company 1",      130.00),
            ("USD Company 2",       11.00),
            ("EUR Company 1",        6.25),  # (20 + 5) / 4
            ("EUR Company 2",       10.00),  # 40 / 4
            ("CHF Company",         10.00),  # 20 / 2
            ("MXN Company",          1.00),  # 2 / 2
        ]

        self.report.currency_translation = 'current'

        current_options_range = self._generate_options(self.report, '2020-01-01', '2020-12-31')
        self.assertLinesValues(
            self.report._get_lines(current_options_range),
            [0, 1],
            current_expected_lines,
            current_options_range,
        )

        self.report.filter_date_range = False
        current_options_single = self._generate_options(self.report, '2020-12-31', '2020-12-31')
        self.assertLinesValues(
            self.report._get_lines(current_options_single),
            [0, 1],
            current_expected_lines,
            current_options_single,
        )

    def test_currency_table_monocurrency(self):
        self.init_invoice('out_invoice', company=self.company_usd_data['company'], invoice_date='2020-01-01', amounts=[63], post=True)
        self.init_invoice('out_invoice', company=self.company_usd_data_2['company'], invoice_date='2020-01-01', amounts=[42], post=True)
        self._generate_equity_move(self.company_usd_data, '2020-11-11', 88)
        self._generate_equity_move(self.company_usd_data_2, '2020-11-11', 92)

        self.env.companies = self.company_usd_data['company'] + self.company_usd_data_2['company']
        options = self._generate_options(self.report, '2020-01-01', '2020-12-31')
        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                          1],
            [
                ("Asset",              105.00),
                ("USD Company 1",       63.00),
                ("USD Company 2",       42.00),
                ("Income",            -105.00),
                ("USD Company 1",      -63.00),
                ("USD Company 2",      -42.00),
                ("Equity",             180.00),
                ("USD Company 1",       88.00),
                ("USD Company 2",       92.00),
            ],
            options,
        )

    def test_currency_table_comparison(self):
        # EUR operations
        self.setup_other_currency('EUR', rates=[('2018-01-01', 7), ('2019-01-01', 2), ('2020-03-12', 5), ('2021-03-30', 20), ('2022-04-01', 4)])

        self.init_invoice('out_invoice', company=self.company_eur_data['company'], invoice_date='2019-01-01', amounts=[14], post=True)
        self.init_invoice('out_invoice', company=self.company_eur_data['company'], invoice_date='2020-01-01', amounts=[24], post=True)
        self._generate_equity_move(self.company_eur_data, '2019-11-11', 55)
        self._generate_equity_move(self.company_eur_data, '2020-11-11', 99)

        # CHF operations
        self.setup_other_currency('CHF', rates=[('2018-01-01', 10), ('2019-01-01', 4), ('2019-03-12', 5), ('2021-03-30', 20), ('2022-04-01', 4)])

        self.init_invoice('out_invoice', company=self.company_chf_data['company'], invoice_date='2019-01-01', amounts=[20], post=True)
        self.init_invoice('out_invoice', company=self.company_chf_data['company'], invoice_date='2020-01-01', amounts=[66], post=True)
        self._generate_equity_move(self.company_chf_data, '2019-11-11', 12)
        self._generate_equity_move(self.company_chf_data, '2020-11-11', 84)

        options = self._generate_options(self.report, '2020-01-01', '2020-12-31')
        options = self._update_comparison_filter(options, self.report, 'previous_period', 1)

        self.assertLinesValues(
            self.report._get_lines(options),
            #                            2020        2019
            [   0,                          1,          2],
            [
                ("Asset",               18.00,      11.00),
                # EUR clsing rate: 2020 = 1/5 ; 2019 = 1/2
                ("EUR Company 1",        4.80,       7.00),
                # CHF closing rate: 2020 = 1/5 ; 2019 = 1/5
                ("CHF Company",         13.20,       4.00),
                ("Income",             -19.40,     -11.19),
                # EUR average rate in 2020: (1/2 * 71 + 1/5 * 295) / 366 = 0.258196721
                # EUR average rate in 2019: 1/2
                ("EUR Company 1",       -6.20,      -7.00),
                # CHF average rate in 2020: 1/5
                # CHF average rate in 2019: (1/4 * 70 + 1/5 * 295) / 365 = 0.209589041
                ("CHF Company",        -13.20,      -4.19),
                ("Equity",              36.60,      29.90),
                ("EUR Company 1",       19.80,      27.50),
                ("CHF Company",         16.80,       2.40),
            ],
            options,
        )

    def test_currency_table_branches(self):
        usd_branch_data = self.setup_other_company(
            name='USD Branch',
            parent_id=self.company_usd_data['company'].id,
            sequence=self.company_usd_data['company'].sequence,
        )

        eur_branch_data = self.setup_other_company(
            name='EUR Branch',
            parent_id=self.company_eur_data['company'].id,
            sequence=self.company_eur_data['company'].sequence,
        )

        usd_branch_data['company'].totals_below_sections = False

        # Add equity accounts to branch data
        usd_branch_data['equity_account'] = self.company_usd_data['equity_account']
        eur_branch_data['equity_account'] = self.company_eur_data['equity_account']

        # Create rates on the root USD company
        self.setup_other_currency('EUR', rates=[('2020-01-01', 4), ('2020-03-01', 2), ('2020-12-01', 5)])

        # Create some entries
        self.init_invoice('out_invoice', company=self.company_usd_data['company'], invoice_date='2020-11-01', amounts=[10], post=True)
        self.init_invoice('out_invoice', company=usd_branch_data['company'], invoice_date='2020-09-01', amounts=[20], post=True)
        self.init_invoice('out_invoice', company=self.company_eur_data['company'], invoice_date='2020-06-25', amounts=[30], post=True)
        self.init_invoice('out_invoice', company=eur_branch_data['company'], invoice_date='2020-02-23', amounts=[40], post=True)

        self._generate_equity_move(self.company_usd_data, '2020-11-12', 50)
        self._generate_equity_move(usd_branch_data, '2020-01-21', 60)
        self._generate_equity_move(self.company_eur_data, '2020-05-12', 70)
        self._generate_equity_move(eur_branch_data, '2020-09-09', 80)

        # env.company becomes the USD branch
        self.env.companies = usd_branch_data['company'] + eur_branch_data['company'] + self.company_usd_data['company'] + self.company_eur_data['company']
        self.env.company = usd_branch_data['company']

        options = self._generate_options(self.report, '2020-01-01', '2020-12-31')
        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                          1],
            [
                ("Asset",               44.00),
                ("USD Branch",          20.00),
                ("USD Company 1",       10.00),
                # EUR 2020 closing rate = 1/5
                ("EUR Branch",           8.00),
                ("EUR Company 1",        6.00),
                ("Income",             -60.35),
                ("USD Branch",         -20.00),
                ("USD Company 1",      -10.00),
                # EUR average rate = (1/4 * 60 + 1/2 * 275 + 1/5 * 31) / 366 = 0.433606557
                ("EUR Branch",         -17.34),
                ("EUR Company 1",      -13.01),
                ("Equity",             185.00),
                ("USD Branch",          60.00),
                ("USD Company 1",       50.00),
                ("EUR Branch",          40.00),
                ("EUR Company 1",       35.00),

            ],
            options,
        )

    def test_currency_table_no_rate(self):
        self.init_invoice('out_invoice', company=self.company_usd_data['company'], invoice_date='2020-11-01', amounts=[10], post=True)
        self._generate_equity_move(self.company_usd_data, '2020-11-12', 20)
        self.init_invoice('out_invoice', company=self.company_eur_data['company'], invoice_date='2020-02-23', amounts=[30], post=True)
        self._generate_equity_move(self.company_eur_data, '2020-05-12', 40)

        options = self._generate_options(self.report, '2020-01-01', '2020-12-31')
        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                          1],
            [
                ("Asset",               40.00),
                ("USD Company 1",       10.00),
                ("EUR Company 1",       30.00),
                ("Income",             -40.00),
                ("USD Company 1",      -10.00),
                ("EUR Company 1",      -30.00),
                ("Equity",              60.00),
                ("USD Company 1",       20.00),
                ("EUR Company 1",       40.00),
            ],
            options,
        )

    def test_currency_table_non_1_domestic_rate(self):
        self.setup_other_currency('USD', rates=[('2020-01-01', 0.5)])
        self.setup_other_currency('EUR', rates=[('2020-01-01', 4), ('2020-03-01', 2), ('2020-12-01', 5)])

        self.init_invoice('out_invoice', company=self.company_usd_data['company'], invoice_date='2020-11-01', amounts=[10], post=True)
        self._generate_equity_move(self.company_usd_data, '2020-11-12', 20)

        self.init_invoice('out_invoice', company=self.company_eur_data['company'], invoice_date='2020-02-23', amounts=[30], post=True)
        self._generate_equity_move(self.company_eur_data, '2020-05-12', 40)

        options = self._generate_options(self.report, '2020-01-01', '2020-12-31')
        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                          1],
            [
                ("Asset",               13.00),
                ("USD Company 1",       10.00),
                # EUR 2020 closing rate = 0.5/5
                ("EUR Company 1",        3.00),
                ("Income",             -16.50),
                ("USD Company 1",      -10.00),
                # EUR average rate = (0.5/4 * 60 + 0.5/2 * 275 + 0.5/5 * 31) / 366 = 0.216803279
                ("EUR Company 1",       -6.50),
                ("Equity",              30.00),
                ("USD Company 1",       20.00),
                ("EUR Company 1",       10.00),  # rate = 0.5/2
            ],
            options,
        )

    def test_currency_table_manual_line_expansion(self):
        self.setup_other_currency('EUR', rates=[('2020-01-01', 2)])
        self.init_invoice('out_invoice', company=self.company_eur_data['company'], invoice_date='2020-12-22', amounts=[42], post=True)

        self.report.line_ids.foldable = True

        options = self._generate_options(self.report, '2020-01-01', '2020-12-31')
        line_to_expand_id = self.report._get_generic_line_id('account.report.line', self.report.line_ids[0].id)
        self.assertLinesValues(
            self.report.get_expanded_lines(options, line_to_expand_id, 'company_id', '_report_expand_unfoldable_line_with_groupby', 0, 0, None),
            [   0,                          1],
            [
                ("EUR Company 1",       21.00),
            ],
            options,
        )

    def test_currency_table_closing_rate_manual_fiscal_year(self):
        self.env['account.fiscal.year'].create([
            {
                'name': "Year 1",
                'date_from': '2019-03-12',
                'date_to': '2019-12-22',
            },
            {
                'name': "Year 2",
                'date_from': '2019-12-23',
                'date_to': '2020-05-02',
            },
            {
                'name': "Year 3",
                'date_from': '2020-05-03',
                'date_to': '2020-12-31',
            },
            # Create a bunch of fiscal years on other companies as well to make sure they do not interfere
            {
                'name': "EUR year 1",
                'date_from': '2018-05-09',
                'date_to': '2019-07-07',
                'company_id': self.company_eur_data['company'].id,
            },
            {
                'name': "EUR year 2",
                'date_from': '2019-07-08',
                'date_to': '2020-11-11',
                'company_id': self.company_eur_data['company'].id,
            },
            {
                'name': "CHF year 1",
                'date_from': '2019-02-01',
                'date_to': '2020-12-01',
                'company_id': self.company_chf_data['company'].id,
            },
        ])

        self.setup_other_currency('EUR', rates=[
            ('2018-10-10', 7),
            ('2019-01-22', 11),
            # Year 1
            ('2019-03-13', 1),
            ('2019-05-01', 5),
            ('2019-10-01', 8),
            # Year 2
            ('2019-12-31', 2),
            # Year 3
            ('2020-06-12', 5),
            ('2020-08-30', 20),
            # Year 4
            ('2021-01-03', 13),
        ])

        self.setup_other_currency('CHF', rates=[
            # Year 1
            # Year 2, 3, 4
            ('2019-12-23', 10),
        ])

        # Invoices - Year 1
        self.init_invoice('out_invoice', company=self.company_usd_data['company'], invoice_date='2019-04-01', amounts=[150], post=True)
        self.init_invoice('out_invoice', company=self.company_eur_data['company'], invoice_date='2019-04-01', amounts=[30], post=True)
        self.init_invoice('out_invoice', company=self.company_eur_data['company'], invoice_date='2019-11-01', amounts=[62], post=True)
        self.init_invoice('out_invoice', company=self.company_eur_data_2['company'], invoice_date='2019-10-01', amounts=[12], post=True)
        self.init_invoice('out_invoice', company=self.company_chf_data['company'], invoice_date='2019-12-01', amounts=[100], post=True)

        # Invoices - Year 2
        self.init_invoice('out_invoice', company=self.company_usd_data['company'], invoice_date='2020-04-01', amounts=[250], post=True)
        self.init_invoice('out_invoice', company=self.company_eur_data['company'], invoice_date='2019-12-30', amounts=[44], post=True)
        self.init_invoice('out_invoice', company=self.company_eur_data['company'], invoice_date='2020-02-06', amounts=[68], post=True)
        self.init_invoice('out_invoice', company=self.company_chf_data['company'], invoice_date='2020-01-30', amounts=[44], post=True)

        # Invoices - Year 3
        self.init_invoice('out_invoice', company=self.company_usd_data['company'], invoice_date='2020-06-01', amounts=[350], post=True)
        self.init_invoice('out_invoice', company=self.company_eur_data['company'], invoice_date='2020-07-06', amounts=[14], post=True)
        self.init_invoice('out_invoice', company=self.company_chf_data['company'], invoice_date='2020-12-06', amounts=[24], post=True)

        # Invoices - Year 4
        self.init_invoice('out_invoice', company=self.company_usd_data['company'], invoice_date='2021-04-01', amounts=[450], post=True)
        self.init_invoice('out_invoice', company=self.company_eur_data['company'], invoice_date='2021-02-06', amounts=[35], post=True)
        self.init_invoice('out_invoice', company=self.company_chf_data['company'], invoice_date='2021-12-12', amounts=[97], post=True)

        self.report.line_ids[1:].unlink()  # We don't need them for this check
        options = self._generate_options(self.report, '2018-01-01', '2022-12-31')

        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                          1],
            [
                ("Asset",             1388.89),
                ("USD Company 1",     1200.00),  # 150 + 250 + 350 + 450
                # EUR closing rate: Year 1=1/8, Year 2=1/2, Year 3=1/20, Year 4=1/13
                ("EUR Company 1",       70.89),  # (30 + 62) / 8 + (44 + 68) / 2 + 14 / 20 + 35 / 13
                ("EUR Company 2",        1.50),  # 12 / 8
                # CHF closing rate: Year 1=1, Year 2, 3, 4=1/10
                ("CHF Company",        116.50),  # 100 / 1 + 44 / 10 + 24 / 10 + 97 / 10
            ],
            options,
        )

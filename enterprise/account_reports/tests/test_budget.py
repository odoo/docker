from odoo import Command, fields
from odoo.tests import tagged
from odoo.tools import date_utils
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install', '-at_install')
class TestBudgetReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].totals_below_sections = False

        cls.account_1 = cls.company_data['default_account_revenue']
        cls.account_2 = cls.copy_account(cls.account_1)
        cls.account_3 = cls.copy_account(cls.account_1)
        cls.account_4 = cls.copy_account(cls.account_1)

        # Create a test report
        cls.report = cls.env['account.report'].create({
            'name': "Budget Test",
            'filter_date_range': True,
            'filter_budgets': True,
            'filter_period_comparison': True,
            'column_ids': [
                Command.create({
                    'name': "Balance",
                    'expression_label': 'balance',
                }),
            ],
            'line_ids': [
                Command.create({
                    'name': 'line_domain',
                    'groupby': 'account_id',
                    'foldable': False,
                    'expression_ids': [
                        Command.create({
                            'label': 'balance',
                            'formula': "[('account_id.account_type', '=', 'income')]",
                            'subformula': 'sum',
                            'engine': 'domain',
                        }),
                    ],
                }),
                Command.create({
                    'name': 'line_account_codes',
                    'groupby': 'account_id',
                    'foldable': False,
                    'expression_ids': [
                        Command.create({
                            'label': 'balance',
                            'formula': cls.account_1.code[:3],
                            'engine': 'account_codes',
                        }),
                    ],
                }),
            ],
        })

        # Create budgets
        cls.budget_1 = cls._create_budget(
            {
                cls.account_1.id: 1000,
                cls.account_3.id: 100,
                cls.account_4.id: 10,
            },
            '2020-01-01',
            '2020-01-01',
        )
        cls.budget_2 = cls._create_budget(
            {
                cls.account_2.id: 10,
            },
            '2020-01-01',
            '2020-01-01',
        )

    @classmethod
    def _create_budget(cls, amount_per_account_ids=None, date_from=None, date_to=None):
        date_from, date_to = fields.Date.to_date(date_from), fields.Date.to_date(date_to)
        items = []
        for account_id, amount in amount_per_account_ids.items():
            for item_date in date_utils.date_range(date_from, date_to):
                items.append(Command.create({
                    'amount': amount,
                    'account_id': account_id,
                    'date': date_utils.start_of(item_date, 'month'),
                }))

        return cls.env['account.report.budget'].create({
            'name': 'Budget',
            'item_ids': items,
        })

    @classmethod
    def _create_moves(cls, amount_per_account_ids=None, date_from=None, date_to=None, to_post=True):
        date_from, date_to = fields.Date.to_date(date_from), fields.Date.to_date(date_to)
        moves_to_create = []
        for move_date in date_utils.date_range(date_from, date_to):
            move_to_create = {
                'date': move_date,
                'journal_id': cls.company_data['default_journal_misc'].id,
                'line_ids': [],
            }
            for account_id, amount in amount_per_account_ids.items():
                move_to_create['line_ids'].extend([
                    Command.create({
                        'debit': amount,
                        'account_id': account_id,
                    }),
                    Command.create({
                        'credit': amount,
                        'account_id': cls.company_data['default_account_assets'].id,
                    })
                ])
            moves_to_create.append(move_to_create)
        moves = cls.env['account.move'].create(moves_to_create)
        if to_post:
            moves.action_post()
        return moves

    def test_reports_single_budget(self):
        self._create_moves(
            {
                self.account_1.id: 100,
                self.account_2.id: 200,
                self.account_3.id: 300,
             },
            '2020-01-01',
            '2020-01-01',
        )

        options = self._generate_options(
            self.report,
            '2020-01-01',
            '2020-12-31',
            default_options={'budgets': [{'id': self.budget_1.id, 'selected': True}]},
        )

        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            [   0,                                             1,        2,          3],
            [
                ('line_domain',                              600,     1110,    '54.1%'),
                (self.account_1.display_name,                100,     1000,    '10.0%'),
                (self.account_2.display_name,                200,        0,      'n/a'),
                (self.account_3.display_name,                300,      100,   '300.0%'),
                (self.account_4.display_name,                  0,       10,     '0.0%'),
                ('line_account_codes',                       600,     1110,    '54.1%'),
                (self.account_1.display_name,                100,     1000,    '10.0%'),
                (self.account_2.display_name,                200,        0,      'n/a'),
                (self.account_3.display_name,                300,      100,   '300.0%'),
                (self.account_4.display_name,                  0,       10,     '0.0%'),
            ],
            options,
        )

    def test_reports_multiple_budgets(self):
        """ This test verifies the report when we have several budgets selected.
            The report should have 2 columns per budget, the budget itself and
            the comparison column.
        """
        self._create_moves(
            {
                self.account_1.id: 100,
                self.account_2.id: 200,
                self.account_3.id: 300,
             },
            '2020-01-01',
            '2020-01-01',
        )

        options = self._generate_options(
            self.report,
            '2020-01-01',
            '2020-12-31',
            default_options={'budgets': [{'id': self.budget_1.id, 'selected': True}, {'id': self.budget_2.id, 'selected': True}]},
        )

        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            [   0,                                             1,        2,          3,        4,          5],
            [
                ('line_domain',                              600,     1110,    '54.1%',       10,   '6000.0%'),
                (self.account_1.display_name,                100,     1000,    '10.0%',        0,       'n/a'),
                (self.account_2.display_name,                200,        0,      'n/a',       10,   '2000.0%'),
                (self.account_3.display_name,                300,      100,   '300.0%',        0,       'n/a'),
                (self.account_4.display_name,                  0,       10,     '0.0%',        0,       'n/a'),
                ('line_account_codes',                       600,     1110,    '54.1%',       10,   '6000.0%'),
                (self.account_1.display_name,                100,     1000,    '10.0%',        0,       'n/a'),
                (self.account_2.display_name,                200,        0,      'n/a',       10,   '2000.0%'),
                (self.account_3.display_name,                300,      100,   '300.0%',        0,       'n/a'),
                (self.account_4.display_name,                  0,       10,     '0.0%',        0,       'n/a'),
            ],
            options,
        )

    def test_reports_budget_with_comparison_period(self):
        budget_2024 = self._create_budget({self.account_1.id: 200}, '2024-01-01', '2024-12-31')
        moves = self._create_moves({self.account_1.id: 200}, '2024-01-01', '2024-12-31', to_post=False)
        moves += self._create_moves({self.account_1.id: 600}, '2024-06-22', '2024-06-22', to_post=False)
        moves.action_post()

        options = self._generate_options(
            self.report,
            '2024-06-01',
            '2024-06-30',
            default_options={
                'budgets': [{'id': budget_2024.id, 'selected': True}],
                'comparison': {'filter': 'previous_period', 'number_period': 1},
            },
        )
        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                                             1,        2,          3,        4,        5,          6],
            [
                ('line_domain',                              800,      200,   '400.0%',      200,      200,   '100.0%'),
                (self.account_1.display_name,                800,      200,   '400.0%',      200,      200,   '100.0%'),
                ('line_account_codes',                       800,      200,   '400.0%',      200,      200,   '100.0%'),
                (self.account_1.display_name,                800,      200,   '400.0%',      200,      200,   '100.0%'),
            ],
            options,
        )

    def test_reports_budget_with_comparison_period_and_multiple_budgets(self):
        budget_2024 = self._create_budget({self.account_1.id: 200}, '2024-01-01', '2024-12-31')
        budget_2023 = self._create_budget({self.account_1.id: 400}, '2023-01-01', '2023-12-31')
        moves = self._create_moves({self.account_1.id: 200}, '2024-01-01', '2024-12-31', to_post=False)
        moves += self._create_moves({self.account_1.id: 400}, '2023-01-01', '2023-12-31', to_post=False)
        moves.action_post()

        options = self._generate_options(
            self.report,
            '2024-01-01',
            '2024-12-31',
            default_options={
                'budgets': [{'id': budget_2024.id, 'selected': True}, {'id': budget_2023.id, 'selected': True}],
                'comparison': {'filter': 'previous_period', 'number_period': 1},
            },
        )
        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                                 1,      2,          3,   4,       5,      6,   7,      8,       9,      10],
            #                        [ Period 2024 + Budget 2024 + % + Budget 2023 + %] [ Period 2023 + Budget 2024 + % + Budget 2023 + %]
            [
                ('line_domain',                 2400,   2400,   '100.0%',   0,   'n/a',   4800,   0,   'n/a',   4800,   '100.0%'),
                (self.account_1.display_name,   2400,   2400,   '100.0%',   0,   'n/a',   4800,   0,   'n/a',   4800,   '100.0%'),
                ('line_account_codes',          2400,   2400,   '100.0%',   0,   'n/a',   4800,   0,   'n/a',   4800,   '100.0%'),
                (self.account_1.display_name,   2400,   2400,   '100.0%',   0,   'n/a',   4800,   0,   'n/a',   4800,   '100.0%'),
            ],
            options,
        )

    def test_report_budget_items_with_different_date_filters(self):
        """ The aim of this test is checking that we get the correct budget items
            according to the selected dates.
        """
        budget_2024 = self._create_budget({self.account_1.id: 300}, '2024-01-01', '2024-12-31')
        self._create_moves({self.account_1.id: 200}, '2024-01-01', '2024-12-31')

        # Case when we display a whole year in the report
        options = self._generate_options(
            self.report,
            '2024-01-01',
            '2024-12-31',
            default_options={'budgets': [{'id': budget_2024.id, 'selected': True}]},
        )
        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                                              1,        2],
            [
                ('line_domain',                              2400,     3600),
                (self.account_1.display_name,                2400,     3600),
                ('line_account_codes',                       2400,     3600),
                (self.account_1.display_name,                2400,     3600),
            ],
            options,
        )

        # Case when we display a whole quarter
        options = self._generate_options(
            self.report,
            '2024-01-01',
            '2024-03-31',
            default_options={'budgets': [{'id': budget_2024.id, 'selected': True}]},
        )
        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                                             1,        2],
            [
                ('line_domain',                              600,      900),
                (self.account_1.display_name,                600,      900),
                ('line_account_codes',                       600,      900),
                (self.account_1.display_name,                600,      900),
            ],
            options,
        )

        # Case when we display a whole month
        options = self._generate_options(
            self.report,
            '2024-03-01',
            '2024-03-31',
            default_options={'budgets': [{'id': budget_2024.id, 'selected': True}]},
        )
        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                                             1,        2],
            [
                ('line_domain',                              200,      300),
                (self.account_1.display_name,                200,      300),
                ('line_account_codes',                       200,      300),
                (self.account_1.display_name,                200,      300),
            ],
            options,
        )

    def test_report_budget_edit_items(self):
        """ This test verifies the way we're modifying budget items.
            The system calculates the difference between the old and new values
            and distributes this difference proportionally over the number of
            months in the selected period.

            The test checks the following scenarios:
            1. Adding a rounded value (1200) for an entire year (12 months).
            2. Setting the value to 300 for 3 months (no change expected).
            3. Setting the value to 900 for 3 months, resulting in three new values of 200 each.
            4. Reducing the value for a whole year to a non-rounded value and checking if the
               remainder is correctly applied to the last period.
        """
        def set_budget_item(value, account_id):
            budget_2024._create_or_update_budget_items(
                value_to_set=value,
                account_id=account_id,
                rounding=self.env.company.currency_id.decimal_places,
                date_from=options['date']['date_from'],
                date_to=options['date']['date_to'],
            )

        budget_2024 = self.env['account.report.budget'].create({'name': "Budget 2024"})
        self._create_moves({self.account_1.id: 200}, '2024-01-01', '2024-12-31')

        options = self._generate_options(
            self.report,
            '2024-01-01',
            '2024-12-31',
            default_options={'budgets': [{'id': budget_2024.id, 'selected': True}]},
        )
        set_budget_item(1200, self.account_1.id)
        expected_items = [
            {'amount': 100.0, 'date': fields.Date.to_date('2024-01-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-02-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-03-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-04-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-05-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-06-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-07-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-08-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-09-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-10-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-11-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-12-01')},
        ]

        self.assertRecordValues(
            budget_2024.item_ids,
            expected_items,
        )
        options = self._generate_options(
            self.report,
            '2024-01-01',
            '2024-03-31',
            default_options={'budgets': [{'id': budget_2024.id, 'selected': True}]},
        )
        set_budget_item(300, self.account_1.id)
        # Nothing should be added as we don't change anything
        self.assertRecordValues(
            budget_2024.item_ids,
            expected_items,
        )

        set_budget_item(900, self.account_1.id)
        expected_items = [
            {'amount': 300.0, 'date': fields.Date.to_date('2024-01-01')},
            {'amount': 300.0, 'date': fields.Date.to_date('2024-02-01')},
            {'amount': 300.0, 'date': fields.Date.to_date('2024-03-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-04-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-05-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-06-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-07-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-08-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-09-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-10-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-11-01')},
            {'amount': 100.0, 'date': fields.Date.to_date('2024-12-01')},
        ]
        self.assertRecordValues(
            budget_2024.item_ids,
            expected_items,
        )

        options = self._generate_options(
            self.report,
            '2024-01-01',
            '2024-12-31',
            default_options={'budgets': [{'id': budget_2024.id, 'selected': True}]},
        )
        self.assertLinesValues(
            self.report._get_lines(options),
            [   0,                                              1,        2],
            [
                ('line_domain',                              2400,     1800),
                (self.account_1.display_name,                2400,     1800),
                ('line_account_codes',                       2400,     1800),
                (self.account_1.display_name,                2400,     1800),
            ],
            options,
        )

        # Test the case with a remainder
        set_budget_item(1000, self.account_1.id)
        expected_items = [
            {'amount': 300.0 - 66.66, 'date': fields.Date.to_date('2024-01-01')},
            {'amount': 300.0 - 66.66, 'date': fields.Date.to_date('2024-02-01')},
            {'amount': 300.0 - 66.66, 'date': fields.Date.to_date('2024-03-01')},
            {'amount': 100.0 - 66.66, 'date': fields.Date.to_date('2024-04-01')},
            {'amount': 100.0 - 66.66, 'date': fields.Date.to_date('2024-05-01')},
            {'amount': 100.0 - 66.66, 'date': fields.Date.to_date('2024-06-01')},
            {'amount': 100.0 - 66.66, 'date': fields.Date.to_date('2024-07-01')},
            {'amount': 100.0 - 66.66, 'date': fields.Date.to_date('2024-08-01')},
            {'amount': 100.0 - 66.66, 'date': fields.Date.to_date('2024-09-01')},
            {'amount': 100.0 - 66.66, 'date': fields.Date.to_date('2024-10-01')},
            {'amount': 100.0 - 66.66, 'date': fields.Date.to_date('2024-11-01')},
            {'amount': 100.0 - 66.74, 'date': fields.Date.to_date('2024-12-01')},
        ]
        self.assertRecordValues(
            budget_2024.item_ids,
            expected_items,
        )

    def test_report_budget_show_all_accounts_filter(self):
        """ The aim of this test is checking that the show all accounts filter
            is returning all the income accounts (as our test report is working with
            income accounts only).
        """
        budget_2024 = self._create_budget({self.account_1.id: 300}, '2024-01-01', '2024-12-31')

        options = self._generate_options(
            self.report,
            '2024-01-01',
            '2024-12-31',
            default_options={
                'budgets': [{'id': budget_2024.id, 'selected': True}],
                'show_all_accounts': True,
            },
        )
        expected_lines = [
            ('line_domain', 0, 3600),
            (self.account_1.display_name, 0, 3600),
        ]
        expected_lines += [
            (account['display_name'], 0, 0)
            for account in self.env['account.account'].search_read([
                ('id', '!=', self.account_1.id),
                ('account_type', '=', 'income'),
                ('company_ids', 'in', self.report.get_report_company_ids(options)),
            ], ['display_name'], order='code')
        ]
        expected_lines += [
            ('line_account_codes', 0, 3600),
            (self.account_1.display_name, 0, 3600),
        ]
        expected_lines += [
            (account['display_name'], 0, 0)
            for account in self.env['account.account'].search_read([
                ('id', '!=', self.account_1.id),
                ('code', '=like', f'{self.account_1.code[:3]}%'),
                ('company_ids', 'in', self.report.get_report_company_ids(options)),
            ], ['display_name'], order='code')
        ]

        self.assertLinesValues(
            self.report._get_lines(options),
            [0, 1, 2],
            expected_lines,
            options,
        )

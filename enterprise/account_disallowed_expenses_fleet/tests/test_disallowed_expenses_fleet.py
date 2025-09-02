# -*- coding: utf-8 -*-

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon

from odoo import Command, fields
from odoo.tests import tagged, freeze_time


@freeze_time('2022-07-15')
@tagged('post_install', '-at_install')
class TestAccountDisallowedExpensesFleetReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.dna_category = cls.env['account.disallowed.expenses.category'].create({
            'code': '2345',
            'name': 'DNA category',
            'rate_ids': [
                Command.create({
                    'date_from': fields.Date.from_string('2022-01-01'),
                    'rate': 60.0,
                    'company_id': cls.company_data['company'].id,
                }),
                Command.create({
                    'date_from': fields.Date.from_string('2022-04-01'),
                    'rate': 40.0,
                    'company_id': cls.company_data['company'].id,
                }),
                Command.create({
                    'date_from': fields.Date.from_string('2022-08-01'),
                    'rate': 23.0,
                    'company_id': cls.company_data['company'].id,
                }),
            ],
        })

        cls.company_data['default_account_expense'].disallowed_expenses_category_id = cls.dna_category.id
        cls.company_data['default_account_expense_2'] = cls.company_data['default_account_expense'].copy()
        cls.company_data['default_account_expense_2'].disallowed_expenses_category_id = cls.dna_category.id

        cls.batmobile, cls.batpod = cls.env['fleet.vehicle'].create([
            {
                'model_id': cls.env['fleet.vehicle.model'].create({
                    'name': name,
                    'brand_id': cls.env['fleet.vehicle.model.brand'].create({
                        'name': 'Wayne Enterprises',
                    }).id,
                    'vehicle_type': vehicle_type,
                    'default_fuel_type': 'hydrogen',
                }).id,
                'rate_ids': [Command.create({
                    'date_from': fields.Date.from_string('2022-01-01'),
                    'rate': rate,
                })],
            } for name, vehicle_type, rate in [('Batmobile', 'car', 31.0), ('Batpod', 'bike', 56.0)]
        ])

        cls.env['fleet.disallowed.expenses.rate'].create({
            'rate': 23.0,
            'date_from': '2022-05-01',
            'vehicle_id': cls.batmobile.id,
        })

        bill_1 = cls.env['account.move'].create({
            'partner_id': cls.partner_a.id,
            'move_type': 'in_invoice',
            'date': fields.Date.from_string('2022-01-15'),
            'invoice_date': fields.Date.from_string('2022-01-15'),
            'invoice_line_ids': [
                Command.create({
                    'name': 'Test',
                    'quantity': 1,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(cls.company_data['default_tax_purchase'].ids)],
                    'account_id': cls.company_data['default_account_expense'].id,
                }),
                Command.create({
                    'vehicle_id': cls.batmobile.id,
                    'quantity': 1,
                    'price_unit': 200.0,
                    'tax_ids': [Command.set(cls.company_data['default_tax_purchase'].ids)],
                    'account_id': cls.company_data['default_account_expense'].id,
                }),
                Command.create({
                    'vehicle_id': cls.batpod.id,
                    'quantity': 1,
                    'price_unit': 300.0,
                    'tax_ids': [Command.set(cls.company_data['default_tax_purchase'].ids)],
                    'account_id': cls.company_data['default_account_expense'].id,
                }),
                Command.create({
                    'vehicle_id': cls.batpod.id,
                    'quantity': 1,
                    'price_unit': 400.0,
                    'tax_ids': [Command.set(cls.company_data['default_tax_purchase'].ids)],
                    'account_id': cls.company_data['default_account_expense_2'].id,
                }),
            ],
        })

        # Create a second bill at a later date in order to have multiple rates in the annual report.
        bill_2 = cls.env['account.move'].create({
            'partner_id': cls.partner_a.id,
            'move_type': 'in_invoice',
            'date': fields.Date.from_string('2022-05-15'),
            'invoice_date': fields.Date.from_string('2022-05-15'),
            'invoice_line_ids': [
                Command.create({
                    'name': 'Test',
                    'quantity': 1,
                    'price_unit': 400.0,
                    'tax_ids': [Command.set(cls.company_data['default_tax_purchase'].ids)],
                    'account_id': cls.company_data['default_account_expense'].id,
                }),
                Command.create({
                    'vehicle_id': cls.batmobile.id,
                    'quantity': 1,
                    'price_unit': 500.0,
                    'tax_ids': [Command.set(cls.company_data['default_tax_purchase'].ids)],
                    'account_id': cls.company_data['default_account_expense_2'].id,
                }),
                Command.create({
                    'vehicle_id': cls.batmobile.id,
                    'quantity': 1,
                    'price_unit': 600.0,
                    'tax_ids': [Command.set(cls.company_data['default_tax_purchase'].ids)],
                    'account_id': cls.company_data['default_account_expense'].id,
                }),
            ],
        })

        # Create a third bill with yet another date.
        bill_3 = cls.env['account.move'].create({
            'partner_id': cls.partner_a.id,
            'move_type': 'in_invoice',
            'date': fields.Date.from_string('2022-08-15'),
            'invoice_date': fields.Date.from_string('2022-08-15'),
            'invoice_line_ids': [
                Command.create({
                    'name': 'Test',
                    'quantity': 1,
                    'price_unit': 700.0,
                    'tax_ids': [Command.set(cls.company_data['default_tax_purchase'].ids)],
                    'account_id': cls.company_data['default_account_expense'].id,
                }),
            ],
        })

        (bill_1 + bill_2 + bill_3).action_post()

    def _setup_base_report(self, unfold=False, split=False):
        report = self.env.ref('account_disallowed_expenses.disallowed_expenses_report')
        default_options = {'unfold_all': unfold, 'vehicle_split': split}
        options = self._generate_options(report, '2022-01-01', '2022-12-31', default_options)
        self.env.company.totals_below_sections = False
        return report, options

    def _prepare_column_values(self, lines):
        """ Helper that adds each line's level to its columns, so that the level can be tested in assertLinesValues().
            It also cleans unwanted characters in the line name.
        """
        for line in lines:
            # This is just to prevent the name override in l10n_be_hr_payroll_fleet from making the test crash.
            line['name'] = line['name'].split(' \u2022 ')[0]
            line['columns'].append({'name': line['level']})

    def test_disallowed_expenses_report_unfold_all(self):
        report, options = self._setup_base_report(unfold=True)
        lines = report._get_lines(options)
        self._prepare_column_values(lines)

        self.assertLinesValues(
            # pylint: disable=C0326
            lines,
            #   Name                                          Total Amount     Rate          Disallowed Amount    Level
            [   0,                                            1,               2,            3,                   4],
            [
                ('2345 DNA category',                         3200.0,          '',          1088.0,               1),
                  ('600000 Expenses',                         2300.0,          '',           749.0,               2),
                    ('600000 Expenses',                        700.0,          '23.00%',     161.0,               3),
                    ('600000 Expenses',                        600.0,          '23.00%',     138.0,               3),
                    ('600000 Expenses',                        400.0,          '40.00%',     160.0,               3),
                    ('600000 Expenses',                        200.0,          '31.00%',      62.0,               3),
                    ('600000 Expenses',                        300.0,          '56.00%',     168.0,               3),
                    ('600000 Expenses',                        100.0,          '60.00%',      60.0,               3),
                  ('600002 Expenses (copy)',                        900.0,          '',           339.0,               2),
                    ('600002 Expenses (copy)',                      500.0,          '23.00%',     115.0,               3),
                    ('600002 Expenses (copy)',                      400.0,          '56.00%',     224.0,               3),
                ('Total',                                     3200.0,          '',          1088.0,               1),
            ],
            options,
        )

    def test_disallowed_expenses_report_unfold_all_with_vehicle_split(self):
        report, options = self._setup_base_report(unfold=True, split=True)
        lines = report._get_lines(options)
        self._prepare_column_values(lines)

        self.assertLinesValues(
            # pylint: disable=C0326
            lines,
            #   Name                                          Total Amount     Rate          Disallowed Amount    Level
            [   0,                                            1,               2,            3,                   4],
            [
                ('2345 DNA category',                         3200.0,          '',          1088.0,               1),
                  ('Wayne Enterprises/Batmobile/No Plate',    1300.0,          '',           315.0,               2),
                    ('600000 Expenses',                        800.0,          '',           200.0,               3),
                      ('600000 Expenses',                      600.0,          '23.00%',     138.0,               4),
                      ('600000 Expenses',                      200.0,          '31.00%',      62.0,               4),
                    ('600002 Expenses (copy)',                      500.0,          '23.00%',     115.0,               3),
                      ('600002 Expenses (copy)',                    500.0,          '23.00%',     115.0,               4),
                  ('Wayne Enterprises/Batpod/No Plate',        700.0,          '56.00%',     392.0,               2),
                    ('600000 Expenses',                        300.0,          '56.00%',     168.0,               3),
                      ('600000 Expenses',                      300.0,          '56.00%',     168.0,               4),
                    ('600002 Expenses (copy)',                      400.0,          '56.00%',     224.0,               3),
                      ('600002 Expenses (copy)',                    400.0,          '56.00%',     224.0,               4),
                  ('600000 Expenses',                         1200.0,          '',           381.0,               2),
                    ('600000 Expenses',                        700.0,          '23.00%',     161.0,               3),
                    ('600000 Expenses',                        400.0,          '40.00%',     160.0,               3),
                    ('600000 Expenses',                        100.0,          '60.00%',      60.0,               3),
                ('Total',                                     3200.0,          '',          1088.0,               1),
            ],
            options,
        )

    def test_disallowed_expenses_report_comparison(self):
        report, options = self._setup_base_report(unfold=True)
        report.filter_period_comparison = True
        options = self._update_comparison_filter(options, report, comparison_type='previous_period', number_period=1)

        self.mr_freeze_account = self.env['account.account'].create({
            'code': '611011',
            'name': 'Frozen Account',
        })

        self.robins_dna = self.env['account.disallowed.expenses.category'].create({
            'code': '2346',
            'name': 'Robins DNA',
            'account_ids': [Command.set(self.mr_freeze_account.id)],
            'rate_ids': [
                Command.create({
                    'date_from': fields.Date.from_string('2022-08-01'),
                    'rate': 50.0,
                    'company_id': self.company_data['company'].id,
                }),
            ],
        })

        # Create journal entries, using a DNA category without a rate to test totals with blank 'Disallowed Amount'
        entry_data = [
            ('2022-08-15', 21.0),
            ('2022-07-15', 25.0),
            ('2021-08-15', 79.0),
        ]
        self.env['account.move'].create([{
            'move_type': 'entry',
            'date': fields.Date.from_string(entry_date),
            'line_ids': [
                Command.create({
                    'account_id': self.mr_freeze_account.id,
                    'name': 'robin vs mr freeze',
                    'debit': entry_amount,
                }),
                Command.create({
                    'account_id': self.company_data['default_account_revenue'].id,
                    'name': 'robin vs mr freeze',
                    'credit': entry_amount,
                }),
            ]
        } for entry_date, entry_amount in entry_data]).action_post()

        lines = report._get_lines(options)
        self._prepare_column_values(lines)
        self.assertLinesValues(
            # pylint: disable=C0326
            lines,
            #                                    [                    2022                      ]    [                           2021               ]
            #   Name                             Total Amount     Rate          Disallowed Amount    Total Amount     Rate          Disallowed Amount    Level
            [   0,                               1,               2,            3,                   4,               5,            6,                   7],
            [
                ('2345 DNA category',            3200.0,          '',          1088.0,               '',              '',           '',                  1),
                  ('600000 Expenses',            2300.0,          '',           749.0,               '',              '',           '',                  2),
                    ('600000 Expenses',           700.0,          '23.00%',     161.0,               '',              '',           '',                  3),
                    ('600000 Expenses',           600.0,          '23.00%',     138.0,               '',              '',           '',                  3),
                    ('600000 Expenses',           400.0,          '40.00%',     160.0,               '',              '',           '',                  3),
                    ('600000 Expenses',           200.0,          '31.00%',      62.0,               '',              '',           '',                  3),
                    ('600000 Expenses',           300.0,          '56.00%',     168.0,               '',              '',           '',                  3),
                    ('600000 Expenses',           100.0,          '60.00%',      60.0,               '',              '',           '',                  3),
                  ('600002 Expenses (copy)',           900.0,          '',           339.0,               '',              '',           '',                  2),
                    ('600002 Expenses (copy)',         500.0,          '23.00%',     115.0,               '',              '',           '',                  3),
                    ('600002 Expenses (copy)',         400.0,          '56.00%',     224.0,               '',              '',           '',                  3),
                ('2346 Robins DNA',                46.0,          '',            10.5,               79.0,            '',           '',                  1),
                  ('611011 Frozen Account',        46.0,          '',            10.5,               79.0,            '',           '',                  2),
                    ('611011 Frozen Account',      21.0,          '50.00%',      10.5,               '',              '',           '',                  3),
                    ('611011 Frozen Account',      25.0,          '',              '',               79.0,            '',           '',                  3),
                ('Total',                        3246.0,          '',          1098.5,               79.0,            '',           0.0,                 1),
            ],
            options,
        )

    def test_disallowed_expenses_account_id_and_vehicle_id_confusion_regression_test(self):
        """
        This test aims to reproduce an issue where two invoice lines were aggregated under the same
        hierarchy when they should have been segregated.
        To reproduce:
            - Create one vehicle and one account sharing the same ID.
            - Create two account move lines: both with the account set on it, but only one of them with the vehicle.
            - Create a DNA category with a rate and set it on the aforementioned account.
            - Set a rate on the vehicle.
        The problem to reproduce:
            - The line with the vehicle should appear in the dedicated vehicle section and should not be included
            in the section related to the account without the vehicle.
        """
        # This test is done in 3 phases:
        #   1) Test technical preparation
        #   2) Test business preparation
        #   3) The reporting test

        # 1) Test technical preparation
        # Prepare the sequence to ensure account.id == vehicle.id later on.

        # Check sequence number and advance the smallest one.
        self.env.cr.execute("SELECT currval('fleet_vehicle_id_seq'), currval('account_account_id_seq')")
        fleet_vehicle_max_id, account_account_max_id = self.env.cr.fetchone()
        # In theory, account sequence will always be bigger but the test should be able to run on a db that already
        # lived and that might have much more vehicles than accounts which means the test should be able to set any
        # of those 2 sequences accordingly
        if fleet_vehicle_max_id < account_account_max_id:
            self.env.cr.execute("SELECT setval('fleet_vehicle_id_seq', %s)", [account_account_max_id])
        elif fleet_vehicle_max_id > account_account_max_id:
            self.env.cr.execute("SELECT setval('account_account_id_seq', %s)", [fleet_vehicle_max_id])

        self.env.cr.execute("SELECT currval('fleet_vehicle_id_seq'), currval('account_account_id_seq')")
        fleet_vehicle_max_id, account_account_max_id = self.env.cr.fetchone()
        assert fleet_vehicle_max_id == account_account_max_id, "At this point the current id should be the same"

        # 2) Test business preparation
        expense_account = self.company_data['default_account_expense'].copy({
            'name': 'Super expense',
            'code': '605555',
        })
        dna_category = self.env['account.disallowed.expenses.category'].create({
            'code': 'bob',
            'name': 'DNA category',
            'rate_ids': [
                Command.create({
                    'date_from': fields.Date.from_string('2022-01-01'),
                    'rate': 40.0,
                }),
            ],
        })
        expense_account.disallowed_expenses_category_id = dna_category.id
        vehicle = self.batmobile.copy()
        assert expense_account.id == vehicle.id, "Those new records need to share the same id to reproduce the issue"

        self.env['fleet.disallowed.expenses.rate'].create({
            'rate': 25.0,
            'date_from': '2022-01-01',
            'vehicle_id': vehicle.id,
        })

        # Remove any noise from the report
        self.env['account.move'].search([('state', '=', 'posted')]).button_draft()

        # Fill some data for the report
        bill = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'move_type': 'in_invoice',
            'date': fields.Date.from_string('2022-01-15'),
            'invoice_date': fields.Date.from_string('2022-01-15'),
            'invoice_line_ids': [
                Command.create({
                    'name': 'Test',
                    'quantity': 1,
                    'price_unit': 1000,
                    'account_id': expense_account.id,
                }),
                Command.create({
                    'vehicle_id': vehicle.id,
                    'quantity': 1,
                    'price_unit': 100.0,
                    'account_id': expense_account.id,
                }),
            ],
        })
        bill.action_post()

        # 3) The reporting test
        report, options = self._setup_base_report(unfold=True, split=True)
        lines = report._get_lines(options)
        self._prepare_column_values(lines)
        self.assertLinesValues(
            # pylint: disable=C0326
            lines,
            #   Name                                         Total Amount     Rate            Disallowed Amount     Level
            [   0,                                           1,                2,             3,                    4],
            [
                ('bob DNA category',                         1_100.0,          '',            425.0,                1),

                  ('Wayne Enterprises/Batmobile/No Plate',     100.0,          '25.00%',       25.0,                2),
                    ('605555 Super expense',                   100.0,          '25.00%',       25.0,                3),
                      ('605555 Super expense',                 100.0,          '25.00%',       25.0,                4),

                  ('605555 Super expense',                   1_000.0,          '40.00%',      400.0,                2),
                    ('605555 Super expense',                 1_000.0,          '40.00%',      400.0,                3),

                ('Total',                                    1_100.0,          '',            425.0,                1),
            ],
            options,
        )

    def test_lines_without_vehicle_should_be_regrouped_by_account(self):
        super_expense_account = self.company_data['default_account_expense'].copy({
            'name': 'Super expense',
            'code': '605555',
        })
        bob_expense_account = self.company_data['default_account_expense'].copy({
            'name': 'bob expense',
            'code': '605556',
        })
        dna_category = self.env['account.disallowed.expenses.category'].create({
            'code': 'bob',
            'name': 'DNA category',
            'rate_ids': [
                Command.create({
                    'date_from': fields.Date.from_string('2022-01-01'),
                    'rate': 40.0,
                }),
            ],
        })
        super_expense_account.disallowed_expenses_category_id = dna_category.id
        bob_expense_account.disallowed_expenses_category_id = dna_category.id
        vehicle = self.batmobile.copy()

        self.env['fleet.disallowed.expenses.rate'].create({
            'rate': 25.0,
            'date_from': '2022-01-01',
            'vehicle_id': vehicle.id,
        })

        # Remove any noise from the report
        self.env['account.move'].search([('state', '=', 'posted')]).button_draft()

        bill = self.env['account.move'].create({
            'partner_id': self.partner_a.id,
            'move_type': 'in_invoice',
            'date': fields.Date.from_string('2022-01-15'),
            'invoice_date': fields.Date.from_string('2022-01-15'),
            'invoice_line_ids': [
                Command.create({
                    'name': 'Test',
                    'quantity': 1,
                    'price_unit': 1_000,
                    'account_id': super_expense_account.id,
                }),
                Command.create({
                    'vehicle_id': vehicle.id,
                    'quantity': 1,
                    'price_unit': 100.0,
                    'account_id': super_expense_account.id,
                }),
                Command.create({
                    'name': 'Test',
                    'quantity': 1,
                    'price_unit': 10_000,
                    'account_id': bob_expense_account.id,
                }),
                Command.create({
                    'vehicle_id': vehicle.id,
                    'quantity': 1,
                    'price_unit': 100_000.0,
                    'account_id': bob_expense_account.id,
                }),
            ],
        })
        bill.action_post()

        report, options = self._setup_base_report(unfold=True, split=True)
        lines = report._get_lines(options)
        self._prepare_column_values(lines)
        expected_lines = [
              # pylint: disable=C0326
              ('bob DNA category',                          111_100.0,                '',    29_425.0,           1),

                ('Wayne Enterprises/Batmobile/No Plate',    100_100.0,          '25.00%',    25_025.0,           2),
                  ('605555 Super expense',                      100.0,          '25.00%',        25.0,           3),
                    ('605555 Super expense',                    100.0,          '25.00%',        25.0,           4),
                  ('605556 bob expense',                    100_000.0,          '25.00%',    25_000.0,           3),
                    ('605556 bob expense',                  100_000.0,          '25.00%',    25_000.0,           4),

                ('605555 Super expense',                      1_000.0,          '40.00%',       400.0,           2),
                  ('605555 Super expense',                    1_000.0,          '40.00%',       400.0,           3),
                ('605556 bob expense',                       10_000.0,          '40.00%',     4_000.0,           2),
                  ('605556 bob expense',                     10_000.0,          '40.00%',     4_000.0,           3),

              ('Total',                                     111_100.0,                '',    29_425.0,           1),
          ]
        self.assertLinesValues(
            # pylint: disable=C0326
            lines,
            #   Name                                          Total Amount        Rate         Disallowed Amount   Level
            [   0,                                            1,                  2,           3,                  4],
            expected_lines,
            options,
        )

        # For each report line, ensure that the audited move lines have the same total amount.
        for name, amount, _dummy, _dummy, level in expected_lines[:-1]:  # 'Total' line can't be audited.
            with self.subTest(name=name, amount=amount, level=level):
                line_id = next(line['id'] for line in lines if (line['name'], line['columns'][0]['no_format'], line['level']) == (name, amount, level))
                action = self.env[report.custom_handler_model_id.model].open_journal_items(options, {'line_id': line_id})
                amls = self.env['account.move.line'].search(action['domain'])
                self.assertEqual(sum(amls.mapped('balance')), amount, "The sum of the audited move lines should be equal to the amount of the corresponding report line.")

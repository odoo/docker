from odoo import Command
from odoo.tests import tagged

from .common import TestAccountReportsCommon


@tagged('post_install', '-at_install')
class TestAnalyticReport(TestAccountReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.groups_id += cls.env.ref(
            'analytic.group_analytic_accounting')
        cls.report = cls.env.ref('account_reports.profit_and_loss')
        cls.report.write({'filter_analytic': True})

        cls.analytic_plan_parent = cls.env['account.analytic.plan'].create({
            'name': 'Plan Parent',
        })
        cls.analytic_plan_child = cls.env['account.analytic.plan'].create({
            'name': 'Plan Child',
            'parent_id': cls.analytic_plan_parent.id,
        })

        cls.analytic_account_parent = cls.env['account.analytic.account'].create({
            'name': 'Account 1',
            'plan_id': cls.analytic_plan_parent.id
        })
        cls.analytic_account_parent_2 = cls.env['account.analytic.account'].create({
            'name': 'Account 2',
            'plan_id': cls.analytic_plan_parent.id
        })
        cls.analytic_account_child = cls.env['account.analytic.account'].create({
            'name': 'Account 3',
            'plan_id': cls.analytic_plan_child.id
        })
        cls.analytic_account_parent_3 = cls.env['account.analytic.account'].create({
            'name': 'Account 4',
            'plan_id': cls.analytic_plan_parent.id
        })

    def test_report_group_by_analytic_plan(self):

        out_invoice = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2019-05-01',
            'invoice_date': '2019-05-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 200.0,
                    'analytic_distribution': {
                        self.analytic_account_parent.id: 100,
                    },
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 200.0,
                    'analytic_distribution': {
                        self.analytic_account_child.id: 100,
                    },
                }),
            ]
        }])
        out_invoice.action_post()

        options = self._generate_options(
            self.report,
            '2019-01-01',
            '2019-12-31',
            default_options={
                'analytic_plans_groupby': [self.analytic_plan_parent.id, self.analytic_plan_child.id],
            }
        )

        lines = self.report._get_lines(options)

        self.assertLinesValues(
            # pylint: disable=bad-whitespace
            lines,
            [   0,                                   1,          2],
            [
              ['Revenue',                       400.00,     200.00],
              ['Less Costs of Revenue',           0.00,       0.00],
              ['Gross Profit',                  400.00,     200.00],
              ['Less Operating Expenses',         0.00,       0.00],
              ['Operating Income (or Loss)',    400.00,     200.00],
              ['Plus Other Income',               0.00,       0.00],
              ['Less Other Expenses',             0.00,       0.00],
              ['Net Profit',                    400.00,     200.00],
            ],
            options,
            currency_map={
                1: {'currency': self.env.company.currency_id},
                2: {'currency': self.env.company.currency_id},
            },
        )

    def test_report_analytic_filter(self):

        out_invoice = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2023-02-01',
            'invoice_date': '2023-02-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 1000.0,
                    'analytic_distribution': {
                        self.analytic_account_parent.id: 100,
                    },
                })
            ]
        }])
        out_invoice.action_post()

        options = self._generate_options(
            self.report,
            '2023-01-01',
            '2023-12-31',
            default_options={
                'analytic_accounts': [self.analytic_account_parent.id],
            }
        )

        self.assertLinesValues(
            # pylint: disable=C0326
            # pylint: disable=bad-whitespace
            self.report._get_lines(options),
            [   0,                                 1],
            [
              ['Revenue',                    1000.00],
              ['Less Costs of Revenue',         0.00],
              ['Gross Profit',               1000.00],
              ['Less Operating Expenses',       0.00],
              ['Operating Income (or Loss)', 1000.00],
              ['Plus Other Income',             0.00],
              ['Less Other Expenses',           0.00],
              ['Net Profit',                 1000.00],
            ],
            options,
            currency_map={
                1: {'currency': self.env.company.currency_id},
                2: {'currency': self.env.company.currency_id},
            },
        )

        # Set the unused analytic account in filter, as no move is
        # using this account, the column should be empty
        options['analytic_accounts'] = [self.analytic_account_child.id]

        self.assertLinesValues(
            # pylint: disable=C0326
            # pylint: disable=bad-whitespace
            self.report._get_lines(options),
            [   0,                                 1],
            [
              ['Revenue',                       0.00],
              ['Less Costs of Revenue',         0.00],
              ['Gross Profit',                  0.00],
              ['Less Operating Expenses',       0.00],
              ['Operating Income (or Loss)',    0.00],
              ['Plus Other Income',             0.00],
              ['Less Other Expenses',           0.00],
              ['Net Profit',                    0.00],
            ],
            options,
            currency_map={
                1: {'currency': self.env.company.currency_id},
                2: {'currency': self.env.company.currency_id},
            },
        )

    def test_report_audit_analytic_filter(self):
        out_invoice = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2023-02-01',
            'invoice_date': '2023-02-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 1000.0,
                    'analytic_distribution': {
                        self.analytic_account_parent.id: 100,
                    },
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 500.0,
                    'analytic_distribution': {
                        self.analytic_account_child.id: 100,
                    },
                }),
            ],
        }])
        out_invoice.action_post()

        options = self._generate_options(
            self.report,
            '2023-01-01',
            '2023-12-31',
            default_options={
                'analytic_accounts': [self.analytic_account_parent.id],
            }
        )

        lines = self.report._get_lines(options)

        report_line = self.report.line_ids[0]
        report_line_dict = next(x for x in lines if x['name'] == report_line.name)

        action_dict = self.report.action_audit_cell(
            options,
            self._get_audit_params_from_report_line(options, report_line, report_line_dict),
        )

        audited_lines = self.env['account.move.line'].search(action_dict['domain'])
        self.assertEqual(audited_lines, out_invoice.invoice_line_ids[0], "Only the line with the parent account should be shown")

    def test_report_analytic_groupby_and_filter(self):
        """
        Test that the analytic filter is applied on the groupby columns
        """

        out_invoice = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2023-02-01',
            'invoice_date': '2023-02-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 1000.0,
                    'analytic_distribution': {
                        self.analytic_account_parent.id: 40,
                        self.analytic_account_child.id: 60,
                    },
                })
            ]
        }])
        out_invoice.action_post()

        # Test with only groupby
        options = self._generate_options(
            self.report,
            '2023-01-01',
            '2023-12-31',
            default_options={
                'analytic_accounts_groupby': [self.analytic_account_parent.id, self.analytic_account_child.id],
            }
        )

        self.assertLinesValues(
            # pylint: disable=C0326
            # pylint: disable=bad-whitespace
            self.report._get_lines(options),
            [   0,                                 1,        2,         3],
            [
              ['Revenue',                     400.00,   600.00,   1000.00],
              ['Less Costs of Revenue',         0.00,     0.00,      0.00],
              ['Gross Profit',                400.00,   600.00,   1000.00],
              ['Less Operating Expenses',       0.00,     0.00,      0.00],
              ['Operating Income (or Loss)',  400.00,   600.00,   1000.00],
              ['Plus Other Income',             0.00,     0.00,      0.00],
              ['Less Other Expenses',           0.00,     0.00,      0.00],
              ['Net Profit',                  400.00,   600.00,   1000.00],
            ],
            options,
            currency_map={
                1: {'currency': self.env.company.currency_id},
                2: {'currency': self.env.company.currency_id},
            },
        )

        # Adding analytic filter for the two analytic accounts used on the invoice line
        # The two groupby columns should still be filled
        options['analytic_accounts'] = [self.analytic_account_parent.id, self.analytic_account_child.id]

        self.assertLinesValues(
            # pylint: disable=C0326
            # pylint: disable=bad-whitespace
            self.report._get_lines(options),
            [   0,                                 1,        2,         3],
            [
              ['Revenue',                     400.00,   600.00,   1000.00],
              ['Less Costs of Revenue',         0.00,     0.00,      0.00],
              ['Gross Profit',                400.00,   600.00,   1000.00],
              ['Less Operating Expenses',       0.00,     0.00,      0.00],
              ['Operating Income (or Loss)',  400.00,   600.00,   1000.00],
              ['Plus Other Income',             0.00,     0.00,      0.00],
              ['Less Other Expenses',           0.00,     0.00,      0.00],
              ['Net Profit',                  400.00,   600.00,   1000.00],
            ],
            options,
            currency_map={
                1: {'currency': self.env.company.currency_id},
                2: {'currency': self.env.company.currency_id},
            },
        )
        # Keep only first analytic account on filter, the groupby column
        # for this account should still be filled, unlike the other
        options['analytic_accounts'] = [self.analytic_account_parent.id]

        self.assertLinesValues(
            # pylint: disable=C0326
            # pylint: disable=bad-whitespace
            self.report._get_lines(options),
            [   0,                                 1,        2,         3],
            [
              ['Revenue',                     400.00,     0.00,   1000.00],
              ['Less Costs of Revenue',         0.00,     0.00,      0.00],
              ['Gross Profit',                400.00,     0.00,   1000.00],
              ['Less Operating Expenses',       0.00,     0.00,      0.00],
              ['Operating Income (or Loss)',  400.00,     0.00,   1000.00],
              ['Plus Other Income',             0.00,     0.00,      0.00],
              ['Less Other Expenses',           0.00,     0.00,      0.00],
              ['Net Profit',                  400.00,     0.00,   1000.00],
            ],
            options,
            currency_map={
                1: {'currency': self.env.company.currency_id},
                2: {'currency': self.env.company.currency_id},
            },
        )

        # Keep only first analytic account on filter, the groupby column
        # for this account should still be filled, unlike the other
        options['analytic_accounts'] = [self.analytic_account_child.id]

        self.assertLinesValues(
            # pylint: disable=C0326
            # pylint: disable=bad-whitespace
            self.report._get_lines(options),
            [   0,                                 1,        2,         3],
            [
              ['Revenue',                       0.00,   600.00,   1000.00],
              ['Less Costs of Revenue',         0.00,     0.00,      0.00],
              ['Gross Profit',                  0.00,   600.00,   1000.00],
              ['Less Operating Expenses',       0.00,     0.00,      0.00],
              ['Operating Income (or Loss)',    0.00,   600.00,   1000.00],
              ['Plus Other Income',             0.00,     0.00,      0.00],
              ['Less Other Expenses',           0.00,     0.00,      0.00],
              ['Net Profit',                    0.00,   600.00,   1000.00],
            ],
            options,
            currency_map={
                1: {'currency': self.env.company.currency_id},
                2: {'currency': self.env.company.currency_id},
            },
        )

        # Set an unused analytic account in filter, all the columns
        # should be empty, as no move is using this account
        options['analytic_accounts'] = [self.analytic_account_parent_2.id]

        self.assertLinesValues(
            # pylint: disable=C0326
            # pylint: disable=bad-whitespace
            self.report._get_lines(options),
            [   0,                                 1,      2,      3],
            [
              ['Revenue',                       0.00,   0.00,   0.00],
              ['Less Costs of Revenue',         0.00,   0.00,   0.00],
              ['Gross Profit',                  0.00,   0.00,   0.00],
              ['Less Operating Expenses',       0.00,   0.00,   0.00],
              ['Operating Income (or Loss)',    0.00,   0.00,   0.00],
              ['Plus Other Income',             0.00,   0.00,   0.00],
              ['Less Other Expenses',           0.00,   0.00,   0.00],
              ['Net Profit',                    0.00,   0.00,   0.00],
            ],
            options,
            currency_map={
                1: {'currency': self.env.company.currency_id},
                2: {'currency': self.env.company.currency_id},
            },
        )

    def test_audit_cell_analytic_groupby_and_filter(self):
        """
        Test that the analytic filters are applied on the auditing of the cells
        """
        def _get_action_dict(options, column_index):
            lines = self.report._get_lines(options)
            report_line = self.report.line_ids[0]
            report_line_dict = next(x for x in lines if x['name'] == report_line.name)
            audit_param = self._get_audit_params_from_report_line(options, report_line, report_line_dict, column_group_key=list(options['column_groups'])[column_index])
            return self.report.action_audit_cell(options, audit_param)

        other_plan = self.env['account.analytic.plan'].create({'name': "Other Plan"})
        other_account = self.env['account.analytic.account'].create({'name': "Other Account", 'plan_id': other_plan.id, 'active': True})

        out_invoices = self.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'date': '2023-02-01',
                'invoice_date': '2023-02-01',
                'invoice_line_ids': [
                    Command.create({
                        'product_id': self.product_a.id,
                        'price_unit': 1000.0,
                        'analytic_distribution': {
                            self.analytic_account_parent.id: 40,
                            self.analytic_account_child.id: 60,
                        }
                    }),
                ]
            },
            {
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'date': '2023-02-01',
                'invoice_date': '2023-02-01',
                'invoice_line_ids': [
                    Command.create({
                        'product_id': self.product_a.id,
                        'price_unit': 2000.0,
                        'analytic_distribution': {
                            f'{self.analytic_account_parent.id},{other_account.id}': 100,
                        },
                    }),
                ]
            }
        ])
        out_invoices.action_post()
        out_invoices = out_invoices.with_context(analytic_plan_id=self.analytic_plan_parent.id)
        analytic_lines_parent = out_invoices.invoice_line_ids.analytic_line_ids.filtered(lambda line: line.auto_account_id == self.analytic_account_parent)
        analytic_lines_other = out_invoices.with_context(analytic_plan_id=other_plan.id).invoice_line_ids.analytic_line_ids.filtered(lambda line: line.auto_account_id == other_account)

        # Test with only groupby
        options = self._generate_options(
            self.report,
            '2023-01-01',
            '2023-12-31',
            default_options={
                'analytic_accounts_groupby': [self.analytic_account_parent.id, other_account.id],
            }
        )
        action_dict = _get_action_dict(options, 0)  # First Column => Parent
        self.assertEqual(
            self.env['account.analytic.line'].search(action_dict['domain']),
            analytic_lines_parent,
            "Only the Analytic Line related to the Parent should be shown",
        )
        action_dict = _get_action_dict(options, 1)  # Second Column => Other
        self.assertEqual(
            self.env['account.analytic.line'].search(action_dict['domain']),
            analytic_lines_other,
            "Only the Analytic Line related to the Parent should be shown",
        )

        action_dict = _get_action_dict(options, 2)  # Third Column => AMLs
        self.assertEqual(
            out_invoices.line_ids.filtered_domain(action_dict['domain']),
            out_invoices.invoice_line_ids,
            "Both amls should be shown",
        )

        # Adding analytic filter for the two analytic accounts used on the invoice line
        options['analytic_accounts'] = [self.analytic_account_parent.id, other_account.id]
        action_dict = _get_action_dict(options, 0)  # First Column => Parent
        self.assertEqual(
            self.env['account.analytic.line'].search(action_dict['domain']),
            analytic_lines_parent,
            "Still only the Analytic Line related to the Parent should be shown",
        )
        action_dict = _get_action_dict(options, 1)  # Second Column => Other
        self.assertEqual(
            self.env['account.analytic.line'].search(action_dict['domain']),
            analytic_lines_other,
            "Still only the Analytic Line related to the Parent should be shown",
        )

        action_dict = _get_action_dict(options, 2)  # Third Column => AMLs
        self.assertEqual(
            out_invoices.line_ids.search(action_dict['domain']),
            out_invoices.invoice_line_ids,
            "Both amls should be shown",
        )

    def test_general_ledger_analytic_filter(self):
        analytic_plan = self.env["account.analytic.plan"].create({
            "name": "Default Plan",
        })
        analytic_account = self.env["account.analytic.account"].create({
            "name": "Test Account",
            "plan_id": analytic_plan.id,
        })

        invoice = self.init_invoice(
            "out_invoice",
            amounts=[100, 200],
            invoice_date="2023-01-01",
        )
        invoice.action_post()
        invoice.invoice_line_ids[0].analytic_distribution = {analytic_account.id: 100}

        general_ledger_report = self.env.ref("account_reports.general_ledger_report")
        options = self._generate_options(
            general_ledger_report,
            "2023-01-01",
            "2023-01-01",
            default_options={
                'analytic_accounts': [analytic_account.id],
                'unfold_all': True,
            }
        )

        self.assertLinesValues(
            general_ledger_report._get_lines(options),
            #   Name                                    Debit           Credit          Balance
            [   0,                                      5,              6,              7],
            [
                ['400000 Product Sales',                0.00,           100.00,         -100.00],
                ['INV/2023/00001',                      0.00,           100.00,         -100.00],
                ['Total 400000 Product Sales',          0.00,           100.00,         -100.00],
                ['Total',                               0.00,           100.00,         -100.00],
            ],
            options,
        )

    def test_analytic_groupby_with_horizontal_groupby(self):

        out_invoice_1 = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2024-07-01',
            'invoice_date': '2024-07-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 500.0,
                    'analytic_distribution': {
                        self.analytic_account_parent_2.id: 80,
                        self.analytic_account_parent_3.id: -10,
                    },
                }),
            ]
        }])
        out_invoice_1.action_post()

        out_invoice_2 = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2024-07-01',
            'invoice_date': '2024-07-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'analytic_distribution': {
                        self.analytic_account_parent.id: 100,
                    },
                }),
            ]
        }])
        out_invoice_2.action_post()

        horizontal_group = self.env['account.report.horizontal.group'].create({
            'name': 'Horizontal Group Journal Entries',
            'report_ids': [self.report.id],
            'rule_ids': [
                Command.create({
                    'field_name': 'move_id',  # this field is specific to account.move.line and not in account.analytic.line
                    'domain': f"[('id', 'in', {(out_invoice_1 + out_invoice_2).ids})]",
                }),
            ],
        })

        options = self._generate_options(
            self.report,
            '2024-01-01',
            '2024-12-31',
            default_options={
                'analytic_accounts_groupby': [self.analytic_account_parent.id, self.analytic_account_parent_2.id, self.analytic_account_parent_3.id],
                'selected_horizontal_group_id': horizontal_group.id,
            }
        )

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Horizontal groupby               [             Move 2              ]     [               Move 1                ]
            #   Analytic groupby                    A1          A2      A3      Balance     A1          A2       A3         Balance
            [   0,                                  1,          2,      3,      4,          5,          6,      7,          8],
            [
              ['Revenue',                       100.00,     0.00,   0.00,   100.00,     0.00,    400.00,    -50.00,     500.00],
              ['Less Costs of Revenue',           0.00,     0.00,   0.00,     0.00,     0.00,      0.00,      0.00,       0.00],
              ['Gross Profit',                  100.00,     0.00,   0.00,   100.00,     0.00,    400.00,    -50.00,     500.00],
              ['Less Operating Expenses',         0.00,     0.00,   0.00,     0.00,     0.00,      0.00,      0.00,       0.00],
              ['Operating Income (or Loss)',    100.00,     0.00,   0.00,   100.00,     0.00,    400.00,    -50.00,     500.00],
              ['Plus Other Income',               0.00,     0.00,   0.00,     0.00,     0.00,      0.00,      0.00,       0.00],
              ['Less Other Expenses',             0.00,     0.00,   0.00,     0.00,     0.00,      0.00,      0.00,       0.00],
              ['Net Profit',                    100.00,     0.00,   0.00,   100.00,     0.00,    400.00,    -50.00,     500.00],
            ],
            options,
        )

# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from .common import TestAccountBudgetCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestCommittedAchievedAmount(TestAccountBudgetCommon):

    def create_other_category_aal(self):
        self.env['account.analytic.line'].create({
            'name': 'aal 1',
            'date': '2019-01-10',
            self.project_column_name: self.analytic_account_partner_a.id,
            'amount': 200,
        })
        self.env['account.analytic.line'].create({
            'name': 'aal 2',
            'date': '2019-01-10',
            self.project_column_name: self.analytic_account_partner_b.id,
            'amount': 200,
        })
        self.env['account.analytic.line'].create({
            'name': 'aal 3',
            'date': '2019-01-10',
            self.project_column_name: self.analytic_account_partner_a.id,
            'amount': -100,
        })
        self.env['account.analytic.line'].create({
            'name': 'aal 4',
            'date': '2019-01-10',
            self.project_column_name: self.analytic_account_partner_b.id,
            'amount': -100,
        })

    def test_budget_revenue_committed_achieved_amount(self):
        plan_a_line, plan_b_line, plan_b_admin_line = self.budget_analytic_revenue.budget_line_ids
        self.assertEqual(plan_a_line.achieved_amount, 0)
        self.assertEqual(plan_b_line.achieved_amount, 0)
        self.assertEqual(plan_b_admin_line.achieved_amount, 0)
        bill = self.purchase_order.invoice_ids

        # Post Purchase order's bill also to make sure this doesn't affect the revenue budget
        (bill + self.out_invoice).action_post()

        self.env['purchase.order'].invalidate_model(['currency_rate'])
        self.env['purchase.order.line'].invalidate_model(['qty_received', 'qty_invoiced', 'price_unit'])
        self.env['budget.line'].invalidate_model(['achieved_amount', 'committed_amount'])
        self.create_other_category_aal()

        # 2 analytic lines with analytic_account_partner_a in an income account:
        # {invoice line[0]: 200, invoice line[1]: 400}
        # 1 positive analytic line with analytic_account_partner_a, "other" category and without a fiscal account:
        # {aal 1: 200}
        # Total Achieved = 800
        self.assertEqual(plan_a_line.achieved_amount, 800.0)
        # Committed should be same as budget type is revenue
        self.assertEqual(plan_a_line.committed_amount, 800.0)

        # 2 analytic lines with analytic_account_partner_b in an income account:
        # {invoice line[2]: 700, invoice line[3]: 600}
        # 1 positive analytic line with analytic_account_partner_b, "other" category and without a fiscal account:
        # {aal 2: 200}
        # Total Achieved = 1500
        self.assertEqual(plan_b_line.achieved_amount, 1500.0)
        # Committed should be same as budget type is revenue
        self.assertEqual(plan_b_line.committed_amount, 1500.0)

        # 1 analytic line with accounts analytic_account_partner_b and analytic_account_administratif
        # invoice line[3]: 600
        self.assertEqual(plan_b_admin_line.achieved_amount, 600.0)
        # Committed should be same as budget type is revenue
        self.assertEqual(plan_b_admin_line.committed_amount, 600.0)

    def test_budget_analytic_expense_committed_achieved_amount(self):
        plan_a_line, plan_b_line, plan_b_admin_line = self.budget_analytic_expense.budget_line_ids
        self.assertEqual(plan_a_line.achieved_amount, 0)
        self.assertEqual(plan_b_line.achieved_amount, 0)
        self.assertEqual(plan_b_admin_line.achieved_amount, 0)
        bill = self.purchase_order.invoice_ids
        bill.write({'invoice_date': '2019-01-10'})
        bill.action_post()

        self.env['purchase.order'].invalidate_model(['currency_rate'])
        self.env['purchase.order.line'].invalidate_model(['qty_received', 'qty_invoiced', 'price_unit'])
        self.env['budget.line'].invalidate_model(['achieved_amount', 'committed_amount'])
        self.create_other_category_aal()

        # 2 analytic lines with account analytic_account_partner_a in an expense account:
        # Bill line[0]: -100, line[1]: -300
        # 1 negative analytic line with analytic_account_partner_a, "other" category and without a fiscal account:
        # {aal 3: -100}
        # Total Achieved = 500
        self.assertEqual(plan_a_line.achieved_amount, 500.0)

        # Product A have 2 PO lines with account analytic_account_partner_a in an expense account:
        # - one for line[0] with 10 ordered at price 100
        # - one for line[1] with 10 ordered at price 100
        # Also, there's 1 negative analytic line with analytic_account_partner_a, "other" category and
        # without a fiscal account that is not linked to a PO (aal 3: -100)
        self.assertEqual(plan_a_line.committed_amount, 2100.0)

        # 2 analytic lines with account analytic_account_partner_b in an expense account:
        # Bill line[2]: -600, line[3]: -500
        # 1 negative analytic line with analytic_account_partner_b, "other" category and without a fiscal account:
        # {aal 4: -100}
        # Total Achieved = 1200
        self.assertEqual(plan_b_line.achieved_amount, 1200.0)

        # Product B have 2 PO lines with account analytic_account_partner_b in an expense account:
        # - one for line[2] with 10 ordered at price 100
        # - one for line[3] with 10 ordered at price 100
        # Also, there's 1 negative analytic line with analytic_account_partner_b, "other" category and
        # without a fiscal account that is not linked to a PO (aal 4: -100)
        self.assertEqual(plan_b_line.committed_amount, 2100.0)

        # 1 analytic line with accounts analytic_account_partner_b and analytic_account_administratif
        # in an expense account
        # Bill line[3]: -500,
        self.assertEqual(plan_b_admin_line.achieved_amount, 500.0)

        # Product B have 1 PO line line[3] with 10 ordered at price 100 with analytic_account_partner_b
        # and analytic_account_administratif in an expense account
        self.assertEqual(plan_b_admin_line.committed_amount, 1000.0)

        # A bill should impact the budget even if it is not linked to a PO
        no_po_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-11',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                    'quantity': 3,
                    'price_unit': 100,
                    'account_id': self.company_data['default_account_expense'].id,
                }),
            ]
        })
        no_po_bill.action_post()
        self.env['budget.line'].invalidate_model(['achieved_amount', 'committed_amount'])
        self.assertEqual(plan_a_line.achieved_amount, 800.0)
        self.assertEqual(plan_a_line.committed_amount, 2400.0)

    def test_budget_analytic_expense_committed_amount_draft_bill(self):
        """ Test that the committed amount stays correct while a PO has a bill which is still unposted.
        The amount should not be 0.
        """
        # Draft the test purchase order.
        self.purchase_order.button_draft()
        # Create a new purchase order
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': '2019-01-10',
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'product_qty': 1,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                }),
            ]
        })
        purchase_order.button_confirm()
        purchase_order.order_line.qty_received = 1

        # The confirmed purchase order should impact the analytic line committed amount.
        plan_a_line = self.budget_analytic_expense.budget_line_ids[0]
        # One PO line with an amount of 100 should be committed.
        self.assertBudgetLine(plan_a_line, committed=100, achieved=0)

        # Create the bill for the PO but do not post it. Committed amount should still be 100.
        bill = self.env['account.move'].browse(purchase_order.action_create_invoice()['res_id'])
        bill.invoice_date = '2019-01-10'
        self.assertBudgetLine(plan_a_line, committed=100, achieved=0)

        # Finally we post the bill. Committed amount AND achieved amount should be 100.
        purchase_order.invoice_ids.action_post()
        self.assertBudgetLine(plan_a_line, committed=100, achieved=100)

    def test_budget_analytic_multiple_bills_from_po(self):
        """ Test with multiple bills linked to a PO. """
        # Draft the test purchase order.
        self.purchase_order.button_draft()
        # Create a new purchase order
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': '2019-01-10',
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'product_qty': 10,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                }),
            ]
        })
        purchase_order.button_confirm()
        plan_a_line = self.budget_analytic_expense.budget_line_ids[0]
        self.assertBudgetLine(plan_a_line, committed=1000, achieved=0)

        # Create bill for 5 units
        purchase_order.order_line.qty_received = 5
        bill = self.env['account.move'].browse(purchase_order.action_create_invoice()['res_id'])
        bill.invoice_date = '2019-01-10'
        self.assertBudgetLine(plan_a_line, committed=1000, achieved=0)
        bill.action_post()
        self.assertBudgetLine(plan_a_line, committed=1000, achieved=500)

        # Create another bill for another 2 units
        purchase_order.order_line.qty_received = 7
        bill = self.env['account.move'].browse(purchase_order.action_create_invoice()['res_id'])
        bill.invoice_date = '2019-01-10'
        bill.action_post()
        self.assertBudgetLine(plan_a_line, committed=1000, achieved=700)

    def test_multiple_bills_from_po_multiple_uom(self):
        """ Test with multiple bills linked to a PO and multiple UoM. """
        self.purchase_order.button_draft()
        gravel_ton = self.env['product.product'].create({
            'name': 'Gravel 1T',
            'uom_id': self.env.ref('uom.product_uom_ton').id,
            'uom_po_id': self.env.ref('uom.product_uom_ton').id,
            'standard_price': 1000,
        })
        gravel_kilo = self.env['product.product'].create({
            'name': 'Gravel 1kg',
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
            'uom_po_id': self.env.ref('uom.product_uom_kgm').id,
            'standard_price': 1,
        })
        # Create a new purchase order
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': '2019-01-10',
            'order_line': [
                Command.create({
                    'product_id': gravel_ton.id,
                    'product_qty': 3.5,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                }),
            ]
        })
        purchase_order.button_confirm()
        plan_a_line = self.budget_analytic_expense.budget_line_ids[0]
        self.assertBudgetLine(plan_a_line, committed=3500, achieved=0)

        # Create bill for 2 tons
        purchase_order.order_line.qty_received = 2
        bill = self.env['account.move'].browse(purchase_order.action_create_invoice()['res_id'])
        bill.invoice_date = '2019-01-10'
        bill.action_post()
        self.assertBudgetLine(plan_a_line, committed=3500, achieved=2000)

        # Create another bill for 1500 kg
        purchase_order.order_line.qty_received = 3.5
        bill = self.env['account.move'].browse(purchase_order.action_create_invoice()['res_id'])
        bill.invoice_line_ids.write({
            'product_id': gravel_kilo.id,
            'quantity': 1500,
        })
        bill.invoice_date = '2019-01-10'
        self.assertBudgetLine(plan_a_line, committed=3500, achieved=2000)
        bill.action_post()
        self.assertBudgetLine(plan_a_line, committed=3500, achieved=3500)

    def test_budget_analytic_both_committed_achieved_amount(self):
        plan_a_line, plan_b_line, plan_b_admin_line = self.budget_analytic_both.budget_line_ids
        self.assertEqual(plan_a_line.achieved_amount, 0)
        self.assertEqual(plan_b_line.achieved_amount, 0)
        self.assertEqual(plan_b_admin_line.achieved_amount, 0)
        bill = self.purchase_order.invoice_ids
        bill.write({'invoice_date': '2019-01-10'})

        (bill + self.out_invoice).action_post()

        self.env['purchase.order'].invalidate_model(['currency_rate'])
        self.env['purchase.order.line'].invalidate_model(['qty_received', 'qty_invoiced', 'price_unit'])
        self.env['budget.line'].invalidate_model(['achieved_amount', 'committed_amount'])
        self.create_other_category_aal()

        # 3 Negative and 3 Positive analytic lines positive with account analytic_account_partner_a:
        # Bill line[0]: -100, line[1]: -300, Invoice line[0]: 200, line[1]: 400, aal 1: 200, aal 3: -100
        # Total Achieved = (-100 + (-300) + 200 + 400 + 200 + (-100)) = 300
        self.assertEqual(plan_a_line.achieved_amount, 300)

        # Product A have 2 PO lines, one for line[0] with 10 order and 1 received and one for line[1] with 10 order and 3 received with account analytic_account_partner_a
        # Committed = ((order - received) * price) + achieved = ((10-1) + (10-3)) * 100 + 300 = 1900
        self.assertEqual(plan_a_line.committed_amount, 1900.0)

        # 3 Negative and 3 Positive analytic lines positive with account analytic_account_partner_a:
        # Bill line[2]: -600, line[3]: -500, Out Invoice line[2]: 700, line[3]: 600, aal 2: 200, aal 4: -100
        # Total Achieved = ((-600) + (-500) + 700 + 600 + 200 + (-100)) = 300
        self.assertEqual(plan_b_line.achieved_amount, 300)

        # Product B have 2 PO lines, one for line[2] with 10 order and 6 received and one for line[3] with 10 order and 5 received with account analytic_account_partner_b
        # Committed = ((order - received) * price) + achieved = ((10-6) + (10-5)) * 100 + 300 = 1200
        self.assertEqual(plan_b_line.committed_amount, 1200)

        # 1 Negative and 1 Positive lines with accounts analytic_account_partner_b and analytic_account_administratif
        # Bill line[3]: -500 Out Bill line[3]: 600
        # Total Achieved = ((-500) + 600) = 100
        self.assertEqual(plan_b_admin_line.achieved_amount, 100)

        # Product B have 1 PO line line[3] with 10 order and 5 received with analytic_account_partner_b and analytic_account_administratif
        # Committed = ((order - received) * price) + achieved = ((10-5) * 100 + 100 = 600
        self.assertEqual(plan_b_admin_line.committed_amount, 600)

    def test_budget_analytic_misc_entry(self):
        """ Even if an analytic distribution is set, only the accounts with type 'income'/'expense' should be taken
        into account for the budgets.
        """
        self.purchase_order.button_draft()
        journal_entry = self.env['account.move'].create({
            'move_type': 'entry',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-10',
            'invoice_line_ids': [
                Command.create({
                    'partner_id': self.partner_a.id,
                    'account_id': self.company_data['default_account_expense'].id,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                    'debit': 100,
                }),
                Command.create({
                    'partner_id': self.partner_a.id,
                    'account_id': self.company_data['default_account_assets'].id,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                    'credit': 70,
                }),
                Command.create({
                    'partner_id': self.partner_a.id,
                    'account_id': self.company_data['default_account_assets'].id,
                    'credit': 30,
                }),
            ],
        })
        journal_entry.action_post()

        budget_both_line_a = self.budget_analytic_both.budget_line_ids[0]
        self.assertEqual((budget_both_line_a.committed_amount, budget_both_line_a.achieved_amount), (-100, -100))

        budget_expense_line_a = self.budget_analytic_expense.budget_line_ids[0]
        self.assertEqual((budget_expense_line_a.committed_amount, budget_expense_line_a.achieved_amount), (100, 100))

    def test_budget_analytic_expense_with_credit_note(self):
        """ Test that credit note are taken into account. """
        plan_a_line, plan_b_line, plan_b_admin_line = self.budget_analytic_expense.budget_line_ids
        self.assertBudgetLine(plan_a_line, committed=2000, achieved=0)
        self.assertBudgetLine(plan_b_line, committed=2000, achieved=0)
        self.assertBudgetLine(plan_b_admin_line, committed=1000, achieved=0)
        # Create a bill from PO
        bill = self.purchase_order.invoice_ids
        bill.write({'invoice_date': '2019-01-10'})
        bill.action_post()
        self.assertBudgetLine(plan_a_line, committed=2000, achieved=400)
        self.assertBudgetLine(plan_b_line, committed=2000, achieved=1100)
        self.assertBudgetLine(plan_b_admin_line, committed=1000, achieved=500)
        # Create a credit note
        reversal_wizard = self.env['account.move.reversal'].with_context(active_model='account.move', active_ids=bill.ids).create({
            'journal_id': bill.journal_id.id,
            'date': '2019-01-11'
        })
        reversal = reversal_wizard.reverse_moves()
        self.env['account.move'].browse(reversal['res_id']).action_post()
        self.assertBudgetLine(plan_a_line, committed=2000, achieved=0)
        self.assertBudgetLine(plan_b_line, committed=2000, achieved=0)
        self.assertBudgetLine(plan_b_admin_line, committed=1000, achieved=0)

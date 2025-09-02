# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.exceptions import UserError

from .test_hr_payroll_account import TestHrPayrollAccountCommon


@tagged('post_install', '-at_install')
class TestHrPayrollPayment(TestHrPayrollAccountCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        credit_account = cls.env['account.account'].create({
            'name': 'Salary Payble',
            'code': '2300',
            'reconcile': True,
            'account_type': 'liability_current',
        })
        cls.env['hr.salary.rule'].create({
            'name': 'Net Salary',
            'amount_select': 'code',
            'amount_python_compute': 'result = categories["BASIC"] + categories["ALW"] + categories["DED"]',
            'code': 'NET',
            'category_id': cls.env.ref('hr_payroll.NET').id,
            'sequence': 10,
            'account_credit': credit_account.id,
            'struct_id': cls.hr_structure_softwaredeveloper.id,
        })

        cls.hr_employee_john.bank_account_id = cls.env['res.partner.bank'].create([{
            'acc_number': '0144748555',
            'partner_id': cls.hr_employee_john.work_contact_id.id,
            'allow_out_payment': True,
        }])

        cls.hr_payslip_john.action_refresh_from_work_entries()

    def test_payment_hr_payslip(self):
        """ Checking the process of a payslip when you register payment.  """

        # I validate the payslip.
        self.hr_payslip_john.action_payslip_done()

        # I verify the payslip is in done state.
        self.assertEqual(self.hr_payslip_john.state, 'done', 'State not changed!')

        # I verify that the Accounting Entry is created.
        self.assertTrue(self.hr_payslip_john.move_id, 'Accounting entry has not been created!')

        with self.assertRaisesRegex(UserError, "You can only register payment for posted journal entries."):
            # Should not register payment for a non-posted journal entry
            self.hr_payslip_john.action_register_payment()

        # I register payment for the payslip.
        self.hr_payslip_john.move_id.action_post()
        self.assertEqual(self.hr_payslip_john.move_id.state, 'posted', 'Accounting entry has not been posted!')
        action_register_payment = self.hr_payslip_john.action_register_payment()
        wizard = self.env[action_register_payment['res_model']].with_context(
            action_register_payment['context'], hr_payroll_payment_register=True).create({})
        action_create_payment = wizard.action_create_payments()
        payment = self.env[action_create_payment['res_model']].browse(action_create_payment['res_id'])
        self.assertAlmostEqual(payment.amount, self.hr_payslip_john.move_id.amount_total, 'Payment amount is not correct!')
        self.assertEqual(payment.partner_bank_id, self.hr_employee_john.bank_account_id)

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from .common import L10nPayrollAccountCommon


@tagged("post_install_l10n", "post_install", "-at_install", "aba_file")
class TestPayslipRun(L10nPayrollAccountCommon):

    def _prepare_payslip_run(self):
        payslip_run = self.env["hr.payslip.run"].create(
            {
                "date_start": "2023-01-01",
                "date_end": "2023-01-31",
                "name": "January Batch",
                "company_id": self.company.id,
            }
        )

        payslip_employee = (
            self.env["hr.payslip.employees"]
            .with_company(self.company)
            .create(
                {
                    "employee_ids": [
                        Command.set([self.employee_1.id, self.employee_2.id])
                    ]
                }
            )
        )
        payslip_employee.with_context(active_id=payslip_run.id).compute_sheet()
        payslip_run.action_validate()
        return payslip_run

    def _register_payment(self, payslip_run):
        action = payslip_run.action_register_payment()

        payment_register = (
                    self.env["account.payment.register"]
                    .with_context(
                        **action["context"],
                        hr_payroll_payment_register=True,
                        hr_payroll_payment_register_batch=payslip_run.id,
                    )
                    .create({})
                )

        return payment_register._create_payments()

    def test_batch_payment(self):
        payslip_run = self._prepare_payslip_run()
        self.assertEqual(
            payslip_run.state, "close", "Payslip run should be in close state"
        )
        # Post journal entries
        payslip_run.slip_ids.move_id._post()
        # action = payslip_run.action_register_payment()
        # payment_register = (
        #     self.env["account.payment.register"]
        #     .with_context(
        #         **action["context"],
        #         hr_payroll_payment_register=True,
        #         hr_payroll_payment_register_batch=payslip_run.id,
        #     )
        #     .create({})
        # )
        # payments = payment_register._create_payments()
        payments = self._register_payment(payslip_run)

        self.assertEqual(payslip_run.l10n_au_payment_batch_id.payment_ids, payments)
        self.assertEqual(payslip_run.l10n_au_payment_batch_id.batch_type, "outbound")
        self.assertEqual(payslip_run.l10n_au_payment_batch_id.payment_method_id, self.env.ref("l10n_au_aba.account_payment_method_aba_ct"))

        self.assertTrue(all(payslip.state == 'paid' for payslip in payslip_run.slip_ids), "All payslips must be marked paid!")
        self.assertEqual(payslip_run.state, 'paid', "The payslip batch should be marked as paid!")
        for payment in payments:
            slip = payslip_run.slip_ids.filtered(lambda p: p.employee_id.work_contact_id == payment.partner_id)
            self.assertEqual(payment.amount, slip.line_ids.filtered(lambda x: x.code == 'NET').total)
            self.assertEqual(payment.partner_bank_id, slip.employee_id.bank_account_id, "The Payment should be made to bank account on the Employee!")

        payslip_run.l10n_au_payment_batch_id.validate_batch()
        self.assertEqual(payslip_run.l10n_au_payment_batch_id.state, "sent", "Batch Should be in sent state!")
        self.assertTrue(payslip_run.l10n_au_payment_batch_id.export_file, "Aba File should be generated!")

    def test_payslip_aba(self):
        payslip_run = self._prepare_payslip_run()
        self.assertEqual(
            payslip_run.state, "close", "Payslip run should be in close state"
        )
        action = payslip_run.action_payment_report('aba')
        self.env["hr.payroll.payment.report.wizard"].with_context(
            **action["context"]
        ).create({}).generate_payment_report()
        self.assertTrue(payslip_run.payment_report, "Aba File should be generated!")

        payslip_run.slip_ids.move_id._post()
        self._register_payment(payslip_run)
        payslip_run.l10n_au_payment_batch_id.validate_batch()

        self.assertEqual(
            payslip_run.l10n_au_payment_batch_id.export_file,
            payslip_run.payment_report
        )

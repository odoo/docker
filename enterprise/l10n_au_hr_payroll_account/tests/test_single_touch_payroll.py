# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo import fields, Command
from odoo.tests import tagged
from odoo.exceptions import ValidationError
from .common import L10nPayrollAccountCommon
from odoo.addons.l10n_au_hr_payroll.tests.test_unused_leaves import TestPayrollUnusedLeaves


@tagged("post_install_l10n", "post_install", "-at_install", "l10n_au_hr_payroll")
class TestSingleTouchPayroll(L10nPayrollAccountCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['l10n_au.stp'].search([]).unlink()
        cls.env['ir.sequence'].create({
            'name': 'STP Sequence',
            'code': 'stp.transaction',
            'prefix': 'PAYEVENT0004',
            'padding': 10,
            'number_next': 1,
        })
        cls.company.l10n_au_bms_id = "ODOO_TEST_BMS_ID"
        cls.company.write({
                "vat": "83914571673",
                "email": "au_company@odoo.com",
                "phone": "123456789",
                "zip": "2000",
                'l10n_au_branch_code': '100'
        })
        cls.long_service = cls.env['hr.leave.type'].create({
            'name': 'Long Service Leave',
            'company_id': cls.company.id,
            'l10n_au_leave_type': 'long_service',
            'leave_validation_type': 'no_validation',
            'work_entry_type_id': cls.env.ref('l10n_au_hr_payroll.l10n_au_work_entry_long_service_leave').id,
        })
        cls.annual = cls.env['hr.leave.type'].create({
            'name': 'Annual Leave',
            'company_id': cls.company.id,
            'l10n_au_leave_type': 'annual',
            'leave_validation_type': 'no_validation',
            'work_entry_type_id': cls.env.ref('l10n_au_hr_payroll.l10n_au_work_entry_paid_time_off').id,
        })

    create_leaves = TestPayrollUnusedLeaves.create_leaves

    # ==================== HELPERS ====================

    def _prepare_payslip_run(self):
        payslip_run = self.env["hr.payslip.run"].create(
            {
                "date_start": "2024-01-01",
                "date_end": "2024-01-31",
                "name": "January Batch",
                "company_id": self.company.id,
            }
        )

        payslip_employee = (
            self.env["hr.payslip.employees"]
            .create(
                {
                    "employee_ids": [
                        Command.set([self.employee_1.id, self.employee_2.id])
                    ]
                }
            )
        )
        payslip_employee.with_context(active_id=payslip_run.id).compute_sheet()
        payslip_run.slip_ids.write({"input_line_ids": [(0, 0, {
            'input_type_id': self.env.ref('l10n_au_hr_payroll.input_laundry_1').id,
            'amount': 100,
            }), (0, 0, {
            'input_type_id': self.env.ref('l10n_au_hr_payroll.input_laundry_2').id,
            'amount': 100,
            }), (0, 0, {
            'input_type_id': self.env.ref('l10n_au_hr_payroll.input_gross_director_fee').id,
            'amount': 100,
            }), (0, 0, {
            'input_type_id': self.env.ref('l10n_au_hr_payroll.input_bonus_commissions_overtime_prior').id,
            'amount': 100,
            })
        ]})
        payslip_run.action_validate()
        return payslip_run

    def _submit_stp(self, stp):
        self.assertTrue(stp, "The STP record should have been created when the payslip was created")
        self.assertEqual(stp.state, "draft", "The STP record should be in draft state")

        # TODO: Check the data being generated in the XML file
        action = self.env['l10n_au.stp.submit'].create(
            {'l10n_au_stp_id': stp.id}
        )
        with self.assertRaises(ValidationError):
            action.action_submit()
        action.stp_terms = True
        action.action_submit()

        self.assertTrue(stp.xml_file, "The XML file should have been generated")
        self.assertEqual(stp.state, "sent", "The STP record should be in sent state")

    def test_stp(self):
        self.employee_1.l10n_au_child_support_garnishee_amount = 0.15
        self.employee_1.l10n_au_child_support_deduction = 120
        self.contract_1.l10n_au_salary_sacrifice_superannuation = 100
        batch = self._prepare_payslip_run()

        self.assertTrue(
            all(state == "ready" for state in batch.slip_ids.mapped("l10n_au_stp_status")),
            "All payslips should be ready to be sent to STP"
        )

        stp = self.env["l10n_au.stp"].search([("payslip_batch_id", "=", batch.id)])
        self._submit_stp(stp)

    def create_ytd_opening_balances(self, employee, values: dict):
        """
        Args:
            employee (hr.employee)
            values (list): List with (code, amount) tuples
        """
        vals_to_create = []
        for code, value in values.items():
            vals_to_create.append({
                "employee_id": employee.id,
                "struct_id": self.default_payroll_structure.id,
                "rule_id": self.env["hr.salary.rule"].search([
                    ("struct_id", "=", self.default_payroll_structure.id),
                    ("code", "=", code)
                ]).id,
                "start_value": value,
                "finalised": False,
                "start_date": date(2024, 7, 1),
            })
        self.env["l10n_au.payslip.ytd"].create(vals_to_create)

    def create_payslips(self, employee, num_slips, start_date):
        for i in range(num_slips):
            slip_month = start_date.month + i if (start_date.month + i) <= 12 else 1
            slip = self.env["hr.payslip"].create({
                "employee_id": employee.id,
                "contract_id": employee.contract_id.id,
                "date_from": start_date.replace(month=slip_month),
                "date_to": start_date.replace(day=31, month=slip_month),
                "name": f"January Payslip {i + 1}",
                "struct_id": self.default_payroll_structure.id,
            })
            slip.compute_sheet()
            slip.action_payslip_done()
        return slip

    # ==================== TESTS ====================

    def test_out_of_cycle_termination(self):
        self.contract_1.write({"l10n_au_salary_sacrifice_superannuation": 100})
        self.create_leaves(
            self.employee_1,
            self.contract_1,
            leaves={
                "annual": {
                    "pre_1993": 20,
                    "post_1993": 10.42,
                }
            },
        )
        payslip = self.env["hr.payslip"].create({
                "name": "payslip",
                "employee_id": self.employee_1.id,
                "contract_id": self.contract_1.id,
                "date_from": "2024-05-01",
                "date_to": "2024-05-31",
                "input_line_ids": [(0, 0, {
                    'input_type_id': self.env.ref('l10n_au_hr_payroll.input_golden_handshake').id,
                    'amount': 250,
                })],
                "l10n_au_termination_type": 'normal',
            })

        payslip.compute_sheet()
        payslip.action_payslip_done()
        stp = self.env["l10n_au.stp"].search([("payslip_ids", "in", payslip.id)])
        rendering_data = stp._get_rendering_data()
        termination_tuple = rendering_data[1][0]["Remuneration"][0]["EmploymentTerminationPaymentCollection"]
        self.assertDictEqual(
            termination_tuple[0],
            {
                "IncomePayAsYouGoWithholdingA": 80.0,
                "IncomeTaxPayAsYouGoWithholdingTypeC": "O",
                "IncomeD": fields.Date.from_string("2024-05-31"),
                "IncomeTaxableA": 250.0,
                "IncomeTaxFreeA": 0,
            },
        )
        super_tuple = rendering_data[1][0]["SuperannuationContributionCollection"]
        self.assertListEqual(
            super_tuple,
            [
                {"EntitlementTypeC": "O", "EmployerContributionsYearToDateA": 5000.0},  # OTE
                {"EntitlementTypeC": "L", "EmployerContributionsYearToDateA": 550.0},  # NON RESC
                {"EntitlementTypeC": "R", "EmployerContributionsYearToDateA": 100.0},  # RESC
            ]
        )
        self.assertEqual(rendering_data[1][0]["EmploymentEndD"], fields.Date.from_string("2024-05-31"))
        self._submit_stp(stp)

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Date
from odoo.tests.common import TransactionCase
from dateutil.relativedelta import relativedelta
from datetime import date
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPayslipComputationMX(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref('base.mx')
        cls.roque_emp = cls.env['hr.employee'].create({
            'name': 'Roque',
        })

        cls.contract_roque = cls.env['hr.contract'].create({
            'date_end': Date.today() + relativedelta(years=2),
            'date_start': Date.to_date('2018-01-01'),
            'name': 'Contract for Roque',
            'wage': 4500,
            'employee_id': cls.roque_emp.id,
            'structure_type_id': cls.env.ref("l10n_mx_hr_payroll.structure_type_employee_mx").id,
            'state': 'open',
        })

    def test_weekly_schedule_pay_mx(self):
        self.contract_roque.l10n_mx_schedule_pay = 'weekly'
        self.contract_roque.schedule_pay = 'weekly'
        roque_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of Roque',
            'employee_id': self.roque_emp.id,
            'contract_id': self.contract_roque.id,
            'struct_id': self.env.ref('l10n_mx_hr_payroll.hr_payroll_structure_mx_employee_salary').id,
            'date_from': date(2018, 1, 1),
            'date_to': date(2018, 1, 7)
        })
        roque_payslip.compute_sheet()
        self.assertAlmostEqual(roque_payslip.paid_amount, 4500, places=2, msg="It should be paid the full wage")
        line_ids_dict = {line['code']: line['amount'] for line in roque_payslip.line_ids}
        self.assertAlmostEqual(line_ids_dict['BASIC'], 4500, places=2, msg="It should be paid the full wage")

    def test_monthly_schedule_pay_mx(self):
        self.contract_roque.l10n_mx_schedule_pay = 'monthly'
        self.contract_roque.schedule_pay = 'monthly'
        roque_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of Roque',
            'employee_id': self.roque_emp.id,
            'contract_id': self.contract_roque.id,
            'struct_id': self.env.ref('l10n_mx_hr_payroll.hr_payroll_structure_mx_employee_salary').id,
            'date_from': date(2018, 1, 1),
            'date_to': date(2018, 1, 31)
        })
        roque_payslip.compute_sheet()
        self.assertAlmostEqual(roque_payslip.paid_amount, 4500, places=2, msg="It should be paid the full wage")
        line_ids_dict = {line['code']: line['amount'] for line in roque_payslip.line_ids}
        self.assertAlmostEqual(line_ids_dict['BASIC'], 4500, places=2, msg="It should be paid the full wage")

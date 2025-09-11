# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon
from odoo.tests import tagged


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('ae')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.ae'),
            structure=cls.env.ref('l10n_ae_hr_payroll.uae_employee_payroll_structure'),
            structure_type=cls.env.ref('l10n_ae_hr_payroll.uae_employee_payroll_structure_type'),
            contract_fields={
                'wage': 40000.0,
                'l10n_ae_housing_allowance': 400.0,
                'l10n_ae_transportation_allowance': 220.0,
                'l10n_ae_other_allowances': 100.0,
                'l10n_ae_is_dews_applied': True,
            }
        )

    def test_payslip_1(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 40000.0, 'HOUALLOW': 400.0, 'TRAALLOW': 220.0, 'OTALLOW': 100.0, 'EOSP': 3333.33, 'ALP': 3393.33, 'GROSS': 40720.0, 'SICC': 5090.0, 'SIEC': -2036.0, 'DEWS': -3332.0, 'NET': 35352.0}
        self._validate_payslip(payslip, payslip_results)

    def test_payslip_2(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        self._add_other_inputs(payslip, {
            'l10n_ae_hr_payroll.input_salary_arrears': 1000.0,
            'l10n_ae_hr_payroll.input_other_earnings': 2000.0,
            'l10n_ae_hr_payroll.input_salary_deduction': 500.0,
            'l10n_ae_hr_payroll.input_other_deduction': 200.0,
            'l10n_ae_hr_payroll.l10n_ae_input_overtime_allowance': 300,
            'l10n_ae_hr_payroll.input_bonus_earnings': 400,
            'l10n_ae_hr_payroll.l10n_ae_input_other_allowance': 600,
            'l10n_ae_hr_payroll.input_airfare_allowance_earnings': 700,
        })
        payslip_results = {'BASIC': 40000.0, 'HOUALLOW': 400.0, 'TRAALLOW': 220.0, 'OTALLOW': 100.0, 'SALARY_ARREARS': 1000.0, 'OTHER_EARNINGS': 2000.0, 'SALARY_DEDUCTIONS': -500.0, 'OTHER_DEDUCTIONS': -200.0, 'OVERTIMEALLOWINP': 300.0, 'BONUS': 400.0, 'OTALLOWINP': 600.0, 'AIRFARE_ALLOWANCE': 700.0, 'EOSP': 3333.33, 'ALP': 3393.33, 'GROSS': 45720.0, 'SICC': 5090.0, 'SIEC': -2036.0, 'DEWS': -3332.0, 'NET': 39652.0}
        self._validate_payslip(payslip, payslip_results)

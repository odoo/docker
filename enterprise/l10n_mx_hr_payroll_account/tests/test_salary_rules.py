# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests.common import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon


@tagged('post_install', 'post_install_l10n', '-at_install', 'payslips_validation')
class TestPayslipValidation(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('mx')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_common(
            country=cls.env.ref('base.mx'),
            structure=cls.env.ref('l10n_mx_hr_payroll.hr_payroll_structure_mx_employee_salary'),
            structure_type=cls.env.ref('l10n_mx_hr_payroll.structure_type_employee_mx'),
            contract_fields={
                'wage': 33000.0,
            }
        )

    def test_payslip_1(self):
        payslip = self._generate_payslip(date(2024, 1, 1), date(2024, 1, 31))
        payslip_results = {'BASIC': 33000.0, 'GROSS': 33000.0, 'ISR': -5418.9, 'SUBSIDY': 0.0, 'INTDAYWAGE': 1100.0, 'RISKIMSSEMPLOYER': 0.0, 'DISFIXIMSSEMPLOYER': 634.89, 'DISADDIMSSEMPLOYER': 260.3, 'DISADDIMSSEMPLOYEE': -94.65, 'DISMEDIMSSEMPLOYER': 346.5, 'DISMEDIMSSEMPLOYEE': -123.75, 'DISMONIMSSEMPLOYER': 231.0, 'DISMONIMSSEMPLOYEE': -82.5, 'DISLIFIMSSEMPLOYER': 577.5, 'DISLIFIMSSEMPLOYEE': -206.25, 'RETIRIMSSEMPLOYER': 660.0, 'CEAVIMSSEMPLOYER': 1039.5, 'CEAVIMSSEMPLOYEE': -371.25, 'NURSIMSSEMPLOYER': 330.0, 'INFONAVITIMSSEMPLOYER': 1650.0, 'IMSSEMPLOYEETOTAL': 878.4, 'IMSSEMPLOYERTOTAL': 5729.69, 'NET': 26702.7}
        self._validate_payslip(payslip, payslip_results)

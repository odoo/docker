# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests.common import tagged
from odoo.addons.hr_payroll_account.tests.common import TestPayslipValidationCommon

_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install', 'swissdec')
class TestSwissdecCommon(TestPayslipValidationCommon):

    @classmethod
    @TestPayslipValidationCommon.setup_country('ch')
    def setUpClass(cls):
        super().setUpClass()
        cls.maxDiff = None
        mapped_payslips = cls.env.company._l10n_ch_generate_swissdec_demo_data()
        for indentifier, payslip in mapped_payslips.items():
            assert isinstance(indentifier, str)
            assert isinstance(payslip, cls.env['hr.payslip'].__class__)
            setattr(cls, indentifier, payslip)
        cls.company = cls.company_data['company']
        cls.resource_calendar_40_hours_per_week = cls.env['resource.calendar'].search([('name', '=', 'Test Calendar : 40 Hours/Week'), ('company_id', '=', cls.company.id)])
        cls.avs_1 = cls.env['l10n.ch.social.insurance'].search([('name', '=', 'AVS 2021')], limit=1)
        cls.laa_1 = cls.env['l10n.ch.accident.insurance'].search([('name', '=', "Backwork-Versicherungen")], limit=1)
        cls.laac_1 = cls.env['l10n.ch.additional.accident.insurance'].search([('name', '=', 'Backwork-Versicherungen')], limit=1)
        cls.ijm_1 = cls.env['l10n.ch.sickness.insurance'].search([('name', '=', 'Backwork-Versicherungen')], limit=1)
        cls.caf_lu_1 = cls.env['l10n.ch.compensation.fund'].search([("member_number", '=', '5676.3')], limit=1)

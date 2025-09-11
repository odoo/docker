# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "K.S.A. - Payroll",
    "countries": ["sa"],
    "author": "Odoo PS",
    "category": "Human Resources/Payroll",
    "description": """
Kingdom of Saudi Arabia Payroll and End of Service rules.
===========================================================

    """,
    "license": "OEEL-1",
    "depends": ["hr_payroll", "hr_work_entry_holidays"],
    "data": [
        "security/ir.model.access.csv",
        "data/hr_departure_reason_data.xml",
        "data/hr_payroll_structure_type_data.xml",
        "data/hr_payroll_structure_data.xml",
        "data/hr_salary_rule_saudi_data.xml",
        "data/hr_salary_rule_expat_data.xml",
        "views/hr_contract_view.xml",
        "views/hr_leave_type_views.xml",
        "views/hr_payroll_master_report_views.xml",
        "data/res_bank_data.xml",
        "data/ir_sequence_data.xml",
        "views/hr_employee_views.xml",
        "views/hr_payslip_run_views.xml",
        "views/hr_payslip_views.xml",
        "wizard/hr_payroll_payment_report_wizard.xml",
        "views/res_bank_views.xml",
        "views/res_config_settings_view.xml",
    ],
    "auto_install": ["hr_payroll"],
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Jordan - Payroll',
    'countries': ['jo'],
    'category': 'Human Resources/Payroll',
    'description': """
Jordan Payroll and Tax Rules
============================
    """,
    'depends': ['hr_payroll'],
    'auto_install': ['hr_payroll'],
    'data': [
        'data/hr_rule_parameter_data.xml',
        'data/hr_salary_rule_category_data.xml',
        'data/hr_payroll_structure_type_data.xml',
        'data/hr_payroll_structure_data.xml',
        'data/hr_salary_rule_data.xml',
        'views/hr_contract_view.xml',
    ],
    'license': 'OEEL-1',
}

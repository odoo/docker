# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Time Off in Payslips',
    'version': '1.0',
    'category': 'Human Resources/Payroll',
    'sequence': 95,
    'depends': ['hr_holidays_gantt', 'hr_work_entry_holidays', 'hr_payroll'],
    'data': [
        'security/hr_payroll_holidays_security.xml',
        'views/res_config_settings_views.xml',
        'views/hr_leave_views.xml',
        'views/hr_allocation_views.xml',
        'views/hr_payslip_run_views.xml',
        'views/hr_payslip_views.xml',
        'data/mail_activity_data.xml',
        'data/ir_actions_server_data.xml',
        'data/hr_payroll_dashboard_warning_data.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'hr_payroll_holidays/static/src/**/*',
            ('remove', 'hr_payroll_holidays/static/src/js/hr_work_entries_gantt.*'),
        ],
        'web.assets_backend_lazy': [
            'hr_payroll_holidays/static/src/js/hr_work_entries_gantt.*',
        ],
    },
    'license': 'OEEL-1',
}

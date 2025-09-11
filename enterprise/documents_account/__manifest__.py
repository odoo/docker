# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documents - Accounting',
    'version': '1.0',
    'category': 'Productivity/Documents',
    'summary': 'Invoices from Documents',
    'description': """
Bridge module between the accounting and documents apps. It enables
the creation invoices from the Documents module, and adds a
button on Accounting's reports allowing to save the report into the
Documents app in the desired format(s).
""",
    'website': ' ',
    'depends': ['documents', 'account_reports'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/mail_activity_type_data.xml',
        'data/documents_account_tour.xml',
        'data/ir_actions_server_data.xml',
        'views/account_move_views.xml',
        'views/documents_account_folder_setting_views.xml',
        'views/documents_document_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/account_reports_export_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'documents_account/static/**/*',
            ('remove', 'documents_account/static/src/views/activity/**'),
        ],
        'web.assets_backend_lazy': [
            'documents_account/static/src/views/activity/**',
        ]
    }
}

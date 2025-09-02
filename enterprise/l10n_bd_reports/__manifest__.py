# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Bangladesh - Accounting Reports',
    'website': 'https://www.odoo.com/documentation/18.0/applications/finance/fiscal_localizations.html',
    'version': '1.0.0',
    'description': """
        Accounting reports for Bangladesh
    """,
    'depends': [
        'account_reports',
        'l10n_bd',
    ],
    'data': [
        'data/corporate_tax_report.xml',
        'views/account_report_menu_view.xml',
        'views/res_config_settings_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}

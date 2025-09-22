# -*- coding: utf-8 -*-
{
    'name': 'Helpdesk Custom',
    'version': '1.0',
    'summary': 'Customizations for Helpdesk',
    'category': 'Helpdesk',
    'author': 'Your Name',
    'depends': ['maintenance', 'hr', 'helpdesk','maintenance_custom'],
    'data': [
        # 'data/data.xml',
        # 'security/security.xml',
        # 'security/ir.model.access.csv',
        'views/helpdesk_ticket_view.xml',
    ],
    'installable': True,
    'application': True,
}

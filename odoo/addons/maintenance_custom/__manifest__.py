# -*- coding: utf-8 -*-
{
    'name': 'Maintenance Custom',
    'version': '1.0',
    'summary': 'Customizations for Maintenance Team',
    'category': 'Maintenance',
    'author': 'Your Name',
    'depends': ['maintenance', 'hr'],
    'data': [
        # 'data/data.xml',
        # 'security/security.xml',
        # 'security/ir.model.access.csv',
        'views/maintenance_view.xml',
        'views/maintenance_equipment_view.xml',
    ],
    'installable': True,
    'application': True,
}

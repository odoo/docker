# -*- coding: utf-8 -*-

{
    'name': 'WhatsApp Tests',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 9898,
    'summary': 'WhatsApp Tests',
    'description': """This module contains tests related to various whatsapp
features. Those tests are present in a separate module as it contains models
used only to perform tests independently to functional aspects of real
applications. """,
    'depends': [
        'contacts',
        'mail',
        'portal',
        'phone_validation',
        'whatsapp',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_tests': [
            'test_whatsapp/static/tests/tours/**/*',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}

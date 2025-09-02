# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Point of Sale Restaurant Appointment',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'This module lets you manage online reservations for restaurant tables',
    'website': 'https://www.odoo.com/app/appointments',
    'depends': ['appointment', 'pos_restaurant'],
    'data': [
        'views/calendar_event_views.xml',
        'views/pos_restaurant_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'demo/pos_restaurant_appointment_demo.xml',
    ],
    'license': 'OEEL-1',
    'post_init_hook': '_pos_restaurant_appointment_after_init',
    'assets': {
        'point_of_sale._assets_pos': [
            'web_gantt/static/src/**/*',
            'pos_restaurant_appointment/static/src/**/*',
            'appointment/static/src/views/gantt/**/*',
            'calendar/static/src/views/widgets/**/*',
            'calendar/static/src/views/calendar_form/**/*',
        ],
    'web.assets_tests': [
            'pos_restaurant_appointment/static/tests/tours/**/*',
        ],
    }
}

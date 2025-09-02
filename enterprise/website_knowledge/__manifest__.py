# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Knowledge Website',
    'summary': 'Publish your articles',
    'version': '1.0',
    'depends': ['knowledge', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/knowledge_views.xml',
        'views/knowledge_templates_public.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'website_knowledge/static/src/backend/**/*',
        ],
        'web.assets_frontend': [
            'html_editor/static/src/utils/url.js',
            'html_editor/static/src/fields/html_viewer.*',
            'html_editor/static/src/others/embedded_component_utils.js',
            'html_editor/static/src/others/embedded_components/core/**/*',
            'knowledge/static/src/editor/embedded_components/core/**/*',
            'knowledge/static/src/editor/html_viewer/**/*',
            'knowledge/static/src/editor/html_migrations/**/*',
            'website_knowledge/static/src/frontend/**/*',
        ],
        'web.assets_tests': [
            'website_knowledge/static/tests/tours/**/*',
        ],
    },
}

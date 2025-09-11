# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

import logging

from odoo.tests import tagged, HttpCase, no_retry

_logger = logging.getLogger(__name__)


@no_retry
@tagged('post_install', '-at_install')
class TestIndustryFsmUi(HttpCase):
    def test_ui(self):
        # Disable onboarding tours as they can conflict with our running tours.
        self.env.ref('base.user_admin').tour_enabled = False
        self.env['res.partner'].create([
            {'name': 'Leroy Philippe', 'email': 'leroy.philou@example.com'},
            {'name': 'Brandon Freeman', 'email': 'brandon.freeman55@example.com'},
        ])
        self.start_tour("/odoo", 'industry_fsm_tour', login="admin")
        self.start_tour('/odoo', 'fsm_task_form_tour', login="admin")

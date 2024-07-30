# Copyright 2017 LasLabs Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, _):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["res.partner"]._install_partner_firstname()

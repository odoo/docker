  # -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_appointment_type_id = fields.Many2one(related="pos_config_id.appointment_type_id", readonly=False)

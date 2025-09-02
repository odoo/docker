# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    planning_generation_interval = fields.Integer("Rate Of Shift Generation", required=True, readonly=False, default=6)

    planning_employee_unavailabilities = fields.Selection(
        selection=[
            ('switch', 'Switch shifts with other employees'),
            ('unassign', 'Unassign themselves from shifts'),
        ],
        string="Employee Unavailabilities",
        default='switch',
        required=True,
    )

    planning_self_unassign_days_before = fields.Integer("Days before shift for unassignment", help="Deadline in days for shift unassignment")

    _sql_constraints = [('planning_self_unassign_days_before_positive', 'CHECK(planning_self_unassign_days_before >= 0)', "The amount of days before unassignment must be positive or equal to zero.")]

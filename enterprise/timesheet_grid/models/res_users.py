# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class User(models.Model):
    _inherit = ['res.users']

    timesheet_manager_id = fields.Many2one(related='employee_id.timesheet_manager_id')

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['timesheet_manager_id']

    def get_last_validated_timesheet_date(self):
        if self.env.user.has_group('hr_timesheet.group_timesheet_manager'):
            return False

        if not self.env.user.has_group('hr_timesheet.group_hr_timesheet_user'):
            raise UserError(_('You are not allowed to see timesheets.'))

        return self.sudo().employee_id.last_validated_timesheet_date

    def get_daily_working_hours(self, date_start, date_stop):
        return self.employee_id._count_daily_working_hours(date_start, date_stop)[self.employee_id.id]

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_ae_annual_leave_days_taken = fields.Float(
        string="Annual Leave Days Taken",
        groups="hr.group_hr_user",
        compute="_compute_l10n_ae_annual_leave_days")
    l10n_ae_annual_leave_days_total = fields.Float(
        string="Annual Leave Days Total",
        groups="hr.group_hr_user",
        compute="_compute_l10n_ae_annual_leave_days")

    def _l10n_ae_get_worked_years(self):
        self.ensure_one()
        if self.contract_id.date_start and self.contract_id.date_end:
            start_datetime = datetime.combine(self.contract_id.first_contract_date, datetime.min.time())
            end_datetime = datetime.combine(self.contract_id.date_end, datetime.max.time())
            return self._get_work_days_data_batch(start_datetime, end_datetime)[self.id]["days"] / 365
        return 0

    def _compute_l10n_ae_annual_leave_days(self):
        self._cr.execute("""
            SELECT
                sum(h.number_of_days) AS days,
                sum(CASE WHEN h.type = 'allocation' THEN h.number_of_days ELSE 0 END) AS total_days_allocated,
                h.employee_id
            FROM
                (
                    SELECT holiday_status_id, number_of_days,
                        state, employee_id, 'allocation' as type
                    FROM hr_leave_allocation
                    UNION ALL
                    SELECT holiday_status_id, (number_of_days * -1) as number_of_days,
                        state, employee_id, 'leave' as type
                    FROM hr_leave
                ) h
                join hr_leave_type s ON (s.id=h.holiday_status_id)
            WHERE
                s.active = true AND h.state='validate' AND
                s.requires_allocation='yes' AND
                h.employee_id in %s AND
                s.l10n_ae_is_annual_leave = TRUE
            GROUP BY h.employee_id""", (tuple(self.ids),))

        employees_remaining_annual_leaves = {row['employee_id']: (row['total_days_allocated'], row['days']) for row in self._cr.dictfetchall()}
        for record in self:
            record.l10n_ae_annual_leave_days_taken = 0
            record.l10n_ae_annual_leave_days_total = 0
            if record.id in employees_remaining_annual_leaves:
                total_days_allocated, remaining_days = employees_remaining_annual_leaves[record.id]
                record.l10n_ae_annual_leave_days_total = total_days_allocated
                record.l10n_ae_annual_leave_days_taken = total_days_allocated - remaining_days

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from dateutil.relativedelta import relativedelta
from pytz import timezone, UTC, utc

from odoo import api, fields, models
from odoo.osv import expression
from odoo.tools import float_is_zero

from odoo.addons.resource.models.utils import Intervals, timezone_datetime


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    color = fields.Integer("Color", compute='_compute_color')
    overtime_progress = fields.Float(compute="_compute_overtime_progress")

    def _compute_overtime_progress(self):
        for attendance in self:
            if not float_is_zero(attendance.worked_hours, precision_digits=2):
                attendance.overtime_progress = 100 - ((attendance.overtime_hours / attendance.worked_hours) * 100)
            else:
                attendance.overtime_progress = 100

    def _gantt_progress_bar(self, field, res_ids, start, stop):
        if not self.env.user._is_internal():
            return {}
        if field == 'employee_id':
            start, stop = utc.localize(start), utc.localize(stop)
            return self._gantt_progress_bar_employee_ids(res_ids, start, stop)
        raise NotImplementedError

    def _gantt_compute_max_work_hours_within_interval(self, employee, start, stop):
        """
        Compute the total work hours of the employee based on the intervals selected on the Gantt view.
        The calculation takes into account the working calendar (flexible or not).

        1) if fully flexible (no limit per day), we return the difference in the time interval.
        2) if flexible: `hours_per_day` or `full_time_required_hours` will be used.
           To approximate the work hours in the interval, we multiply the `full_time_required_hours` by the number of weeks.
           date() method is explicitely used to avoid having issue with daylight saving time (DST) when computing the number of days.
        3) if fixed working hours, we compute the work hours based on their expected attendances.
        """
        num_days = (stop.date() - start.date()).days
        if employee.is_fully_flexible:
            return num_days * 24
        if not employee.is_flexible:
            return self.env['resource.calendar']._get_attendance_intervals_days_data(employee._get_expected_attendances(start, stop))['hours']
        if num_days == 1:
            return employee.resource_id.calendar_id.hours_per_day
        # final result is rounded to the hour (e.g. 177.5 hours -> 178 hours)
        return round(employee.resource_id.calendar_id.full_time_required_hours * (num_days / 7))

    def _gantt_progress_bar_employee_ids(self, res_ids, start, stop):
        """
        Resulting display is worked hours / expected worked hours
        """
        values = {}
        worked_hours_group = self._read_group([('employee_id', 'in', res_ids),
                                               ('check_in', '>=', start),
                                               ('check_out', '<=', stop)],
                                              groupby=['employee_id'],
                                              aggregates=['worked_hours:sum'])
        employee_data = {emp.id: worked_hours for emp, worked_hours in worked_hours_group}
        employees = self.env['hr.employee'].browse(res_ids)
        for employee in employees:
            # Retrieve expected attendance for that employee
            values[employee.id] = {
                'value': employee_data.get(employee.id, 0),
                'max_value': self._gantt_compute_max_work_hours_within_interval(employee, start, stop),
                'is_fully_flexible_hours': employee.resource_id._is_fully_flexible(),
            }

        return values

    @api.model
    def get_gantt_data(self, domain, groupby, read_specification, limit=None, offset=0, unavailability_fields=[], progress_bar_fields=None, start_date=None, stop_date=None, scale=None):
        """
        We override get_gantt_data to allow the display of open-ended records,
        We also want to add in the gantt rows, the active emloyees that have a check in in the previous 60 days
        """

        domain = expression.AND([domain, self.env.context.get('active_domain', [])])
        open_ended_gantt_data = super().get_gantt_data(domain, groupby, read_specification, limit=limit, offset=offset, unavailability_fields=unavailability_fields, progress_bar_fields=progress_bar_fields, start_date=start_date, stop_date=stop_date, scale=scale)

        if self.env.context.get('gantt_start_date') and groupby and groupby[0] == 'employee_id':
            user_domain = self.env.context.get('user_domain')
            active_employees_domain = expression.AND([
                user_domain,
                [
                    '&',
                    ('check_out', '<', start_date),
                    ('check_in', '>', fields.Datetime.from_string(start_date) - relativedelta(days=60)),
                    ('employee_id', 'not in', [group['employee_id'][0] for group in open_ended_gantt_data['groups']])
                ]])
            previously_active_employees = super().get_gantt_data(active_employees_domain, groupby, read_specification, limit=None, offset=0, unavailability_fields=unavailability_fields, progress_bar_fields=progress_bar_fields, start_date=start_date, stop_date=stop_date, scale=scale)
            for group in previously_active_employees['groups']:
                del group['__record_ids']  # Records are not needed here
                open_ended_gantt_data['groups'].append(group)
                open_ended_gantt_data['length'] += 1
            if unavailability_fields:
                for field in open_ended_gantt_data['unavailabilities']:
                    open_ended_gantt_data['unavailabilities'][field] |= previously_active_employees['unavailabilities'][field]

        return open_ended_gantt_data

    @api.model
    def _gantt_unavailability(self, field, res_ids, start, stop, scale):
        if field != "employee_id":
            return super()._gantt_unavailability(field, res_ids, start, stop, scale)

        employees_by_calendar = defaultdict(lambda: self.env['hr.employee'])
        employees = self.env['hr.employee'].browse(res_ids)

        # Retrieve for each employee, their period linked to their calendars
        calendar_periods_by_employee = employees._get_calendar_periods(
            timezone_datetime(start),
            timezone_datetime(stop),
        )

        full_interval_UTC = Intervals([(
            start.astimezone(UTC),
            stop.astimezone(UTC),
            self.env['resource.calendar'],
        )])

        # calculate the intervals not covered by employee-specific calendars.
        # store these uncovered intervals for each employee.
        # store by calendar, employees involved with them
        periods_without_calendar_by_employee = defaultdict(list)
        for employee, calendar_periods in calendar_periods_by_employee.items():
            employee_interval_UTC = Intervals([])
            for (start, stop, calendar) in calendar_periods:
                calendar_periods_interval_UTC = Intervals([(
                    start.astimezone(UTC),
                    stop.astimezone(UTC),
                    self.env['resource.calendar'],
                )])
                employee_interval_UTC |= calendar_periods_interval_UTC
                employees_by_calendar[calendar] |= employee
            interval_without_calendar = full_interval_UTC - employee_interval_UTC
            if interval_without_calendar:
                periods_without_calendar_by_employee[employee.id] = interval_without_calendar

        # retrieve, for each calendar, unavailability periods for employees linked to this calendar
        unavailable_intervals_by_calendar = {}
        for calendar, employees in employees_by_calendar.items():
            # In case the calendar is not set (fully flexible calendar), we consider the employee as always available
            if not calendar:
                unavailable_intervals_by_calendar[calendar] = {
                    employee.id: Intervals([])
                    for employee in employees
                }
                continue

            calendar_work_intervals = calendar._work_intervals_batch(
                timezone_datetime(start),
                timezone_datetime(stop),
                resources=employees.resource_id,
                tz=timezone(calendar.tz)
            )
            full_interval = Intervals([(
                start.astimezone(timezone(calendar.tz)),
                stop.astimezone(timezone(calendar.tz)),
                calendar
            )])
            unavailable_intervals_by_calendar[calendar] = {
                employee.id: full_interval - calendar_work_intervals[employee.resource_id.id]
                for employee in employees}

        # calculate employee's unavailability periods based on his calendar's periods
        # (e.g. calendar A on monday and tuesday and calendar b for the rest of the week)
        unavailable_intervals_by_employees = {}
        for employee, calendar_periods in calendar_periods_by_employee.items():
            employee_unavailable_full_interval = Intervals([])
            for (start, stop, calendar) in calendar_periods:
                interval = Intervals([(start, stop, self.env['resource.calendar'])])
                calendar_unavailable_interval_list = unavailable_intervals_by_calendar[calendar][employee.id]
                employee_unavailable_full_interval |= interval & calendar_unavailable_interval_list
            unavailable_intervals_by_employees[employee.id] = employee_unavailable_full_interval

        result = {}
        for employee_id in res_ids:
            # When an employee doesn't have any calendar,
            # he is considered unavailable for the entire interval
            if employee_id not in unavailable_intervals_by_employees:
                result[employee_id] = [{
                    'start': start.astimezone(UTC),
                    'stop': stop.astimezone(UTC),
                }]
                continue
            # When an employee doesn't have a calendar for a part of the entire interval,
            # he will be unavailable for this part
            if employee_id in periods_without_calendar_by_employee:
                unavailable_intervals_by_employees[employee_id] |= periods_without_calendar_by_employee[employee_id]
            result[employee_id] = [{
                'start': interval[0].astimezone(UTC),
                'stop': interval[1].astimezone(UTC),
            } for interval in unavailable_intervals_by_employees[employee_id]]

        return result

    def action_open_details(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.attendance",
            "views": [[self.env.ref('hr_attendance.hr_attendance_view_form').id, "form"]],
            "res_id": self.id
        }


# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licens

import logging
from odoo import http, _
from odoo.http import request
from odoo.tools import format_duration
from odoo.osv import expression

import pytz
from odoo.tools.misc import get_lang

from odoo import tools

_logger = logging.getLogger(__name__)

try:
    import vobject
except ImportError:
    _logger.warning("`vobject` Python module not found, vcard file generation disabled. Consider installing this module if you want to generate vcard files")
    vobject = None

class ShiftController(http.Controller):

    @http.route(['/planning/<string:planning_token>/<string:employee_token>'], type='http', auth="public", website=True)
    def planning(self, planning_token, employee_token, message=False, **kwargs):
        """ Displays an employee's calendar and the current list of open shifts """
        planning_data = self._planning_get(planning_token, employee_token, message)
        if not planning_data:
            return request.not_found()
        return request.render('planning.period_report_template', planning_data)

    def _get_slot_title(self, slot):
        return '%s%s' % (slot.role_id.name or _('Shift'), ' \U0001F4AC' if slot.name else '')

    def _get_slot_vals(self, slot):
        return {
            'title': self._get_slot_title(slot),
            'color': self._format_planning_shifts(slot.role_id.color),
            'alloc_hours': format_duration(slot.allocated_hours),
            'alloc_perc': f'{slot.allocated_percentage:.2f}',
            'slot_id': slot.id,
            'note': slot.name,
            'allow_self_unassign': slot.allow_self_unassign,
            'is_unassign_deadline_passed': slot.is_unassign_deadline_passed,
            'role': slot.role_id.name,
            'request_to_switch': slot.request_to_switch,
            'is_past': slot.is_past,
        }

    def _get_slots_vals(self, slot, employee_token, attendance_intervals):
        # This method provides a hook for customization by allowing the overriding for specific values
        employee_sudo = request.env['hr.employee'].sudo().search([('employee_token', '=', employee_token)], limit=1)
        if not employee_sudo:
            return []

        employee_tz = pytz.timezone(employee_sudo.tz or 'UTC')
        datetime_start = pytz.utc.localize(slot.start_datetime)
        datetime_end = pytz.utc.localize(slot.end_datetime)

        if employee_sudo.is_flexible:
            vals = self._get_slot_vals(slot)
            vals['start'] = str(datetime_start.astimezone(employee_tz).replace(tzinfo=None))
            vals['end'] = str(datetime_end.astimezone(employee_tz).replace(tzinfo=None))
            return [vals]

        res = []
        for start, stop, dummy in attendance_intervals:
            if datetime_start < stop and datetime_end > start:
                vals = self._get_slot_vals(slot)
                vals['start'] = str(max(datetime_start, start).astimezone(employee_tz).replace(tzinfo=None))
                vals['end'] = str(min(datetime_end, stop).astimezone(employee_tz).replace(tzinfo=None))
                res.append(vals)

        return [{**vals, 'alloc_hours': format_duration(slot.allocated_hours / len(res))} for vals in res]

    def _planning_get(self, planning_token, employee_token, message=False):
        employee_sudo = request.env['hr.employee'].sudo().search([('employee_token', '=', employee_token)], limit=1)
        if not employee_sudo:
            return

        planning_sudo = request.env['planning.planning'].sudo().search([('access_token', '=', planning_token)], limit=1)
        if not planning_sudo:
            return

        employee_tz = pytz.timezone(employee_sudo.tz or 'UTC')
        employee_fullcalendar_data = []
        open_slots = []
        unwanted_slots = []

        domain = [
            ('start_datetime', '>=', planning_sudo.start_datetime),
            ('end_datetime', '<=', planning_sudo.end_datetime),
            ('state', '=', 'published'),
        ]
        if planning_sudo.include_unassigned:
            domain = expression.AND([
                domain,
                [
                    '|',
                    ('employee_id', '=', employee_sudo.id),
                    '|',
                        ('resource_id', '=', False),
                        ('request_to_switch', '=', True),
                ],
            ])
        else:
            domain = expression.AND([
                domain,
                [
                    '|',
                        ('employee_id', '=', employee_sudo.id),
                        ('request_to_switch', '=', True),
                ],
            ])
        planning_slots = request.env['planning.slot'].sudo().search(domain, order='start_datetime asc')

        datetime_start = pytz.utc.localize(planning_sudo.start_datetime)
        datetime_end = pytz.utc.localize(planning_sudo.end_datetime)
        resource_work_intervals, dummy = employee_sudo.resource_id._get_valid_work_intervals(
            datetime_start,
            datetime_end,
        )
        attendance_intervals = resource_work_intervals[employee_sudo.resource_id.id]

        # filter and format slots
        slots_start_datetime = []
        slots_end_datetime = []
        # Default values. In case of missing slots (an error message is shown)
        # Avoid errors if the _work_intervals are not defined.
        checkin_min = 8
        checkout_max = 18
        planning_values = {
            'employee_slots_fullcalendar_data': employee_fullcalendar_data,
            'open_slots_ids': open_slots,
            'unwanted_slots_ids': unwanted_slots,
            'planning_planning_id': planning_sudo,
            'employee': employee_sudo,
            'employee_token': employee_token,
            'planning_token': planning_token,
            'no_data': True
        }
        for slot in planning_slots:
            if slot.employee_id:
                slot_start_datetime = pytz.utc.localize(slot.start_datetime).astimezone(employee_tz).replace(tzinfo=None)
                slot_end_datetime = pytz.utc.localize(slot.end_datetime).astimezone(employee_tz).replace(tzinfo=None)
                if slot.request_to_switch and (
                    not slot.role_id
                    or slot.employee_id == employee_sudo
                    or not employee_sudo.planning_role_ids
                    or slot.role_id in employee_sudo.planning_role_ids
                ):
                    unwanted_slots.append(slot)
                if slot.employee_id == employee_sudo:
                    vals = self._get_slots_vals(slot, employee_token, attendance_intervals)
                    employee_fullcalendar_data.extend(vals)
                # We add the slot start and stop into the list after converting it to the timezone of the employee
                slots_start_datetime.append(slot_start_datetime)
                slots_end_datetime.append(slot_end_datetime)
            elif not slot.is_past and (
                not employee_sudo.planning_role_ids
                or not slot.role_id
                or slot.role_id in employee_sudo.planning_role_ids) and (
            # This slot is for employee working flexible hours or the slot is during at least a valid working interval
                employee_sudo.is_flexible or
                any(pytz.utc.localize(slot.start_datetime) < end and pytz.utc.localize(slot.end_datetime) > start for start, end, dummy in attendance_intervals._items)
            ):
                open_slots.append(slot)
        # Calculation of the events to define the default calendar view:
        # If the planning_sudo only spans a week, default view is week, else it is month.
        min_start_datetime = slots_start_datetime and min(slots_start_datetime) \
                             or pytz.utc.localize(planning_sudo.start_datetime).astimezone(employee_tz).replace(tzinfo=None)
        max_end_datetime = slots_end_datetime and max(slots_end_datetime) \
                           or pytz.utc.localize(planning_sudo.end_datetime).astimezone(employee_tz).replace(tzinfo=None)
        if min_start_datetime.isocalendar()[1] == max_end_datetime.isocalendar()[1]:
            # isocalendar returns (year, week number, and weekday)
            default_view = 'timeGridWeek'
        else:
            default_view = 'dayGridMonth'
        # Calculation of the minTime and maxTime values in timeGridDay and timeGridWeek
        # We want to avoid displaying overly large hours range each day or hiding slots outside the
        # normal working hours
        if employee_sudo.resource_calendar_id and attendance_intervals:
            checkin_min = 24
            checkout_max = 0
            for start, end, dummy in attendance_intervals:
                checkin_min = min(checkin_min, start.hour)
                checkout_max = max(checkout_max, end.hour)
        # We calculate the earliest/latest hour of the slots. It is used in the weekview.
        if slots_start_datetime and slots_end_datetime:
            event_hour_min = min(map(lambda s: s.hour, slots_start_datetime)) # idem
            event_hour_max = max(map(lambda s: s.hour, slots_end_datetime)) # idem
            mintime_weekview, maxtime_weekview = self._get_hours_intervals(checkin_min, checkout_max, event_hour_min,
                                                                           event_hour_max)
        else:
            # Fallback when no slot is available. Still needed because open slots display a calendar
            mintime_weekview, maxtime_weekview = checkin_min, checkout_max
        if employee_fullcalendar_data or open_slots or unwanted_slots:
            planning_values.update({
                'employee_slots_fullcalendar_data': employee_fullcalendar_data,
                'open_slots_ids': open_slots,
                'unwanted_slots_ids': unwanted_slots,
                # fullcalendar does not understand complex iso code like fr_BE
                'locale': get_lang(request.env).iso_code.split("_")[0],
                'format_datetime': lambda dt, dt_format: tools.format_datetime(request.env, dt, tz=employee_tz.zone, dt_format=dt_format),
                'notification_text': message in ['assign', 'unassign', 'already_assign', 'deny_unassign', 'switch', 'cancel_switch'],
                'message_slug': message,
                'open_slot_has_role': any(s.role_id.id for s in open_slots),
                'open_slot_has_note': any(s.name for s in open_slots),
                'unwanted_slot_has_role': any(s.role_id.id for s in unwanted_slots),
                'unwanted_slot_has_note': any(s.name for s in unwanted_slots),
                # start_datetime and end_datetime are used in the banner. This ensure that these values are
                # coherent with the sended mail.
                'start_datetime': planning_sudo.start_datetime,
                'end_datetime': planning_sudo.end_datetime,
                'mintime': '%02d:00:00' % mintime_weekview,
                'maxtime': '%02d:00:00' % maxtime_weekview,
                'default_view': default_view,
                'default_start': min_start_datetime.date(),
                'no_data': False
            })
        return planning_values

    @http.route('/planning/<string:token_planning>/<string:token_employee>/assign/<int:slot_id>', type="http", auth="public", website=True)
    def planning_self_assign(self, token_planning, token_employee, slot_id, message=False, **kwargs):
        slot_sudo = request.env['planning.slot'].sudo().browse(slot_id)
        if not slot_sudo.exists():
            return request.not_found()

        employee_sudo = request.env['hr.employee'].sudo().search([('employee_token', '=', token_employee)], limit=1)
        if not employee_sudo:
            return request.not_found()

        planning_sudo = request.env['planning.planning'].sudo().search([('access_token', '=', token_planning)], limit=1)
        if not planning_sudo._is_slot_in_planning(slot_sudo):
            return request.not_found()

        if slot_sudo.resource_id and not slot_sudo.request_to_switch:
            return request.redirect('/planning/%s/%s?message=%s' % (token_planning, token_employee, 'already_assign'))

        slot_sudo.write({'resource_id': employee_sudo.resource_id.id})
        slot_sudo.slot_properties  # necessary addition to stop the re-computation of the slot_properties field during the redirect (leads to access rights error)
        if message:
            return request.redirect('/planning/%s/%s?message=%s' % (token_planning, token_employee, 'assign'))
        else:
            return request.redirect('/planning/%s/%s' % (token_planning, token_employee))

    @http.route('/planning/<string:token_planning>/<string:token_employee>/unassign/<int:shift_id>', type="http", auth="public", website=True)
    def planning_self_unassign(self, token_planning, token_employee, shift_id, message=False, **kwargs):
        slot_sudo = request.env['planning.slot'].sudo().search([('id', '=', shift_id)], limit=1)
        if not slot_sudo or not slot_sudo.allow_self_unassign:
            return request.not_found()

        if slot_sudo.is_unassign_deadline_passed:
            return request.redirect('/planning/%s/%s?message=%s' % (token_planning, token_employee, "deny_unassign"))

        employee_sudo = request.env['hr.employee'].sudo().search([('employee_token', '=', token_employee)], limit=1)
        if not employee_sudo or employee_sudo.id != slot_sudo.employee_id.id:
            return request.not_found()

        planning_sudo = request.env['planning.planning'].sudo().search([('access_token', '=', token_planning)], limit=1)
        if not planning_sudo._is_slot_in_planning(slot_sudo):
            return request.not_found()

        slot_sudo.write({'resource_id': False})
        slot_sudo.slot_properties  # necessary addition to stop the re-computation of the slot_properties field during the redirect (leads to access rights error)
        if message:
            return request.redirect('/planning/%s/%s?message=%s' % (token_planning, token_employee, 'unassign'))
        else:
            return request.redirect('/planning/%s/%s' % (token_planning, token_employee))

    @http.route('/planning/<string:token_planning>/<string:token_employee>/switch/<int:shift_id>', type="http", auth="public", website=True)
    def planning_switch_shift(self, token_planning, token_employee, shift_id, **kwargs):
        slot_sudo = request.env['planning.slot'].sudo().browse(shift_id)
        if not slot_sudo.exists():
            return request.not_found()

        employee_sudo = request.env['hr.employee'].sudo().search([('employee_token', '=', token_employee)], limit=1)
        if not employee_sudo or employee_sudo != slot_sudo.employee_id:
            return request.not_found()

        planning_sudo = request.env['planning.planning'].sudo().search([('access_token', '=', token_planning)], limit=1)
        if not planning_sudo._is_slot_in_planning(slot_sudo):
            return request.not_found()

        slot_sudo.write({'request_to_switch': True})
        return request.redirect(f'/planning/{token_planning}/{token_employee}?message=switch')

    @http.route('/planning/<string:token_planning>/<string:token_employee>/cancel_switch/<int:shift_id>', type="http", auth="public", website=True)
    def planning_cancel_shift_switch(self, token_planning, token_employee, shift_id, **kwargs):
        slot_sudo = request.env['planning.slot'].sudo().browse(shift_id)
        if not slot_sudo.exists():
            return request.not_found()

        employee_sudo = request.env['hr.employee'].sudo().search([('employee_token', '=', token_employee)], limit=1)
        if not employee_sudo or employee_sudo != slot_sudo.employee_id:
            return request.not_found()

        planning_sudo = request.env['planning.planning'].sudo().search([('access_token', '=', token_planning)], limit=1)
        if not planning_sudo._is_slot_in_planning(slot_sudo):
            return request.not_found()

        slot_sudo.write({'request_to_switch': False})
        return request.redirect(f'/planning/{token_planning}/{token_employee}?message=cancel_switch')

    @http.route('/planning/assign/<string:token_employee>/<int:shift_id>', type="http", auth="user", website=True)
    def planning_self_assign_with_user(self, token_employee, shift_id, **kwargs):
        slot_sudo = request.env['planning.slot'].sudo().search([('id', '=', shift_id)], limit=1)
        if not slot_sudo:
            return request.not_found()

        employee = request.env.user.employee_id
        if not employee:
            return request.not_found()

        if not slot_sudo.employee_id:
            slot_sudo.write({'resource_id': employee.resource_id.id})
            slot_sudo.slot_properties  # necessary addition to stop the re-computation of the slot_properties field during the redirect (leads to access rights error)

        return request.redirect('/odoo/action-planning.planning_action_open_shift')

    @http.route('/planning/unassign/<string:token_employee>/<int:shift_id>', type="http", auth="user", website=True)
    def planning_self_unassign_with_user(self, token_employee, shift_id, **kwargs):
        slot_sudo = request.env['planning.slot'].sudo().search([('id', '=', shift_id)], limit=1)
        if not slot_sudo or not slot_sudo.allow_self_unassign:
            return request.not_found()

        if slot_sudo.is_unassign_deadline_passed:
            return request.redirect('/odoo/action-planning.planning_action_open_shift')

        employee = request.env['hr.employee'].sudo().search([('employee_token', '=', token_employee)], limit=1)
        if not employee:
            employee = request.env.user.employee_id
        if not employee or employee != slot_sudo.employee_id:
            return request.not_found()

        slot_sudo.write({'resource_id': False})
        slot_sudo.slot_properties  # necessary addition to stop the re-computation of the slot_properties field during the redirect (leads to access rights error)

        if request.env.user:
            return request.redirect('/odoo/action-planning.planning_action_open_shift')
        return request.env['ir.ui.view']._render_template('planning.slot_unassign')

    @http.route(['/slot/<string:access_token>.ics'], type='http', auth="public", website=True)
    def slot_get_ics_file(self, access_token, **kwargs):
        """
            Route to add the appointment event in a iCal/Outlook calendar
        """
        slot = request.env['planning.slot'].sudo().search([('access_token', '=', access_token)], limit=1)
        if not slot or not vobject:
            return request.not_found()

        calendar = slot._get_ics_file(vobject.iCalendar(), slot.employee_id.tz)
        if not calendar:
            return request.not_found()
        content = calendar.serialize().encode('utf-8')

        shift_name = slot.role_id.name.replace(" ", "_") if slot.role_id else _('New_Shift')
        shift_start_time = slot.start_datetime.astimezone(pytz.timezone(slot._get_tz())).strftime('%m_%d_%H_%M')

        return request.make_response(content, [
            ('Content-Type', 'application/octet-stream'),
            ('Content-Length', len(content)),
            ('Content-Disposition', f'attachment; filename=shift_{shift_name}_{shift_start_time}.ics')
        ])

    @http.route(['/planning/<string:planning_token>/<string:employee_token>.ics'], type='http', auth="public", website=True)
    def planning_get_ics_file(self, planning_token, employee_token, **kwargs):
        """
            Route to add the appointment event in a iCal/Outlook calendar
        """
        employee_sudo = request.env['hr.employee'].sudo().search([('employee_token', '=', employee_token)], limit=1)


        planning_sudo = request.env['planning.planning'].sudo().search([('access_token', '=', planning_token)], limit=1)
        if not (planning_sudo and vobject):
            return request.not_found()

        calendar = planning_sudo._get_ics_file(
            vobject.iCalendar(),
            employee_sudo,
        )
        start_name = planning_sudo.date_start.strftime('%m_%d')
        end_name = planning_sudo.date_end.strftime('%m_%d')
        response = request.make_response(calendar.serialize())
        response.headers.add('Content-Type', 'text/calendar')
        response.headers.add('Content-Disposition', 'attachment', filename=f'planning_{start_name}_to_{end_name}.ics')
        return response

    @staticmethod
    def _format_planning_shifts(color_code):
        """Take a color code from Odoo's Kanban view and returns an hex code compatible with the fullcalendar library"""

        switch_color = {
            0: '#008784',   # No color (doesn't work actually...)
            1: '#EE4B39',   # Red
            2: '#F29648',   # Orange
            3: '#F4C609',   # Yellow
            4: '#55B7EA',   # Light blue
            5: '#71405B',   # Dark purple
            6: '#E86869',   # Salmon pink
            7: '#008784',   # Medium blue
            8: '#267283',   # Dark blue
            9: '#BF1255',   # Fushia
            10: '#2BAF73',  # Green
            11: '#8754B0'   # Purple
        }

        return switch_color[color_code]

    @staticmethod
    def _get_hours_intervals(checkin_min, checkout_max, event_hour_min, event_hour_max):
        """
        This method aims to calculate the hours interval displayed in timeGrid
        By default 0:00 to 23:59:59 is displayed.
        We want to display work intervals but if an event occurs outside them, we adapt and display a margin
        to render a nice grid
        """
        if event_hour_min is not None and checkin_min > event_hour_min:
            # event_hour_min may be equal to 0 (12 am)
            mintime = max(event_hour_min - 2, 0)
        else:
            mintime = checkin_min
        if event_hour_max and checkout_max < event_hour_max:
            maxtime = min(event_hour_max + 2, 24)
        else:
            maxtime = checkout_max

        return mintime, maxtime

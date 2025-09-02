# Part of Odoo. See LICENSE file for full copyright and licensing details
from datetime import datetime

from odoo.tests.common import TransactionCase


class TestCommonPlanning(TransactionCase):
    def get_by_employee(self, employee):
        return self.env['planning.slot'].search([('employee_id', '=', employee.id)])

    @classmethod
    def setUpEmployees(cls):
        cls.env.user.tz = "Europe/Brussels"
        cls.employee_joseph = cls.env['hr.employee'].create({
            'name': 'joseph',
            'work_email': 'joseph@a.be',
            'tz': 'UTC',
            'employee_type': 'freelance',
            'create_date': '2015-01-01 00:00:00',
        })
        cls.resource_joseph = cls.employee_joseph.resource_id
        cls.employee_bert = cls.env['hr.employee'].create({
            'name': 'bert',
            'work_email': 'bert@a.be',
            'tz': 'UTC',
            'employee_type': 'freelance',
            'create_date': '2015-01-01 00:00:00',
        })
        cls.resource_bert = cls.employee_bert.resource_id
        cls.employee_janice = cls.env['hr.employee'].create({
            'name': 'janice',
            'work_email': 'janice@a.be',
            'tz': 'America/New_York',
            'employee_type': 'freelance',
            'create_date': '2015-01-01 00:00:00',
        })
        cls.resource_janice = cls.employee_janice.resource_id

    @classmethod
    def setUpDates(cls):
        cls.random_date = datetime(2020, 11, 27)  # it doesn't really matter but it lands on a Friday
        cls.random_sunday_date = datetime(2024, 3, 10)  # this should be a Sunday and thus a closing day
        cls.random_monday_date = datetime(2024, 3, 11)  # this should be a Monday

    @classmethod
    def setUpCalendars(cls):
        cls.flex_40h_calendar, cls.flex_50h_calendar = cls.env['resource.calendar'].create([
            {
                'name': 'Flexible 40h/week',
                'tz': 'UTC',
                'hours_per_day': 8.0,
                'flexible_hours': True,
            }, {
                'name': 'Flexible 50h/week',
                'tz': 'UTC',
                'hours_per_day': 10.0,
                'flexible_hours': True,
            },
        ])

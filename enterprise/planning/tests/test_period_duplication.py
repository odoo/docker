# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.addons.planning.tests.common import TestCommonPlanning


class TestPeriodDuplication(TestCommonPlanning):

    @classmethod
    def setUpClass(cls):
        super(TestPeriodDuplication, cls).setUpClass()
        cls.setUpEmployees()
        cls.setUpCalendars()
        cls.env['planning.slot'].create({
            'resource_id': cls.resource_bert.id,
            'start_datetime': datetime(2019, 6, 3, 8, 0),  # it was a slot on Sunday...
            'end_datetime': datetime(2019, 6, 3, 17, 0),
        })
        cls.env['planning.slot'].create({
            'resource_id': cls.resource_bert.id,
            'start_datetime': datetime(2019, 6, 4, 8, 0),
            'end_datetime': datetime(2019, 6, 5, 17, 0),
        })
        cls.env['planning.slot'].create({
            'resource_id': cls.resource_bert.id,
            'start_datetime': datetime(2019, 6, 3, 8, 0),
            'end_datetime': datetime(2019, 6, 3, 17, 0),
            'repeat': True,
            'repeat_type': 'until',
            'repeat_until': datetime(2019, 6, 6, 17, 0, 0),
            'repeat_interval': 1,
        })
        cls.env['planning.slot'].create({
            'resource_id': cls.resource_joseph.id,
            'start_datetime': datetime(2020, 10, 19, 6, 0),
            'end_datetime': datetime(2020, 10, 19, 15, 0),
        })

    def test_dont_duplicate_recurring_slots(self):
        """Original week :  6/2/2019 -> 6/8/2019
           Destination week : 6/9/2019 -> 6/15/2019
            slots:
                6/2/2019 08:00 -> 6/2/2019 17:00
                6/4/2019 08:00 -> 6/5/2019 17:00
                6/3/2019 08:00 -> 6/3/2019 17:00 --> this one should be recurrent therefore not duplicated
        """
        employee = self.employee_bert

        self.assertEqual(len(self.get_by_employee(employee)), 3)
        self.assertEqual(sum(self.get_by_employee(employee).mapped('allocated_hours')), 16.0 + 8.0 + 8.0, 'duplicate has only duplicated slots that fit entirely in the period')

        self.env['planning.slot'].action_copy_previous_week('2019-06-09 00:00:00', [['start_datetime', '<=', '2020-04-04 21:59:59'], ['end_datetime', '>=', '2020-03-28 23:00:00']])

        slots = self.get_by_employee(employee)
        self.assertEqual(len(slots), 5, 'duplicate has only duplicated slots that fit entirely in the period')

        duplicated_slots = self.env['planning.slot'].search([
            ('employee_id', '=', employee.id),
            ('start_datetime', '>', datetime(2019, 6, 9, 0, 0)),
            ('end_datetime', '<', datetime(2019, 6, 15, 23, 59)),
        ])
        self.assertEqual(len(duplicated_slots), 2, 'duplicate has only duplicated slots that fit entirely in the period')

        self.assertEqual(sum(self.get_by_employee(employee).mapped('allocated_hours')), 16.0 + 8.0 + 8.0 + 16.0 + 8.0, 'duplicate has only duplicated slots that fit entirely in the period')

    def test_duplication_should_preserve_local_time(self):
        """Original week: 10/19/2020 -> 10/23/2020
           Destination week: 10/26/2020 -> 10/30/2020
           Timezone: Europe/Brussels
            slots:
                10/19/2020 08:00 (CEST) -> 10/19/2020 17:00

           After copy, we need to have a slot on Monday 10/26 with the same time
                10/19/2020 08:00 (CET) -> 10/19/2020 17:00
        """
        employee = self.employee_joseph
        employee.tz = 'Europe/Brussels'
        self.env['planning.slot'].action_copy_previous_week('2020-10-26 00:00:00', [['start_datetime', '<=', '2020-10-25 23:59:59'], ['end_datetime', '>=', '2020-10-18 00:00:00']])

        duplicated_slots = self.env['planning.slot'].search([
            ('employee_id', '=', employee.id),
            ('start_datetime', '>', datetime(2020, 10, 26, 0, 0)),
            ('end_datetime', '<', datetime(2020, 10, 30, 23, 59)),
        ])
        self.assertEqual(1, len(duplicated_slots), 'one slot duplicated')
        self.assertEqual('2020-10-26 07:00:00', str(duplicated_slots[0].start_datetime),
                         'adjust GMT timestamp to account for DST shift')

    def test_duplication_on_non_working_days_for_flexible_hours(self):
        """ When applying copy_previous week, it should copy the shifts of flexible resources when they fall on a non-working day.
            (E.g. a shift on a Sunday for a flexible employee should be copied to the next Sunday with same allocated hours)

            Test Case:
            =========
            1) set an employee with a flexible calendar.
            2) create a shift on a Sunday
            3) apply copy_previous_week and verify that the shift is copied to the next Sunday with the same allocated hours
        """
        # set a employee with a flexible calendar
        employee = self.resource_bert
        employee.calendar_id = self.flex_50h_calendar

        # set a shift on Sunday for 7 hours
        self.env['planning.slot'].create({
            'resource_id': employee.id,
            'start_datetime': datetime(2020, 10, 18, 11, 0),
            'end_datetime': datetime(2020, 10, 18, 18, 0),
        })

        # copy the slot to the next Sunday
        self.env['planning.slot'].action_copy_previous_week('2020-10-19 00:00:00', [['start_datetime', '<=', '2020-10-18 23:59:59'], ['end_datetime', '>=', '2020-10-12 00:00:00']])
        duplicated_slots = self.env['planning.slot'].search([
            ('resource_id', '=', employee.id),
            ('start_datetime', '>', datetime(2020, 10, 19, 0, 0)),
            ('end_datetime', '<', datetime(2022, 10, 25, 23, 59)),
        ])
        self.assertEqual(1, len(duplicated_slots), 'one slot duplicated')
        self.assertEqual(7, duplicated_slots.allocated_hours, 'allocated hours should be the same as the original slot')

    def test_duplication_for_fully_flexible_hours(self):
        """ Test copy_previous_week for fully flexible resources.
            Test Case:
            =========
            1) set an employee with a fully flexible calendar.
            2) create 3 slots on 3 different days with each different allocated hours (Monday 5h, Tuesday 6h, Friday 11h)
            3) apply copy_previous_week and verify that the shift is copied to the next week with the same allocated hours
        """
        # set an employee as a fully flexible resource
        employee = self.resource_bert
        employee.calendar_id = False

        # set 3 slots on 3 different days with different allocated hours
        self.env['planning.slot'].create([
            {
                'resource_id': employee.id,
                'start_datetime': datetime(2020, 10, 12, 8, 0),
                'end_datetime': datetime(2020, 10, 12, 13, 0),
                'state': 'published',
            }, {
                'resource_id': employee.id,
                'start_datetime': datetime(2020, 10, 13, 8, 0),
                'end_datetime': datetime(2020, 10, 13, 14, 0),
                'state': 'published',
            }, {
                'resource_id': employee.id,
                'start_datetime': datetime(2020, 10, 16, 8, 0),
                'end_datetime': datetime(2020, 10, 16, 19, 0),
                'state': 'published',
            }
        ])

        # copy the slot to the next week
        self.env['planning.slot'].action_copy_previous_week('2020-10-19 00:00:00', [['start_datetime', '<=', '2020-10-18 23:59:59'], ['end_datetime', '>=', '2020-10-12 00:00:00']])
        duplicated_slots = self.env['planning.slot'].search([
            ('resource_id', '=', employee.id),
            ('start_datetime', '>', datetime(2020, 10, 19, 0, 0)),
            ('end_datetime', '<', datetime(2022, 10, 25, 23, 59)),
        ])

        # check number of slots and their allocated hours
        self.assertEqual(3, len(duplicated_slots), '3 slots duplicated')
        self.assertEqual(5, duplicated_slots.filtered(lambda slot: slot.start_datetime.weekday() == 0).allocated_hours, 'Monday slot should have 5 allocated hours')
        self.assertEqual(6, duplicated_slots.filtered(lambda slot: slot.start_datetime.weekday() == 1).allocated_hours, 'Tuesday slot should have 6 allocated hours')
        self.assertEqual(11, duplicated_slots.filtered(lambda slot: slot.start_datetime.weekday() == 4).allocated_hours, 'Friday slot should have 11 allocated hours')

    def test_duplication_open_shift(self):
        """ Test copy_previous_week with a open shift

            Test Case:
            =========
            1) create an open shift planned
            2) apply `copy_previous_week` for the next week
            3) make sure the allocated hours for the new shift is the same than the one copied
        """
        slot = self.env['planning.slot'].create({
            'start_datetime': datetime(2020, 10, 12, 8, 0),
            'end_datetime': datetime(2020, 10, 13, 12, 0),
            'state': 'published',
        })
        # copy the slot to the next week
        self.env['planning.slot'].action_copy_previous_week('2020-10-19 00:00:00', [['start_datetime', '<=', '2020-10-18 23:59:59'], ['end_datetime', '>=', '2020-10-12 00:00:00']])
        duplicated_slots = self.env['planning.slot'].search([
            ('resource_id', '=', False),
            ('start_datetime', '>', datetime(2020, 10, 19, 0, 0)),
            ('end_datetime', '<', datetime(2022, 10, 25, 23, 59)),
        ])
        self.assertEqual(1, len(duplicated_slots), "One slot should have been copied to this week")
        self.assertEqual(slot.allocated_hours, duplicated_slots.allocated_hours, "The allocated hours between the original slot and the copied one should be equal")

    def test_duplication_on_non_working_days_for_fully_flexible_hours(self):
        """ When applying copy_previous week, it should copy the shifts of flexible resources when they fall on a non-working day.
            (E.g. a shift from Saturday toSunday for a fully flexible employee should be copied to the next week with same allocated hours)

            Test Case:
            =========
            1) set an employee with a fully flexible calendar.
            2) create a shift from Saturday to Sunday
            3) apply copy_previous_week and verify that the shift is copied to the next week with the same allocated hours
        """
        # set an employee as a fully flexible resource
        employee = self.resource_bert
        employee.calendar_id = False

        # set a shift on Saturday Evening 9PM to Sunday morning 8AM (11 hours)
        self.env['planning.slot'].create({
            'resource_id': employee.id,
            'start_datetime': datetime(2020, 10, 17, 21, 0),
            'end_datetime': datetime(2020, 10, 18, 8, 0),
            'state': 'published',
        })

        # copy the slot to the next week
        self.env['planning.slot'].action_copy_previous_week('2020-10-19 00:00:00', [['start_datetime', '<=', '2020-10-18 23:59:59'], ['end_datetime', '>=', '2020-10-12 00:00:00']])
        duplicated_slots = self.env['planning.slot'].search([
            ('resource_id', '=', employee.id),
            ('start_datetime', '>', datetime(2020, 10, 19, 0, 0)),
            ('end_datetime', '<', datetime(2022, 10, 25, 23, 59)),
        ])
        self.assertEqual(1, len(duplicated_slots), 'one slot duplicated')
        self.assertEqual(11, duplicated_slots.allocated_hours, 'allocated hours should be the same as the original slot')

    def test_duplication_on_non_working_days_for_regular_employee(self):
        """ When applying copy_previous week, slots of regular 9-5 employees
        which land on non-working days should not be copied to the next week.

        Test Case:
        =========
        1) set an employee with a regular calendar.
        2) create a shift on a Sunday
        3) apply copy_previous_week and verify that the shift is not copied to the next Sunday
        """

        employee = self.employee_bert

        # set a shift on Sunday for 8 hours
        self.env['planning.slot'].create({
            'employee_id': employee.id,
            'start_datetime': datetime(2020, 10, 18, 8, 0),
            'end_datetime': datetime(2020, 10, 18, 16, 0),
        })

        # copy the slot to the next Sunday
        self.env['planning.slot'].action_copy_previous_week('2020-10-19 00:00:00', [['start_datetime', '<=', '2020-10-18 23:59:59'], ['end_datetime', '>=', '2020-10-12 00:00:00']])

        duplicated_slots = self.env['planning.slot'].search([
            ('employee_id', '=', employee.id),
            ('start_datetime', '>', datetime(2020, 10, 19, 0, 0)),
            ('end_datetime', '<', datetime(2022, 10, 25, 23, 59)),
        ])
        self.assertEqual(0, len(duplicated_slots), 'no slot should be duplicated on a non-working days')

    def test_duplication_should_take_filters_into_account(self):
        PlanningSlot = self.env['planning.slot']
        dt = datetime(2020, 10, 26, 0, 0)
        copied, to_copy = PlanningSlot.with_context(tz='Europe/Brussels').action_copy_previous_week(
            str(dt), [
                ['start_datetime', '<=', dt],
                ['end_datetime', '>=', dt - relativedelta(weeks=1)],
                ['resource_id', '=', self.resource_joseph.id],
            ]
        )
        self.assertEqual(PlanningSlot.browse(copied + to_copy).resource_id, self.resource_joseph,
                         "Filter should be taken into account when copying previous week")

    def test_duplication_should_only_copy_once_except_if_undone(self):
        PlanningSlot = self.env['planning.slot']
        dt = datetime(2020, 10, 26, 0, 0)
        domain = [
            ['start_datetime', '<=', dt + relativedelta(weeks=1)],
            ['end_datetime', '>=', dt],
            ['resource_id', '=', self.resource_joseph.id],
        ]

        def copy_slot():
            return PlanningSlot.with_context(tz='Europe/Brussels').action_copy_previous_week(
                str(dt), [
                    ['start_datetime', '<=', dt],
                    ['end_datetime', '>=', dt - relativedelta(weeks=1)],
                    ['resource_id', '=', self.resource_joseph.id],
                ]
            )

        copied, to_copy = copy_slot()
        self.assertTrue(copied, "The slot should be copied")
        self.assertTrue(PlanningSlot.search(domain), "The slot should be copied")

        self.assertFalse(copy_slot(), "The slot shouldn't be copied, as it already exists")

        PlanningSlot.browse(copied).action_rollback_copy_previous_week(to_copy)
        self.assertFalse(PlanningSlot.search(domain), "The slot should be deleted")
        self.assertTrue(copy_slot(), "The slot should be copied again, as it was deleted")

    def test_duplication_should_create_open_shift_when_outside_schedule(self):
        PlanningSlot = self.env['planning.slot']
        dt = datetime(2023, 7, 24, 0, 0)
        PlanningSlot.create({
            'resource_id': self.resource_joseph.id,
            'start_datetime': dt + relativedelta(hour=19),
            'end_datetime': dt + relativedelta(hour=20),
        })
        copied, _dummy = PlanningSlot.with_context(tz='Europe/Brussels').action_copy_previous_week(
            str(dt + relativedelta(weeks=1)), [
                ['start_datetime', '<=', dt + relativedelta(weeks=1)],
                ['end_datetime', '>=', dt],
                ['resource_id', '=', self.resource_joseph.id],
            ]
        )
        self.assertFalse(PlanningSlot.browse(copied).resource_id, "The slot should be copied as open, as it's outside the schedule")

    def test_duplication_should_create_assigned_shift_when_flexible_resource(self):
        PlanningSlot = self.env['planning.slot']
        dt = datetime(2023, 7, 24, 0, 0)
        flexible_resource = self.env['resource.resource'].create({
            'name': 'Flexible Resource',
            'calendar_id': False,
        })
        PlanningSlot.create({
            'resource_id': flexible_resource.id,
            'start_datetime': dt + relativedelta(hour=19),
            'end_datetime': dt + relativedelta(hour=20),
        })
        copied, _dummy = PlanningSlot.with_context(tz='Europe/Brussels').action_copy_previous_week(
            str(dt + relativedelta(weeks=1)), [
                ['start_datetime', '<=', dt + relativedelta(weeks=1)],
                ['end_datetime', '>=', dt],
                ['resource_id', '=', flexible_resource.id],
            ]
        )
        self.assertEqual(PlanningSlot.browse(copied).resource_id, flexible_resource, "The slot should be copied as assigned, as its resource is flexible")

    def test_duplication_should_create_open_shift_when_conflicting_destination(self):
        PlanningSlot = self.env['planning.slot']
        dt = datetime(2023, 7, 24, 0, 0)
        PlanningSlot.create([{
            'resource_id': self.resource_joseph.id,
            'start_datetime': dt + relativedelta(hours=9, weeks=i),
            'end_datetime': dt + relativedelta(hours=15, weeks=i),
        } for i in range(2)])
        copied, _dummy = PlanningSlot.with_context(tz='Europe/Brussels').action_copy_previous_week(
            str(dt + relativedelta(weeks=1)), [
                ['start_datetime', '<=', dt + relativedelta(weeks=1)],
                ['end_datetime', '>=', dt],
                ['resource_id', '=', self.resource_joseph.id],
            ]
        )
        self.assertFalse(PlanningSlot.browse(copied).resource_id, "The slot should be copied as open, as another shift already exists at this time")

    def test_duplication_should_create_open_shift_when_conflicting_origin(self):
        PlanningSlot = self.env['planning.slot']
        dt = datetime(2023, 7, 24, 0, 0)
        PlanningSlot.create([{
            'resource_id': self.resource_joseph.id,
            'start_datetime': dt + relativedelta(hours=9),
            'end_datetime': dt + relativedelta(hours=15),
        } for _dummy in range(2)])
        copied, _dummy = PlanningSlot.with_context(tz='Europe/Brussels').action_copy_previous_week(
            str(dt + relativedelta(weeks=1)), [
                ['start_datetime', '<=', dt + relativedelta(weeks=1)],
                ['end_datetime', '>=', dt],
                ['resource_id', '=', self.resource_joseph.id],
            ]
        )
        resource_ids = [s.resource_id.id for s in PlanningSlot.browse(copied)]
        self.assertEqual(len(resource_ids), 2, "Both shifts should be copied")
        self.assertIn(self.resource_joseph.id, resource_ids, "One of the shifts should be assigned")
        self.assertIn(False, resource_ids, "One of the shifts should open")

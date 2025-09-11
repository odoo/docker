# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale_planning.tests.test_sale_planning import TestSalePlanning


@tagged('post_install', '-at_install')
class TestRentalPlanning(TestSalePlanning):

    def test_planning_rental_sol_confirmation(self):
        plannable_employees = (
            plannable_employee1,
            plannable_employee2,
        ) = self.env['hr.employee'].create([
          {'name': 'employee 1'},
          {'name': 'employee 2'},
        ])
        self.env['resource.calendar.leaves'].create([{
            'name': 'leave',
            'date_from': datetime(2023, 10, 20, 8, 0),
            'date_to': datetime(2023, 10, 20, 17, 0),
            'resource_id': plannable_employee1.resource_id.id,
            'calendar_id': plannable_employee1.resource_calendar_id.id,
            'time_type': 'leave',
        }, {
            'name': 'Public Holiday',
            'date_from': datetime(2023, 10, 25, 0, 0, 0),
            'date_to': datetime(2023, 10, 25, 23, 59, 59),
            'calendar_id': plannable_employee1.resource_calendar_id.id,
        }])
        self.planning_role_junior.resource_ids = plannable_employees.resource_id
        self.plannable_product.rent_ok = True

        basic_so, resource_time_off_so, public_holiday_so = self.env['sale.order'].with_context(
            in_rental_app=True,
        ).create([{
            'partner_id': self.planning_partner.id,
            'rental_start_date': datetime(2023, 9, 25, 8, 0),
            'rental_return_date': datetime(2023, 9, 28, 8, 0),
            'order_line': [
                Command.create({
                    'product_id': self.plannable_product.id,
                    'product_uom_qty': 10,
                }),
            ],
        }, {
            'partner_id': self.planning_partner.id,
            'rental_start_date': datetime(2023, 10, 20, 8, 0),
            'rental_return_date': datetime(2023, 10, 20, 10, 0),
            'order_line': [
                Command.create({
                    'product_id': self.plannable_product.id,
                    'product_uom_qty': 10,
                }),
            ],
        }, {
            'partner_id': self.planning_partner.id,
            'rental_start_date': datetime(2023, 10, 25, 8, 0),
            'rental_return_date': datetime(2023, 10, 25, 15, 0),
            'order_line': [
                Command.create({
                    'product_id': self.plannable_product.id,
                    'product_uom_qty': 10,
                }),
            ],
        }])

        basic_so.action_confirm()
        slot = basic_so.order_line.planning_slot_ids

        self.assertTrue(slot.resource_id, 'Slot resource_id should not be False')
        self.assertEqual(slot.start_datetime, datetime(2023, 9, 25, 8, 0), 'Slot start datetime should be same as on SO')
        self.assertEqual(slot.end_datetime, datetime(2023, 9, 28, 8, 0), 'Slot end datetime should be same as on SO')

        resource_time_off_so.action_confirm()
        slot_2 = resource_time_off_so.order_line.planning_slot_ids

        self.assertEqual(slot_2.resource_id, plannable_employee2.resource_id, 'Second resource should be assign as first resource is on Time Off')

        plannable_employee1.resource_id.calendar_id = False
        public_holiday_so.action_confirm()
        slot_3 = public_holiday_so.order_line.planning_slot_ids

        self.assertEqual(slot_3.resource_id, plannable_employee1.resource_id, 'First resource should be assign on public holiday as first resource is working flexible hours')

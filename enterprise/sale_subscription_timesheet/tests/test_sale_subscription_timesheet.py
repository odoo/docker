# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged, freeze_time

from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo.addons.sale_timesheet.tests.common import TestCommonSaleTimesheet


@tagged('-at_install', 'post_install')
class TestSubscriptionTask(TestSubscriptionCommon, TestCommonSaleTimesheet):
    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.product_deliver_timesheet = self.env['product.product'].create({
            'name': "Service Ordered, create task in global project",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': self.uom_hour.id,
            'uom_po_id': self.uom_hour.id,
            'default_code': 'SERV-ORDERED2',
            'service_type': 'timesheet',
            'recurring_invoice': True,
            'service_tracking': 'task_global_project',
            'project_id': self.project_global.id,
            'taxes_id': False,
            'property_account_income_id': self.account_sale.id,
        })
        self.subscription_timesheet = self.env['sale.order'].create({
            'name': 'TestSubscriptionWithTimeSheet',
            'is_subscription': True,
            'plan_id': self.plan_month.id,
            'note': "original subscription description",
            'partner_id': self.user_portal.partner_id.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
             'order_line': [
                    Command.create({
                        'product_id': self.product_deliver_timesheet.id,
                        'product_uom_qty': 1
                    }),
                ],
        })

    def test_sub_timesheet_create_recurring_tasks(self):
        # Similar test with recurring tasks: new tasks are created automatically
        # Note: when the setting is deactivated it works similarly. All timesheets must be created into a single task.
        self.env['res.config.settings'].create({
            'group_project_recurring_tasks': True,
        }).execute()

        self.env.user.groups_id += self.env.ref('project.group_project_recurring_tasks')
        with freeze_time("2024-10-01"):
            self.subscription_timesheet.action_confirm()
            inv = self.subscription_timesheet._create_recurring_invoice()
            self.assertFalse(inv, "No invoice should be created")
            task = self.subscription_timesheet.tasks_ids
            self.assertTrue(task, "A new task should be created")
        with freeze_time("2024-10-01"):
            # record timesheet for that task
            self.env['account.analytic.line'].create({
            'name': 'Test Line',
            'project_id': task.project_id.id,
            'task_id': task.id,
            'unit_amount': 10,
            'employee_id': self.employee_user.id,
             })
            self.subscription_timesheet.order_line.with_context(arj=True)._compute_qty_delivered()
            self.assertEqual(self.subscription_timesheet.order_line.qty_delivered, 10, "The product should be delivered")
            # When the task is done, we create a new one
            task.state = '1_done'
            self.subscription_timesheet.invalidate_recordset(['tasks_ids'])
            task = self.subscription_timesheet.tasks_ids - task
            self.assertTrue(task)
        with freeze_time("2024-11-01"):
            inv = self.subscription_timesheet._create_recurring_invoice()
            self.assertEqual(inv.amount_untaxed, 900, "The amount depends on the timesheet (90 per hour)")
        with freeze_time("2024-11-15"):
            self.env['account.analytic.line'].create({
                'name': 'Test Line',
                'project_id': task.project_id.id,
                'task_id': task.id,
                'unit_amount': 50,
                'employee_id': self.employee_user.id,
             })
            self.assertEqual(self.subscription_timesheet.order_line.qty_delivered, 50, "The product should be delivered")
        with freeze_time("2024-12-01"):
            inv = self.subscription_timesheet._create_recurring_invoice()
            # When the task is done, we create a new one
            task.state = '1_done'
            self.subscription_timesheet.invalidate_recordset(['tasks_ids'])
            task = self.subscription_timesheet.tasks_ids - task
            self.assertTrue(task)
            self.assertEqual(inv.amount_untaxed, 4500, "The amount depends on the timesheet (90 per hour)")
            self.assertEqual(len(task), 2, "Two tasks are created automatically")

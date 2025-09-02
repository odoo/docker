# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestAccountBudgetCommon
from odoo import Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPurchaseOrder(TestAccountBudgetCommon):

    def test_access_purchase_order(self):
        """ Make sure a purchase manager can access a purchase order linked to a budget. """

        self.budget_analytic_expense.action_budget_confirm()
        purchase_partner = self.env['res.partner'].create({'name': 'Purchaser'})
        purchase_user = self.env['res.users'].create({
            'login': 'Purchaser',
            'partner_id': purchase_partner.id,
            'groups_id': [Command.set(self.env.ref('purchase.group_purchase_manager').ids)],
        })

        self.assertTrue(
            self.purchase_order.with_user(purchase_user).order_line.budget_line_ids,
            " Purchase Order should be linked to a Budget and Purchaser should have access to it. "
        )

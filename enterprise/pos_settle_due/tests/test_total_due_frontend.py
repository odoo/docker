# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(TestPointOfSaleHttpCommon):

    def test_settle_account_due_update_instantly(self):
        self.partner_test_a = self.env["res.partner"].create({"name": "A Partner"})
        self.customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'split_transactions': True,
        })

        self.main_pos_config.write({'payment_method_ids': [(6, 0, self.customer_account_payment_method.ids)]})
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'pos_settle_account_due_update_instantly', login="accountman")

    def test_settle_due_account_button(self):
        """ Test that an invoice can be created after the session is closed """
        self.customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'split_transactions': True,
        })
        self.partner_test_a = self.env["res.partner"].create({"name": "A Partner"})
        self.partner_test_b = self.env["res.partner"].create({"name": "B Partner"})

        self.main_pos_config.write({'payment_method_ids': [(6, 0, self.customer_account_payment_method.ids)]})

        self.main_pos_config.open_ui()
        current_session = self.main_pos_config.current_session_id

        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner_test_b.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product_a.id,
                'price_unit': 1000,
                'discount': 0,
                'qty': 1,
                'tax_ids': [[6, False, []]],
                'price_subtotal': 1000,
                'price_subtotal_incl': 1000,
            })],
            'pricelist_id': self.main_pos_config.pricelist_id.id,
            'amount_paid': 1000.0,
            'amount_total': 1000.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
        })

        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': 1000.0,
            'payment_method_id': self.customer_account_payment_method.id
        })
        order_payment.with_context(**payment_context).check()
        current_session.close_session_from_ui()
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'SettleDueButtonPresent', login="accountman")

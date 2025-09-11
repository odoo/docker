# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, tagged
from .common import TestInterCompanyRulesCommonStock


@tagged('post_install', '-at_install')
class TestInterCompanyOthersWithStock(TestInterCompanyRulesCommonStock):

    def test_return_purchase_on_inter_company(self):
        """
        Check that returning the reciept of an inter-company transit
        updates the received quantity correctly.
        """
        super_product = self.env['product.product'].create({
            'name': 'Super Product',
            'is_storable': True,
            'company_id': False,
        })
        purchase_order = Form(self.env['purchase.order'].with_company(self.company_a))
        purchase_order.partner_id = self.company_b.partner_id
        purchase_order.company_id = self.company_a
        purchase_order = purchase_order.save()

        with Form(purchase_order.with_company(self.company_b)) as po:
            with po.order_line.new() as line:
                line.product_id = super_product
                line.product_qty = 10.0

        # Confirm Purchase order
        purchase_order.with_company(self.company_a).button_confirm()
        receipt = purchase_order.picking_ids
        self.assertRecordValues(receipt.move_ids, [{
            'product_id': super_product.id,
            'product_uom_qty': 10.0,
        }])
        # validate the receipt
        receipt.move_ids.quantity = 10.0
        receipt.move_ids.picked = True
        receipt.with_company(self.company_a).button_validate()
        self.assertEqual(receipt.state, 'done')
        self.assertEqual(purchase_order.order_line.qty_received, 10.0)
        # return the units to the inter company transit location
        self.env.user.groups_id |= self.env.ref('stock.group_stock_multi_locations')
        stock_return_picking_form = Form(self.env['stock.return.picking'].with_company(self.company_a).with_context(active_ids=receipt.ids, active_id=receipt.sorted().ids[0], active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        return_wiz.product_return_moves.write({'quantity': 10.0})
        res = return_wiz.action_create_returns()
        pick_return = self.env['stock.picking'].browse(res['res_id'])
        self.assertEqual(pick_return.location_dest_id, self.env.ref('stock.stock_location_inter_company'))
        pick_return.move_ids.quantity = 10.0
        pick_return.move_ids.picked = True
        pick_return.with_company(self.company_a).button_validate()
        self.assertEqual(pick_return.state, 'done')
        self.assertEqual(purchase_order.order_line.qty_received, 0.0)

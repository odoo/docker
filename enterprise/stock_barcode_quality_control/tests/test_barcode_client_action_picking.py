# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged
from odoo.addons.stock_barcode.tests.test_barcode_client_action import TestBarcodeClientAction


@tagged('post_install', '-at_install')
class TestBarcodeClientActionPicking(TestBarcodeClientAction):
    def test_partial_quantity_check_fail(self):
        """
        This test verifies that a partial quantity check is correctly handled.
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [Command.link(grp_multi_loc.id)]})
        self.env['quality.point'].create({
            'product_ids': [Command.link(self.product1.id)],
            'picking_type_ids': [Command.link(self.picking_type_in.id)],
            'measure_on': 'move_line',
            'failure_location_ids': [Command.link(self.shelf1.id)],
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id,
        })
        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'move_ids': [Command.create({
                'name': 'test',
                'product_id': self.product1.id,
                'product_uom_qty': 10,
                'product_uom': self.uom_unit.id,
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
            })],
        })
        receipt.action_confirm()
        url = self._get_client_action_url(receipt.id)
        self.start_tour(url, 'test_partial_quantity_check_fail', login='admin')
        self.assertEqual(receipt.move_ids[0].picked, True)
        self.assertEqual(receipt.move_ids[1].picked, True)
        self.assertEqual(receipt.check_ids[0].quality_state, 'fail')
        self.assertEqual(receipt.check_ids[1].quality_state, 'pass')
        self.assertEqual(receipt.check_ids[0].move_line_id.quantity, 3)
        self.assertEqual(receipt.check_ids[1].move_line_id.quantity, 7)

# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestShopFloor(HttpCase):

    def test_shop_floor_spreadsheet(self):
        self.env.ref('base.group_user').implied_ids += (
            self.env.ref('mrp.group_mrp_routings')
        )
        snow_leopard = self.env['product.product'].create({
            'name': 'Snow leopard',
            'is_storable': True,
        })
        mountains = self.env['mrp.workcenter'].create({
            'name': 'Mountains',
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 80,
        })
        leg = self.env['product.product'].create({
            'name': 'Leg',
            'is_storable': True,
        })
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        stock_location = warehouse.lot_stock_id
        self.env['stock.quant']._update_available_quantity(leg, stock_location, quantity=100)
        bom = self.env['mrp.bom'].create({
            'product_id': snow_leopard.id,
            'product_tmpl_id': snow_leopard.product_tmpl_id.id,
            'product_uom_id': snow_leopard.uom_id.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'operation_ids': [
                (0, 0, {
                'name': 'op1',
                'workcenter_id': mountains.id,
            })],
            'bom_line_ids': [
                (0, 0, {'product_id': leg.id, 'product_qty': 4}),
            ]
        })
        picking_type = warehouse.manu_type_id
        spreadsheet = self.env['quality.spreadsheet.template'].create({
            'check_cell': 'A1',
            'name': 'my spreadsheet quality check template',
        })
        self.env['quality.point'].create([
            {
                'picking_type_ids': [(4, picking_type.id)],
                'product_ids': [(4, snow_leopard.id)],
                'operation_id': bom.operation_ids[0].id,
                'title': 'My spreadsheet check',
                'test_type_id': self.env.ref('quality_control.test_type_spreadsheet').id,
                'sequence': 0,
                'spreadsheet_template_id': spreadsheet.id,
            },
        ])
        mo = self.env['mrp.production'].create({
            'product_id': snow_leopard.id,
            'product_qty': 1,
            'bom_id': bom.id,
        })
        mo.action_confirm()
        action = self.env['ir.actions.actions']._for_xml_id('mrp_workorder.action_mrp_display')
        url = f"/odoo/action-{action['id']}"
        self.start_tour(url, 'test_shop_floor_spreadsheet', login='admin')
        self.assertRecordValues(mo.workorder_ids[0].check_ids, [
            {'quality_state': 'fail'},
        ])

# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests import Form
from odoo.tests.common import HttpCase, tagged

@tagged('post_install', '-at_install')
class TestShopFloor(HttpCase):

    def setUp(self):
        super().setUp()
        # Set Administrator as the current user.
        self.uid = self.env.ref('base.user_admin').id
        # Enables Work Order setting, and disables other settings.
        group_workorder = self.env.ref('mrp.group_mrp_routings')
        self.env.user.write({'groups_id': [(4, group_workorder.id, 0)]})

        group_lot = self.env.ref('stock.group_production_lot')
        group_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        group_pack = self.env.ref('stock.group_tracking_lot')
        group_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'groups_id': [(3, group_lot.id)]})
        self.env.user.write({'groups_id': [(3, group_multi_loc.id)]})
        self.env.user.write({'groups_id': [(3, group_pack.id)]})
        # Explicitly remove the UoM group.
        group_user = self.env.ref('base.group_user')
        group_user.write({'implied_ids': [(3, group_uom.id)]})
        self.env.user.write({'groups_id': [(3, group_uom.id)]})

        # Add some properties for commonly used in tests records.
        self.warehouse = self.env['stock.warehouse'].search([], limit=1)
        self.stock_location = self.warehouse.lot_stock_id

    def test_shop_floor(self):
        # Creates somme employees for test purpose.
        employees = self.env['hr.employee'].create([{
            'name': name,
            'company_id': self.env.company.id,
        } for name in ['Abbie Seedy', 'Billy Demo', 'Cory Corrinson']])
        employees[0].barcode = "659898105101"

        giraffe = self.env['product.product'].create({
            'name': 'Giraffe',
            'is_storable': True,
            'tracking': 'lot',
        })
        leg = self.env['product.product'].create({
            'name': 'Leg',
            'is_storable': True,
        })
        neck = self.env['product.product'].create({
            'name': 'Neck',
            'is_storable': True,
            'tracking': 'serial',
        })
        color = self.env['product.product'].create({
            'name': 'Color',
            'is_storable': True,
        })
        neck_sn_1, neck_sn_2 = self.env['stock.lot'].create([{
            'name': 'NE1',
            'product_id': neck.id,
        }, {
            'name': 'NE2',
            'product_id': neck.id,
        }])
        self.env['stock.quant']._update_available_quantity(leg, self.stock_location, quantity=100)
        self.env['stock.quant']._update_available_quantity(color, self.stock_location, quantity=100)
        self.env['stock.quant']._update_available_quantity(neck, self.stock_location, quantity=1, lot_id=neck_sn_1)
        self.env['stock.quant']._update_available_quantity(neck, self.stock_location, quantity=1, lot_id=neck_sn_2)
        savannah = self.env['mrp.workcenter'].create({
            'name': 'Savannah',
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 80,
        })
        jungle = self.env['mrp.workcenter'].create({'name': 'Jungle'})
        picking_type = self.warehouse.manu_type_id
        bom = self.env['mrp.bom'].create({
            'product_id': giraffe.id,
            'product_tmpl_id': giraffe.product_tmpl_id.id,
            'product_uom_id': giraffe.uom_id.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'operation_ids': [
                (0, 0, {
                'name': 'Creation',
                'workcenter_id': savannah.id,
            }), (0, 0, {
                'name': 'Release',
                'workcenter_id': jungle.id,
            })],
            'bom_line_ids': [
                (0, 0, {'product_id': leg.id, 'product_qty': 4}),
                (0, 0, {'product_id': neck.id, 'product_qty': 1, 'manual_consumption': True})
            ]
        })
        steps_common_values = {
            'picking_type_ids': [(4, picking_type.id)],
            'product_ids': [(4, giraffe.id)],
            'operation_id': bom.operation_ids[0].id,
        }
        self.env['quality.point'].create([
            {
                **steps_common_values,
                'title': 'Register Production',
                'test_type_id': self.env.ref('mrp_workorder.test_type_register_production').id,
                'sequence': 0,
            },
            {
                **steps_common_values,
                'title': 'Instructions',
                'test_type_id': self.env.ref('quality.test_type_instructions').id,
                'sequence': 1,
            },
            {
                **steps_common_values,
                'title': 'Register legs',
                'component_id': leg.id,
                'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
                'sequence': 2,
            },
            {
                **steps_common_values,
                'title': 'Register necks',
                'component_id': neck.id,
                'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
                'sequence': 3,
            },
            {
                **steps_common_values,
                'title': 'Release',
                'test_type_id': self.env.ref('quality.test_type_instructions').id,
                'sequence': 4,
            },
        ])
        mo = self.env['mrp.production'].create({
            'product_id': giraffe.id,
            'product_qty': 2,
            'bom_id': bom.id,
        })
        mo.action_confirm()
        mo.action_assign()
        mo.button_plan()

        # Tour
        action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.action_mrp_display")
        url = f"/odoo/action-{action['id']}"
        self.start_tour(url, "test_shop_floor", login='admin')

        self.assertEqual(mo.move_finished_ids.quantity, 2)
        self.assertRecordValues(mo.move_raw_ids, [
            {'product_id': leg.id, 'quantity': 10.0, 'state': 'done'},
            {'product_id': neck.id, 'quantity': 2.0, 'state': 'done'},
            {'product_id': color.id, 'quantity': 1.0, 'state': 'done'},
        ])
        self.assertRecordValues(mo.workorder_ids, [
            {'state': 'done', 'workcenter_id': savannah.id},
            {'state': 'done', 'workcenter_id': jungle.id},
        ])
        self.assertRecordValues(mo.workorder_ids[0].check_ids, [
            {'quality_state': 'pass', 'component_id': False, 'qty_done': 2, 'lot_id': mo.move_finished_ids.move_line_ids.lot_id.id},
            {'quality_state': 'pass', 'component_id': False, 'qty_done': 0, 'lot_id': 0},
            {'quality_state': 'pass', 'component_id': leg.id, 'qty_done': 8, 'lot_id': 0},
            {'quality_state': 'pass', 'component_id': leg.id, 'qty_done': 2, 'lot_id': 0},
            {'quality_state': 'pass', 'component_id': neck.id, 'qty_done': 1, 'lot_id': neck_sn_2.id},
            {'quality_state': 'pass', 'component_id': neck.id, 'qty_done': 1, 'lot_id': neck_sn_1.id},
            {'quality_state': 'pass', 'component_id': False, 'qty_done': 0, 'lot_id': 0},
        ])

    def test_shop_floor_auto_select_workcenter(self):
        """ This test ensures the right work center is selected when Shop Floor is opened."""
        # Create some products.
        product_final = self.env['product.product'].create({
            'name': 'Pizza',
            'is_storable': True,
        })
        product_comp1 = self.env['product.product'].create({
            'name': 'Pizza dough',
            'is_storable': True,
        })
        product_comp2 = self.env['product.product'].create({
            'name': 'Tomato sauce',
            'is_storable': True,
        })
        # Adds some quantity in stock.
        self.env['stock.quant']._update_available_quantity(product_comp1, self.stock_location, quantity=999)
        self.env['stock.quant']._update_available_quantity(product_comp2, self.stock_location, quantity=999)
        # Create three workcenters.
        wc1, wc2 = self.env['mrp.workcenter'].create([{
            'name': f'Preparation Table {i}',
            'default_capacity': 1,
        } for i in range(1, 3)])
        wc1.alternative_workcenter_ids = wc2
        wc2.alternative_workcenter_ids = wc1
        wc3 = self.env['mrp.workcenter'].create({'name': 'Furnace'})
        # Create a BoM.
        bom = self.env['mrp.bom'].create({
            'product_id': product_final.id,
            'product_tmpl_id': product_final.product_tmpl_id.id,
            'product_uom_id': product_final.uom_id.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'operation_ids': [
                Command.create({
                'name': 'Prepare the pizza 🤌',
                'workcenter_id': wc1.id,
            }), Command.create({
                'name': 'Bake it!',
                'workcenter_id': wc3.id,
            })],
            'bom_line_ids': [
                Command.create({'product_id': product_comp1.id, 'product_qty': 1, 'manual_consumption': True}),
                Command.create({'product_id': product_comp2.id, 'product_qty': 1, 'manual_consumption': True})
            ]
        })
        # Create two Manufacturing Orders.
        all_mo = self.env['mrp.production'].create([{
            'product_id': product_final.id,
            'product_qty': qty,
            'bom_id': bom.id,
        } for qty in [6, 4]])
        all_mo.action_confirm()
        all_mo.action_assign()
        all_mo.button_plan()
        # Mark as done the 2th MO 1st WO.
        all_mo[1].workorder_ids[0].button_start()
        all_mo[1].workorder_ids[0].button_done()
        self.start_tour("/odoo/shop-floor", "test_shop_floor_auto_select_workcenter", login='admin')

    def test_generate_serials_in_shopfloor(self):
        component1 = self.env['product.product'].create({
            'name': 'comp1',
            'is_storable': True,
        })
        component2 = self.env['product.product'].create({
            'name': 'comp2',
            'is_storable': True,
        })
        finished = self.env['product.product'].create({
            'name': 'finish',
            'is_storable': True,
        })
        byproduct = self.env['product.product'].create({
            'name': 'byprod',
            'is_storable': True,
            'tracking': 'serial',
        })
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        stock_location = warehouse.lot_stock_id
        self.env['stock.quant']._update_available_quantity(component1, stock_location, quantity=100)
        self.env['stock.quant']._update_available_quantity(component2, stock_location, quantity=100)
        workcenter = self.env['mrp.workcenter'].create({
            'name': 'Assembly Line',
        })
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': finished.product_tmpl_id.id,
            'product_qty': 1.0,
            'operation_ids': [
                (0, 0, {'name': 'Assemble', 'workcenter_id': workcenter.id}),
            ],
            'bom_line_ids': [
                (0, 0, {'product_id': component1.id, 'product_qty': 1}),
                (0, 0, {'product_id': component2.id, 'product_qty': 1}),
            ],
            'byproduct_ids': [
                (0, 0, {'product_id': byproduct.id, 'product_qty': 1}),
            ]
        })
        bom.byproduct_ids[0].operation_id = bom.operation_ids[0].id
        mo = self.env['mrp.production'].create({
            'product_id': finished.id,
            'product_qty': 1,
            'bom_id': bom.id,
        })
        mo.action_confirm()
        mo.action_assign()
        mo.button_plan()

        action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.action_mrp_display")
        url = f"/odoo/action-{action['id']}"
        self.start_tour(url, "test_generate_serials_in_shopfloor", login='admin')

    def test_canceled_wo(self):
        finished = self.env['product.product'].create({
            'name': 'finish',
            'is_storable': True,
        })
        workcenter = self.env['mrp.workcenter'].create({
            'name': 'Assembly Line',
        })
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': finished.product_tmpl_id.id,
            'product_qty': 1.0,
            'operation_ids': [
                (0, 0, {'name': 'op1', 'workcenter_id': workcenter.id}),
                (0, 0, {'name': 'op2', 'workcenter_id': workcenter.id}),
            ],
        })

        # Cancel previous MOs and create a new one
        self.env['mrp.production'].search([]).action_cancel()
        mo = self.env['mrp.production'].create({
            'product_id': finished.id,
            'product_qty': 2,
            'bom_id': bom.id,
        })
        mo.action_confirm()
        mo.action_assign()
        mo.button_plan()

        # wo_1 completely finished
        mo_form = Form(mo)
        mo_form.qty_producing = 2
        mo = mo_form.save()
        mo.workorder_ids[0].button_start()
        mo.workorder_ids[0].button_finish()

        # wo_2 partially finished
        mo_form.qty_producing = 1
        mo = mo_form.save()
        mo.workorder_ids[1].button_start()
        mo.workorder_ids[1].button_finish()

        # Create a backorder
        action = mo.button_mark_done()
        backorder = Form(self.env['mrp.production.backorder'].with_context(**action['context']))
        backorder.save().action_backorder()
        mo_backorder = mo.procurement_group_id.mrp_production_ids[-1]
        mo_backorder.button_plan()

        # Sanity check
        self.assertEqual(mo_backorder.workorder_ids[0].state, 'cancel')
        self.assertEqual(mo_backorder.workorder_ids[1].state, 'ready')

        action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.action_mrp_display")
        url = f"/odoo/action-{action['id']}"
        self.start_tour(url, "test_canceled_wo", login='admin')

    def test_quality_checks_updated_in_shop_floor(self):
        component1 = self.env['product.product'].create({
            'name': 'comp1',
            'is_storable': True,
            'tracking': 'lot',
        })
        finished = self.env['product.product'].create({
            'name': 'finish',
            'is_storable': True,
            'tracking': 'serial',
        })
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        stock_location = warehouse.lot_stock_id
        lot = self.env['stock.lot'].create([{'name': 'LOT', 'product_id': component1.id}])
        self.env['stock.quant']._update_available_quantity(component1, stock_location, quantity=100, lot_id=lot)
        workcenter = self.env['mrp.workcenter'].create({
            'name': 'Assembly Line',
        })
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': finished.product_tmpl_id.id,
            'product_qty': 1.0,
            'operation_ids': [
                (0, 0, {'name': 'Assemble', 'workcenter_id': workcenter.id}),
            ],
            'bom_line_ids': [
                (0, 0, {'product_id': component1.id, 'product_qty': 1}),
            ],
        })
        self.env['quality.point'].create([
            {
                'picking_type_ids': [(4, warehouse.manu_type_id.id)],
                'product_ids': [(4, finished.id)],
                'operation_id': bom.operation_ids[0].id,
                'title': 'Register Production',
                'test_type_id': self.env.ref('mrp_workorder.test_type_register_production').id,
                'sequence': 0,
            },
            {
                'picking_type_ids': [(4, warehouse.manu_type_id.id)],
                'product_ids': [(4, finished.id)],
                'operation_id': bom.operation_ids[0].id,
                'title': 'Register comp1',
                'component_id': component1.id,
                'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
                'sequence': 1,
            },
        ])
        mo = self.env['mrp.production'].create({
            'product_id': finished.id,
            'product_qty': 3,
            'bom_id': bom.id,
        })
        mo.action_confirm()
        mo.action_assign()
        mo.button_plan()

        action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.action_mrp_display")
        url = '/web?#action=%s' % (action['id'])
        self.start_tour(url, "test_updated_quality_checks", login='admin')

    def test_change_qty_produced(self):
        """
            Check that component quantity matches the quantity produced set in the shop
            floor register production change to the quantity produced
            Example:
                move.uom_unit = 2.
                bom.final_quantity = 1
                MO.qty_producing = 5 -> should consume 10 components for move_raw.
                Confirm MO and update MO.qty_producing = 3
                Finish the workorder, then it should consume 6 components for move_raw.
            The above behaviour should be occur on the MO form and shop floor.
        """
        demo = self.env['product.product'].create({
            'name': 'DEMO'
        })
        comp1 = self.env['product.product'].create({
            'name': 'COMP1',
            'is_storable': True
        })
        comp2 = self.env['product.product'].create({
            'name': 'COMP2',
            'is_storable': True
        })
        work_center = self.env['mrp.workcenter'].create({"name": "WorkCenter", "time_start": 11})
        uom_unit = self.env.ref('uom.product_uom_unit')
        bom = self.env['mrp.bom'].create({
            'product_id': demo.id,
            'product_tmpl_id': demo.product_tmpl_id.id,
            'product_uom_id': uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'operation_ids': [
                Command.create({'name': 'OP1', 'workcenter_id': work_center.id, 'time_cycle': 12, 'sequence': 1}),
                Command.create({'name': 'OP2', 'workcenter_id': work_center.id, 'time_cycle': 18, 'sequence': 2})
            ]
        })
        self.env['mrp.bom.line'].create([
            {
                'product_id': comp.id,
                'product_qty': qty,
                'bom_id': bom.id,
                'operation_id': operation.id,
            } for comp, qty, operation in zip([comp1, comp2], [1.0, 2.0], bom.operation_ids)
        ])
        self.env['stock.quant'].create([
            {
                'location_id': self.env.ref('stock.warehouse0').lot_stock_id.id,
                'product_id': comp.id,
                'inventory_quantity': 20,
            } for comp in [comp1, comp2]
        ]).action_apply_inventory()

        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom
        mo_form.product_qty = 5
        mo = mo_form.save()
        mo.action_confirm()

        wo = mo.workorder_ids.sorted()[0]
        wo.button_start()
        wo.button_finish()

        self.start_tour("/odoo/shop-floor", "test_change_qty_produced", login='admin')
        self.assertEqual(mo.qty_producing, 3)
        for move in mo.move_raw_ids:
            if move.product_id.id == comp1.id:
                self.assertEqual(move.quantity, 5)
                self.assertTrue(move.picked)
            if move.product_id.id == comp2.id:
                self.assertEqual(move.quantity, 6)
                self.assertTrue(move.picked)

    def test_update_tracked_consumed_materials_in_shopfloor(self):
        """
        Test that changing the consumed lot in a quality check updates the
        related moves accordingly.

        Detailed steps:
        - Create a bom with using a tracked component.
        - Create a quality check to register the consumed materials.
        - Put 4 SN in stock: 3 in the warehouse of the MO and 1 elsewhere to be unavailable.
        - Create and confirm an MO to consume 2 units.
        - Register: 1 of the reserved unit, 1 of the unreserved one and 1 unavaible one on the QC.

        Check that every update was correctly applied.
        """
        warehouse_1 = self.env.ref("stock.warehouse0")
        locations = self.env['stock.location'].create([
            {
            'name': f"Lovely shelf {i + 1}",
            'location_id': warehouse_1.lot_stock_id.id,
            'usage': 'internal',
            'company_id': self.env.company.id
            } for i in range(3)
        ]) | self.env['stock.warehouse'].create({'name': 'WH2', 'code': 'WH2', 'company_id': self.env.company.id}).lot_stock_id
        final_product, component = self.env['product.product'].create([
            {
            'name': 'Lovely Product',
            'is_storable': True,
            'tracking': 'none',
            },
            {
            'name': 'Lovely Component',
            'is_storable': True,
            'tracking': 'serial',
            },
        ])
        lots = self.env['stock.lot'].create([
            {'name': f'SN00{i + 1}', 'product_id': component.id}
            for i in range(4)
        ])
        for i in range(4):
            self.env['stock.quant']._update_available_quantity(component, locations[i], quantity=1, lot_id=lots[i])
        workcenter = self.env['mrp.workcenter'].create({
            'name': 'Lovely Workcenter',
        })
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'operation_ids': [
                Command.create({'name': 'Lovely Operation', 'workcenter_id': workcenter.id}),
            ],
            'bom_line_ids': [
                Command.create({'product_id': component.id, 'product_qty': 2}),
            ]
        })
        self.env['quality.point'].create([
            {
                'picking_type_ids': [Command.link(warehouse_1.manu_type_id.id)],
                'product_ids': [Command.link(final_product.id)],
                'operation_id': bom.operation_ids.id,
                'title': 'Register component',
                'component_id': component.id,
                'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
                'sequence': 1,
            },
        ])
        mo = self.env['mrp.production'].create({
            'product_id': final_product.id,
            'product_qty': 1,
            'bom_id': bom.id,
        })
        mo.action_confirm()
        mo.action_assign()
        mo.button_plan()
        self.assertEqual(mo.move_raw_ids.lot_ids, lots[:2])
        action = mo.workorder_ids.action_open_mes()
        url = '/web?#action=%s' % (action['id'])
        self.start_tour(url, "test_update_tracked_consumed_materials_in_shopfloor", login='admin')
        self.assertEqual(mo.move_raw_ids.quantity, 3.0)
        self.assertEqual(mo.move_raw_ids.lot_ids, lots[1:])
        self.assertEqual(mo.move_raw_ids.move_line_ids.filtered(lambda m: m.lot_id == lots[1]).location_id, locations[1])
        self.assertEqual(mo.move_raw_ids.move_line_ids.filtered(lambda m: m.lot_id == lots[2]).location_id, locations[2])
        # since the production happens in WH1, the update of SN004 should have fall back on that location
        self.assertEqual(mo.move_raw_ids.move_line_ids.filtered(lambda m: m.lot_id == lots[3]).location_id, warehouse_1.lot_stock_id)

    def test_shop_floor_catalog_add_component_in_two_steps(self):
        """ Ensures when a component is added through the Shop Floor catalog,
        the Pick Component operation is correctly created/updated."""
        # Set the manufacture in 2 steps.
        self.warehouse.write({'manufacture_steps': 'pbm'})
        # Create a product with a BoM and two components.
        # Create some products.
        product_final = self.env['product.product'].create({
            'name': 'Pot',
            'is_storable': True,
        })
        product_comp1, product_comp2 = self.env['product.product'].create([{
            'name': 'C1 - Earthenware Clay',
            'is_storable': True,
        }, {
            'name': 'C2 - Stoneware Clay',
            'is_storable': True,
        }])
        bom = self.env['mrp.bom'].create({
            'product_id': product_final.id,
            'product_tmpl_id': product_final.product_tmpl_id.id,
            'product_uom_id': product_final.uom_id.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'bom_line_ids': [
                Command.create({'product_id': product_comp1.id, 'product_qty': 1, 'manual_consumption': True}),
            ]
        })
        # Adds some quantity in stock.
        self.env['stock.quant']._update_available_quantity(product_comp1, self.stock_location, quantity=999)
        self.env['stock.quant']._update_available_quantity(product_comp2, self.stock_location, quantity=999)
        # Create a Manufacturing Order.
        mo = self.env['mrp.production'].create({
            'product_id': product_final.id,
            'product_qty': 1,
            'bom_id': bom.id,
        })
        mo.action_confirm()
        mo.action_assign()
        mo.button_plan()
        # Validate the MO's Pick Component.
        self.assertEqual(len(mo.picking_ids), 1)
        mo.picking_ids.button_validate()
        # Simulate "Add Component" from the Shop Floor.
        kwargs = {'from_shop_floor': True}
        mo._update_order_line_info(product_comp2.id, 1, 'move_raw_ids', **kwargs)
        self.assertEqual(len(mo.picking_ids), 2, "A second picking should have been created for the MO")
        self.assertEqual(mo.components_availability_state, 'available', "MO should still be ready nevertheless")
        second_picking = mo.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertRecordValues(second_picking.move_ids, [
            {'product_id': product_comp2.id, 'product_uom_qty': 1, 'picked': False},
        ])
        self.assertRecordValues(mo.move_raw_ids, [
            {'product_id': product_comp1.id, 'product_uom_qty': 1, 'quantity': 1, 'picked': False},
            {'product_id': product_comp2.id, 'product_uom_qty': 1, 'quantity': 1, 'picked': False},
        ])
        # Simulate adding more quantity from the Shop Floor.
        mo._update_order_line_info(product_comp2.id, 2, 'move_raw_ids', **kwargs)
        self.assertEqual(len(mo.picking_ids), 2, "No other picking should have been created")
        self.assertEqual(mo.components_availability_state, 'available', "MO should still be ready")
        self.assertRecordValues(second_picking.move_ids, [
            {'product_id': product_comp2.id, 'product_uom_qty': 2, 'picked': False},
        ])
        self.assertRecordValues(mo.move_raw_ids, [
            {'product_id': product_comp1.id, 'product_uom_qty': 1, 'quantity': 1, 'picked': False},
            {'product_id': product_comp2.id, 'product_uom_qty': 2, 'quantity': 2, 'picked': False},
        ])

    def test_under_consume_materials_in_shopfloor(self):
        """
        Test that underconsuming in a "register consumed materials" step updates
        the consumed quantity of the component accordingly and that the reservation
        state is not altered.
        """
        warehouse = self.env.ref("stock.warehouse0")
        final_product, component = self.env['product.product'].create([
            {
            'name': 'Lovely Product',
            'is_storable': True,
            'tracking': 'none',
            },
            {
            'name': 'Lovely Component',
            'is_storable': True,
            'tracking': 'none',
            },
        ])
        self.env['stock.quant']._update_available_quantity(component, warehouse.lot_stock_id, quantity=10)
        workcenter = self.env['mrp.workcenter'].create({
            'name': 'Lovely Workcenter',
        })
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'operation_ids': [
                Command.create({'name': 'Lovely Operation', 'workcenter_id': workcenter.id}),
            ],
            'bom_line_ids': [
                Command.create({'product_id': component.id, 'product_qty': 10}),
            ]
        })
        self.env['quality.point'].create([
            {
                'picking_type_ids': [Command.link(warehouse.manu_type_id.id)],
                'product_ids': [Command.link(final_product.id)],
                'operation_id': bom.operation_ids.id,
                'title': 'Register component',
                'component_id': component.id,
                'test_type_id': self.env.ref('mrp_workorder.test_type_register_consumed_materials').id,
                'sequence': 1,
            },
        ])
        mo = self.env['mrp.production'].create({
            'product_id': final_product.id,
            'product_qty': 1,
            'bom_id': bom.id,
        })
        mo.action_confirm()
        mo.action_assign()
        self.assertEqual(mo.reservation_state, 'assigned')
        mo.button_plan()
        self.assertEqual(mo.move_raw_ids.quantity, 10.0)
        action = mo.workorder_ids.action_open_mes()
        url = '/web?#action=%s' % (action['id'])
        self.start_tour(url, "test_under_consume_materials_in_shopfloor", login='admin')
        self.assertEqual(mo.move_raw_ids.quantity, 5.0)
        self.assertEqual(mo.move_raw_ids.move_line_ids.mapped('quantity'), [3.0, 2.0])
        self.assertEqual(len(mo.move_raw_ids.move_line_ids.quality_check_ids), 2.0)
        self.assertEqual(mo.reservation_state, 'assigned')

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import Form, tagged
from odoo.addons.stock_barcode.tests.test_barcode_client_action import TestBarcodeClientAction


@tagged('post_install', '-at_install')
class TestMRPBarcodeClientAction(TestBarcodeClientAction):
    def setUp(self):
        super().setUp()

        self.component01 = self.env['product.product'].create({
            'name': 'Compo 01',
            'is_storable': True,
            'barcode': 'compo01',
        })
        self.component_lot = self.env['product.product'].create({
            'name': 'Compo Lot',
            'is_storable': True,
            'barcode': 'compo_lot',
            'tracking': 'lot',
        })

        self.final_product = self.env['product.product'].create({
            'name': 'Final Product',
            'is_storable': True,
            'barcode': 'final',
        })

        self.final_product_lot = self.env['product.product'].create({
            'name': 'Final Product2',
            'is_storable': True,
            'barcode': 'final_lot',
            'tracking': 'lot',
        })

        self.by_product = self.env['product.product'].create({
            'name': 'By Product',
            'is_storable': True,
            'barcode': 'byproduct'
        })

        self.bom_lot = self.env['mrp.bom'].create({
            'product_tmpl_id': self.final_product_lot.product_tmpl_id.id,
            'product_qty': 2.0,
            'bom_line_ids': [
                (0, 0, {'product_id': self.component01.id, 'product_qty': 2.0}),
                (0, 0, {'product_id': self.component_lot.id, 'product_qty': 2.0}),
            ],
        })

    def test_barcode_production_process(self):
        """Create a manufacturing order in the backend and process it
            in the barcode app.
        """
        self.env['stock.quant'].create({
            'quantity': 4,
            'product_id': self.component01.id,
            'location_id': self.stock_location.id,
        })

        mo = self.env['mrp.production'].create({
            'product_id': self.final_product.id,
            'product_qty': 1,
            'move_raw_ids': [(0, 0, {
                'product_id': self.component01.id,
                'product_uom_qty': 2
            })]
        })

        mo.action_confirm()

        url = "/odoo/action-stock_barcode.stock_picking_type_action_kanban"
        self.start_tour(url, 'test_process_confirmed_mo', login='admin', timeout=180)
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.qty_produced, 1)
        self.assertEqual(mo.qty_producing, 1)

    def test_barcode_production_create(self):
        """Create a manufacturing order from barcode app
        """
        self.clean_access_rights()
        self.env['stock.quant'].create({
            'quantity': 4,
            'product_id': self.component01.id,
            'location_id': self.stock_location.id,
        })
        url = "/odoo/action-stock_barcode.stock_picking_type_action_kanban"
        self.start_tour(url, 'test_barcode_production_create', login='admin', timeout=180)
        mo = self.env['mrp.production'].search([], order='id desc', limit=1)
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.qty_produced, 2)
        self.assertRecordValues(mo.move_raw_ids, [
            {'product_id': self.component01.id, 'product_uom_qty': 2},
        ])

    def test_barcode_production_create_bom(self):
        """ Creates a manufacturing order and scans a product who has a BoM, it
        should create a line for each component, and automatically increase
        their quantity every time the final product is scanned.
        """
        self.clean_access_rights()
        # Creates a BoM.
        component02 = self.env['product.product'].create({
            'name': 'Compo 02',
            'is_storable': True,
            'barcode': 'compo02',
        })
        self.env['mrp.bom'].create({
            'product_tmpl_id': self.final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {'product_id': self.component01.id, 'product_qty': 2.0}),
                (0, 0, {'product_id': component02.id, 'product_qty': 3.0}),
            ],
        })
        # Adds some quantities in stock for the components.
        for component in [self.component01, component02]:
            self.env['stock.quant'].create({
                'quantity': 99,
                'product_id': component.id,
                'location_id': self.stock_location.id,
            })

        url = "/odoo/action-stock_barcode.stock_picking_type_action_kanban"
        self.start_tour(url, 'test_barcode_production_create_bom', login='admin', timeout=180)
        mo = self.env['mrp.production'].search([], order='id desc', limit=1)
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.qty_produced, 3)
        self.assertRecordValues(mo.move_raw_ids, [
            {'product_id': self.component01.id, 'product_uom_qty': 2, 'quantity': 6},
            {'product_id': component02.id, 'product_uom_qty': 3, 'quantity': 9},
        ])

    def test_barcode_production_create_tracked_bom(self):
        """Create a manufacturing order with bom from barcode app, with byproducts
        """
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        grp_by_product = self.env.ref('mrp.group_mrp_byproducts')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0), (4, grp_by_product.id, 0)]})
        self.env['stock.quant'].create({
            'quantity': 4,
            'product_id': self.component01.id,
            'location_id': self.stock_location.id,
        })
        lot_id = self.env['stock.lot'].create({
            'name': 'lot01',
            'product_id': self.component_lot.id,
        })
        self.env['stock.quant'].create({
            'quantity': 4,
            'product_id': self.component_lot.id,
            'location_id': self.stock_location.id,
            'lot_id': lot_id.id
        })
        url = "/odoo/action-stock_barcode.stock_picking_type_action_kanban"
        self.start_tour(url, 'test_barcode_production_create_tracked_bom', login='admin', timeout=180)
        mo = self.env['mrp.production'].search([], order='id desc', limit=1)
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.qty_produced, 3)
        self.assertRecordValues(mo.move_raw_ids, [
            {'product_id': self.component01.id, 'product_uom_qty': 3, 'quantity': 3},
            {'product_id': self.component_lot.id, 'product_uom_qty': 3, 'quantity': 3},
        ])
        self.assertRecordValues(mo.move_byproduct_ids, [
            {'product_id': self.by_product.id, 'product_uom_qty': 2, 'quantity': 2},
        ])

    def test_barcode_production_reserved_from_multiple_locations(self):
        """ Process a production with components reserved in different locations
        and with the scan of the source for each component.
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        picking_type_production = self.env['stock.picking.type'].search([
            ('code', '=', 'mrp_operation'), ('company_id', '=', self.env.company.id)])
        picking_type_production.restrict_scan_dest_location = 'no'
        picking_type_production.restrict_scan_source_location = 'mandatory'
        # Creates a BoM and adds some quantities for the components in different locations.
        self.env['mrp.bom'].create({
            'product_tmpl_id': self.final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {'product_id': self.component01.id, 'product_qty': 2.0}),
            ],
        })
        self.env['stock.quant'].create({
            'quantity': 1,
            'product_id': self.component01.id,
            'location_id': self.shelf1.id,
        })
        self.env['stock.quant'].create({
            'quantity': 2,
            'product_id': self.component01.id,
            'location_id': self.shelf2.id,
        })
        self.env['stock.quant'].create({
            'quantity': 2,
            'product_id': self.component01.id,
            'location_id': self.shelf3.id,
        })
        self.env['stock.quant'].create({
            'quantity': 1,
            'product_id': self.component01.id,
            'location_id': self.shelf4.id,
        })
        # Prepares a production for 3x final product, then process it in the Barcode App.
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.final_product
        mo_form.product_qty = 3
        mo = mo_form.save()
        mo.action_confirm()

        url = f'/odoo/{mo.id}/action-stock_barcode_mrp.stock_barcode_mo_client_action?debug=assets'
        self.start_tour(url, 'test_barcode_production_reserved_from_multiple_locations', login='admin', timeout=180)

    def test_barcode_production_scan_other_than_reserved(self):
        """ Process a production with a reserved untracked component and a lot tracked component.
        Scan a different lot than the reserved lot and scan a different (location) component than
        the reserved location."""
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0), (4, grp_multi_loc.id, 0)]})
        picking_type_production = self.env['stock.picking.type'].search([
            ('code', '=', 'mrp_operation'), ('company_id', '=', self.env.company.id)])
        picking_type_production.restrict_scan_source_location = 'mandatory'
        # Prepares a production for 2x final product, then process it in the Barcode App.
        lot_01 = self.env['stock.lot'].create({
            'name': 'lot_01',
            'product_id': self.component_lot.id,
        })
        lot_02 = self.env['stock.lot'].create({
            'name': 'lot_02',
            'product_id': self.component_lot.id,
        })
        self.env['stock.quant'].create({
            'quantity': 2,
            'product_id': self.component01.id,
            'location_id': self.stock_location.id,
        })
        self.env['stock.quant'].create({
            'quantity': 2,
            'product_id': self.component01.id,
            'location_id': self.shelf1.id,
        })
        self.env['stock.quant'].create({
            'quantity': 2,
            'product_id': self.component_lot.id,
            'location_id': self.stock_location.id,
            'lot_id': lot_01.id
        })
        self.env['stock.quant'].create({
            'quantity': 2,
            'product_id': self.component_lot.id,
            'location_id': self.stock_location.id,
            'lot_id': lot_02.id
        })

        untracked_product_bom_line = self.bom_lot.bom_line_ids.filtered(lambda l: l.product_id == self.component01)
        untracked_product_bom_line.manual_consumption = True

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.final_product_lot
        mo_form.product_qty = 2
        mo = mo_form.save()
        mo.action_confirm()

        url = f'/odoo/{mo.id}/action-stock_barcode_mrp.stock_barcode_mo_client_action?debug=assets'
        self.start_tour(url, 'test_barcode_production_scan_other_than_reserved', login='admin', timeout=180)

        # Checks move lines values after MO is completed.
        self.assertEqual(mo.state, "done")
        # ensure that lot ml not scanned by validation time is removed
        self.assertEqual(len(mo.move_raw_ids.move_line_ids), 2)
        self.assertRecordValues(mo.move_raw_ids, [
            {'product_id': self.component01.id, 'product_uom_qty': 2, 'quantity': 2, 'lot_ids': [], 'location_id': self.stock_location.id},
            {'product_id': self.component_lot.id, 'product_uom_qty': 2, 'quantity': 2, 'lot_ids': lot_02.ids, 'location_id': self.stock_location.id},
        ])
        self.assertRecordValues(mo.move_raw_ids.move_line_ids, [
            {'product_id': self.component01.id, 'quantity': 2, 'lot_id': False, 'location_id': self.shelf1.id},
            {'product_id': self.component_lot.id, 'quantity': 2, 'lot_id': lot_02.id, 'location_id': self.stock_location.id},
        ])
        self.assertRecordValues(mo.finished_move_line_ids, [
            {'product_id': self.final_product_lot.id, 'quantity': 2},
        ])
        self.assertEqual(mo.finished_move_line_ids.lot_id.name, "finished_lot")

    def test_barcode_production_component_no_stock(self):
        """Create MO from barcode for final product with bom but component has not stock
        """
        self.clean_access_rights()
        self.env['mrp.bom'].create({
            'product_tmpl_id': self.final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {'product_id': self.component01.id, 'product_qty': 2.0}),
            ],
        })
        url = "/odoo/action-stock_barcode.stock_picking_type_action_kanban"
        self.start_tour(url, 'test_barcode_production_component_no_stock', login='admin', timeout=180)

    def test_mo_scrap_digipad_view(self):
        """
        Checks if a new, mobile-friendly scrap view is shown for MOs.
        """
        mo = self.env['mrp.production'].create({
            'product_id': self.final_product.id,
            'product_qty': 1,
            'move_raw_ids': [(0, 0, {
                'product_id': self.component01.id,
                'product_uom_qty': 1
            })]
        })
        # Ensure state != 'cancel' && state != 'draft' to allow Scrap
        mo.action_confirm()

        url = f'/odoo/{mo.id}/action-stock_barcode_mrp.stock_barcode_mo_client_action?debug=assets'
        self.start_tour(url, 'test_mo_scrap_digipad_view', login='admin', timeout=180)

    def test_barcode_production_components_reservation_state(self):
        """ When components are unreserved, they should not be visible in the
        Barcode app nor re-reserved when the MO is opened.
        Only reserved components should be visible in the barcode."""
        self.clean_access_rights()
        self.env['stock.quant'].create({
            'quantity': 4,
            'product_id': self.component01.id,
            'location_id': self.stock_location.id,
        })
        mo = self.env['mrp.production'].create({
            'product_id': self.final_product.id,
            'product_qty': 1,
            'move_raw_ids': [(0, 0, {
                'product_id': self.component01.id,
                'product_uom_qty': 2,
                'picked': False,
            })]
        })
        mo.action_confirm()
        url = f"/odoo/{mo.id}/action-stock_barcode_mrp.stock_barcode_mo_client_action"

        # when MO component's are reserved
        self.assertEqual(mo.move_raw_ids.move_line_ids.quantity, mo.move_raw_ids.product_uom_qty)
        self.start_tour(url, 'test_barcode_production_components_reservation_state_reserved', login='admin', timeout=180)

        # when MO component's are unreserved
        self.assertEqual(len(mo.move_raw_ids.move_line_ids), 1)
        mo.do_unreserve()
        self.assertEqual(len(mo.move_raw_ids.move_line_ids), 0)
        self.start_tour(url, 'test_barcode_production_components_reservation_state_unreserved', login='admin', timeout=180)
        self.assertEqual(
            len(mo.move_raw_ids.move_line_ids), 0,
            "Verify MO components are still unreserved after open the MO in the Barcode app")

    def test_barcode_production_add_scrap(self):
        """ Process a production where one of the component is scraped
        """
        self.clean_access_rights()
        # Creates a BoM.
        component02 = self.env['product.product'].create({
            'name': 'Compo 02',
            'is_storable': True,
            'barcode': 'compo02',
        })
        self.env['mrp.bom'].create({
            'product_tmpl_id': self.final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {'product_id': self.component01.id, 'product_qty': 1.0}),
                (0, 0, {'product_id': component02.id, 'product_qty': 1.0}),
            ],
        })
        # Adds some quantities in stock for the components.
        for component in [self.component01, component02]:
            self.env['stock.quant'].create({
                'quantity': 99,
                'product_id': component.id,
                'location_id': self.stock_location.id,
            })

        url = "/odoo/action-stock_barcode.stock_picking_type_action_kanban"
        self.start_tour(url, 'test_barcode_production_add_scrap', login='admin', timeout=180)
        mo = self.env['mrp.production'].search([], order='id desc', limit=1)
        self.assertEqual(mo.scrap_count, 1)
        self.assertEqual(mo.scrap_ids.product_id.name, 'Compo 01')

    def test_barcode_production_add_byproduct(self):
        """ Process a production where we add a byproduct.
        We ensure the final product can't be added as a byproduct.
        """
        self.clean_access_rights()
        grp_by_product = self.env.ref('mrp.group_mrp_byproducts')
        self.env.user.write({'groups_id': [(4, grp_by_product.id, 0)]})
        # Disable creation of new lots for component, the purpose is to check
        # by-products lots can still be created anyway.
        self.env['stock.picking.type'].search(
            [('code', '=', 'mrp_operation')], limit=1
        ).use_create_components_lots = False
        # Creates a BoM.
        component02 = self.env['product.product'].create({
            'name': 'Compo 02',
            'is_storable': True,
            'barcode': 'compo02',
        })
        self.env['mrp.bom'].create({
            'product_tmpl_id': self.final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {'product_id': self.component01.id, 'product_qty': 1.0}),
                (0, 0, {'product_id': component02.id, 'product_qty': 1.0}),
            ],
        })
        # Adds some quantities in stock for the components.
        for component in [self.component01, component02]:
            self.env['stock.quant'].create({
                'quantity': 99,
                'product_id': component.id,
                'location_id': self.stock_location.id,
            })

        url = "/odoo/action-stock_barcode.stock_picking_type_action_kanban"
        self.start_tour(url, 'test_barcode_production_add_byproduct', login='admin', timeout=180)
        mo = self.env['mrp.production'].search([], order='id desc', limit=1)
        self.assertEqual(len(mo.move_byproduct_ids), 2)
        self.assertEqual(mo.move_byproduct_ids[0].product_id.display_name, 'By Product')
        self.assertEqual(mo.move_byproduct_ids[1].product_id.display_name, 'Compo Lot')
        self.assertEqual(mo.move_byproduct_ids[1].lot_ids.name, 'byprod_lot_001')

    def test_split_line_on_exit_for_production(self):
        """ Ensures that exit an unfinished MO will split the uncompleted move lines to have one
        move line with all picked quantity and one move line with the remaining qty."""
        self.clean_access_rights()

        # Creates a product with a BoM.
        product_final = self.env['product.product'].create({
            'name': 'Final Product',
            'is_storable': True,
        })
        bom = self.env['mrp.bom'].create({
            'product_id': product_final.id,
            'product_tmpl_id': product_final.product_tmpl_id.id,
            'product_uom_id': product_final.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'consumption':  'flexible',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product1.id, 'product_qty': 2}),
                (0, 0, {'product_id': self.product2.id, 'product_qty': 1})
            ]})

        # Adds some quantity in stock.
        self.env['stock.quant'].create({
            'quantity': 4,
            'product_id': self.product1.id,
            'location_id': self.stock_location.id,
        })
        self.env['stock.quant'].create({
            'quantity': 2,
            'product_id': self.product2.id,
            'location_id': self.stock_location.id,
        })

        # Creates and confirms manufacturing order for 2 product_final.
        production = self.env['mrp.production'].create({
            'name': "production_split_line_on_exit",
            'bom_id': bom.id,
            'product_id': product_final.id,
            'product_qty': 2,
        })
        production.action_confirm()

        self.start_tour("odoo/barcode/", 'test_split_line_on_exit_for_production', login='admin')
        # Checks production moves raw values.
        self.assertRecordValues(production.move_raw_ids, [
            {'product_id': self.product1.id, 'quantity': 4, 'picked': True},
            {'product_id': self.product2.id, 'quantity': 2, 'picked': True},
        ])
        self.assertRecordValues(production.move_raw_line_ids, [
            {'product_id': self.product1.id, 'quantity': 3, 'picked': True},
            {'product_id': self.product1.id, 'quantity': 1, 'picked': False},
            {'product_id': self.product2.id, 'quantity': 1, 'picked': True},
            {'product_id': self.product2.id, 'quantity': 1, 'picked': False},
        ])

    def test_barcode_production_component_different_uom(self):
        self.clean_access_rights()
        self.env.ref('base.user_admin').groups_id += self.env.ref('uom.group_uom')
        uom_kg = self.env.ref('uom.product_uom_kgm')
        uom_gm = self.env.ref('uom.product_uom_gram')
        self.component01.uom_id = uom_gm
        self.env['mrp.bom'].create({
            'product_tmpl_id': self.final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {'product_id': self.component01.id, 'product_qty': 1.0, 'product_uom_id': uom_kg.id}),
            ],
        })
        url = "/odoo/action-stock_barcode.stock_picking_type_action_kanban"
        self.start_tour(url, 'test_barcode_production_component_different_uom', login='admin', timeout=180)

    def test_multi_company_manufacture_creation_in_barcode(self):
        """ Ensure that when a manufacturing operation of an active (checked) company is scanned,
        then some product is added, its `company_id` matches that of the operation type.
        """
        self.clean_access_rights()
        company2 = self.env['res.company'].create({'name': 'second company'})
        self.env.user.company_ids = [(4, company2.id)]
        self.env['stock.picking.type'].search([
            ('code', '=', 'mrp_operation'),
            ('company_id', '=', company2.id),
        ], limit=1).barcode = 'company2_mrp_operation'

        cids = '-'.join(str(cid) for cid in self.env.user.company_ids.ids)
        url = f'/odoo/action-stock_barcode.stock_barcode_action_main_menu?cids={cids}'
        self.start_tour(url, 'test_multi_company_manufacture_creation_in_barcode', login='admin', timeout=180)

        self.assertEqual(
            len(self.env['mrp.production'].search([('company_id', '=', company2.id)])),
            2
        )

    def test_multi_company_record_access_in_mrp_barcode(self):
        """ Ensure that, when in the barcode view for an active company's manufacturing operation,
        it is not possible to add a product belonging exclusively to an inactive (unchecked)
        company to the operation and that scanning such a product does not prevent the user from
        using the back button.

        Then, ensure that we can add a product that belongs to the company who owns the MO picking
        type.
        """
        self.clean_access_rights()
        company2 = self.env['res.company'].create({'name': 'second company'})
        company2_product = self.env['product.product'].create({
            'name': 'second company product',
            'company_id': company2.id,
            'barcode': 'second_company_product'
        })

        self.env['stock.picking.type'].search([
            ('code', '=', 'mrp_operation'),
            ('company_id', '=', self.env.company.id),
        ], limit=1).barcode = 'company_mrp_operation'

        cids = '-'.join(str(cid) for cid in self.env.user.company_ids.ids)
        url = f'/odoo/action-stock_barcode.stock_barcode_action_main_menu?cids={cids}'
        self.start_tour(url, 'test_multi_company_record_access_in_mrp_barcode', login='admin', timeout=180)

        self.assertFalse(
            self.env['mrp.production'].search([
                ('company_id', '=', self.env.company.id),
                ('product_id', '=', company2_product.id),
            ], limit=1)
        )

        self.env.companies += company2
        self.env['stock.picking.type'].search([
            ('code', '=', 'mrp_operation'),
            ('company_id', '=', company2.id),
        ], limit=1).barcode = 'company2_mrp_operation'
        url = url + f'-{company2.id}'
        self.start_tour(url, 'test_multi_company_record_access_in_mrp_barcode2', login='admin', timeout=180)

        self.assertTrue(
            self.env['mrp.production'].search([
                ('company_id', '=', company2.id),
                ('product_id', '=', company2_product.id),
            ], limit=1)
        )

    def test_kit_bom_decomposition_keeps_location(self):
        self.clean_access_rights()
        self.env.user.groups_id += self.env.ref('stock.group_stock_multi_locations')
        self.picking_type_internal.active = True

        final_2 = self.env['product.product'].create({
            'name': 'final2',
            'is_storable': True,
            'barcode': 'final2',
        })
        for comp1, comp2, final_prod in [
            (self.component01, self.product1, self.final_product),
            (self.component01, self.product2, final_2),
        ]:
            self.env['mrp.bom'].create({
                'product_tmpl_id': final_prod.product_tmpl_id.id,
                'product_id': final_prod.id,
                'product_qty': 1.0,
                'type': 'phantom',
                'bom_line_ids': [
                    (0, 0, {'product_id': comp1.id, 'product_qty': 1.0}),
                    (0, 0, {'product_id': comp2.id, 'product_qty': 1.0}),
                ],
            })

        test_pickings = self.env['stock.picking']
        for i in range(1, 3):
            test_pickings += self.env['stock.picking'].create({
                'name': f'test_kit_bom_decomposition_keeps_location_picking{i}',
                'picking_type_id': self.picking_type_internal.id,
                'location_id': self.stock_location.id,
                'location_dest_id': self.stock_location.id,
            })

        url = "/odoo/action-stock_barcode.stock_barcode_action_main_menu"
        self.start_tour(url, 'test_kit_bom_decomposition_keeps_location', login='admin', timeout=180)

        expected_move_line_vals_list = [
            [
                {'product_id': self.component01.id, 'location_id': self.stock_location.id, 'location_dest_id': self.shelf1.id},
                {'product_id': self.product1.id, 'location_id': self.stock_location.id, 'location_dest_id': self.shelf1.id},
                {'product_id': self.component01.id, 'location_id': self.stock_location.id, 'location_dest_id': self.shelf2.id},
                {'product_id': self.product1.id, 'location_id': self.stock_location.id, 'location_dest_id': self.shelf2.id},
            ],
            [
                {'product_id': self.component01.id, 'location_id': self.stock_location.id, 'location_dest_id': self.shelf1.id},
                {'product_id': self.product1.id, 'location_id': self.stock_location.id, 'location_dest_id': self.shelf1.id},
                {'product_id': self.component01.id, 'location_id': self.stock_location.id, 'location_dest_id': self.shelf2.id},
                {'product_id': self.product2.id, 'location_id': self.stock_location.id, 'location_dest_id': self.shelf2.id},
            ]
        ]

        for test_picking, expected_move_line_vals in zip(test_pickings, expected_move_line_vals_list):
            self.assertRecordValues(test_picking.move_line_ids, expected_move_line_vals)

    def test_always_backorder_mo_without_redirect_to_backend(self):
        """
        Check that you are not redirect to the backend when you automatically
        backorder an mo from the barcode module.
        """
        self.clean_access_rights()
        warehouse = self.stock_location.warehouse_id
        manufacturing_type = warehouse.manu_type_id
        manufacturing_type.create_backorder = "always"
        product = self.final_product
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_qty': 1.0,
        })
        mo = self.env['mrp.production'].create({
            'product_id': product.id,
            'product_qty': 3.0,
            'bom_id': bom.id,
        })
        mo.action_confirm()

        action_id = self.env.ref('stock_barcode.stock_picking_type_action_kanban')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_always_backorder_mo', login='admin', timeout=180)
        self.assertRecordValues(mo, [{'state':  'done', 'qty_produced': 1.0}])
        bo = mo.backorder_ids - mo
        self.assertRecordValues(bo, [{'product_id': product.id, 'product_qty': 2.0}])

    def test_backorder_partial_completion_save_sensible_split(self):
        """
        In a production opened in Barcode, create move lines as opposed to moves when having to
        split incomplete transfer lines but dont split unassigned.
        """
        self.clean_access_rights()

        available_comp, unavailable_comp = self.component01, self.product1
        self.env['stock.quant']._update_available_quantity(available_comp, self.stock_location, quantity=10)

        manufacturing_order = self.env['mrp.production'].create({
            'name': 'TBPCSNS mo',
            'product_id': self.final_product.id,
            'product_qty': 10,
            'move_raw_ids': [
                Command.create({
                    'product_id': available_comp.id,
                    'product_uom_qty': 10,
                }),
                Command.create({
                    'product_id': unavailable_comp.id,
                    'product_uom_qty': 4,
                }),
            ],
        })
        manufacturing_order.action_confirm()

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = f"/web#action={action_id.id}"
        self.start_tour(url, 'test_backorder_partial_completion_save_sensible_split', login='admin', timeout=180)
        # Check that the unavailable + unedited component move was unaffected by the split
        self.assertEqual(manufacturing_order.move_raw_ids.filtered(lambda m: m.product_id == unavailable_comp).mapped('quantity'), [0.00])
        backorder_mo = manufacturing_order.backorder_ids - manufacturing_order
        self.assertRecordValues(
            backorder_mo.move_raw_ids.sorted('product_uom_qty'), [
                {'product_id': unavailable_comp.id, 'product_uom_qty': 2, 'quantity': 0, 'picked': False},
                {'product_id': available_comp.id, 'product_uom_qty': 5, 'quantity': 5, 'picked': False},
            ]
        )
        self.assertRecordValues(
            backorder_mo.move_finished_ids,
            [{'quantity': 5, 'product_uom_qty': 5,}]
        )

    def test_barcode_mo_creation_in_mo2(self):
        """
        Ensures that MO is created in another manufacturing operation type (MO2)
        with creating new MO in MO2 operation type and confirm it and Produce it.
        """
        self.clean_access_rights()

        mo2_operation_type = self.env['stock.picking.type'].create({
            'name': 'MO2',
            'barcode': 'MO2_BARCODE',
            'code': 'mrp_operation',
            'sequence_code': 'MO2',
            'warehouse_id': self.env.ref('stock.warehouse0').id,
        })

        product_to_manufacture = self.env['product.product'].create({
            'name': 'Product4',
            'is_storable': True,
            'barcode': 'MO2_TEST_PRODUCT',
        })
        self.start_tour('/odoo/barcode', 'test_barcode_mo_creation_in_mo2', login='admin')

        mos = self.env['mrp.production'].search([('product_id', '=', product_to_manufacture.id)])
        self.assertEqual(len(mos), 2, "Two Manufacturing Orders must have been created.")
        self.assertEqual(mos[0].picking_type_id, mo2_operation_type, "The first MO was not created with the correct operation type (MO2).")
        self.assertEqual(mos[1].picking_type_id, mo2_operation_type, "The second MO was not created with the correct operation type (MO2).")

    def test_barcode_mo_creation_in_scan_mo2(self):
        """
        Ensures that MO is created in another manufacturing operation type (MO2)
        with creating new MO in MO2 operation type by scanning the product and Produce it.
        """
        self.clean_access_rights()

        mo2_operation_type = self.env['stock.picking.type'].create({
            'name': 'MO2',
            'code': 'mrp_operation',
            'sequence_code': 'MO2',
            'warehouse_id': self.env.ref('stock.warehouse0').id,
        })

        product_to_manufacture = self.env['product.product'].create({
            'name': 'Test Product',
            'is_storable': True,
            'barcode': 'MO2_TEST_PRODUCT',
        })
        url = "/odoo/action-stock_barcode.stock_picking_type_action_kanban"
        self.start_tour(url, 'test_barcode_mo_creation_in_scan_mo2', login='admin', timeout=180)

        mo = self.env['mrp.production'].search([('product_id', '=', product_to_manufacture.id)], limit=1)
        self.assertTrue(mo, "The Manufacturing Order was not created.")
        self.assertEqual(mo.picking_type_id, mo2_operation_type, "The MO was not created with the correct operation type (MO2).")

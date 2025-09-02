# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.exceptions import UserError
from .test_common import TestQualityCommon
from odoo.tests import Form, tagged


@tagged('-at_install', 'post_install')
class TestQualityCheck(TestQualityCommon):

    def test_00_picking_quality_check(self):

        """Test quality check on incoming shipment."""

        # Create Quality Point for incoming shipment.
        self.qality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
        })

        # Check that quality point created.
        self.assertTrue(self.qality_point_test, "First Quality Point not created for Laptop Customized.")

        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id})

        # Check that incoming shipment is created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")

        # Confirm incoming shipment.
        self.picking_in.action_confirm()

        # Check Quality Check for incoming shipment is created and check it's state is 'none'.
        self.assertEqual(len(self.picking_in.check_ids), 1)
        self.assertEqual(self.picking_in.check_ids.quality_state, 'none')

        # 'Pass' Quality Checks of incoming shipment.
        self.picking_in.check_ids.do_pass()

        # Validate incoming shipment.
        self.picking_in.button_validate()

        # Now check state of quality check.
        self.assertEqual(self.picking_in.check_ids.quality_state, 'pass')

    def test_01_picking_quality_check_type_text(self):

        """ Test a Quality Check on a picking with 'Instruction'
        as test type.
        """
        # Create Quality Point for incoming shipment with 'Instructions' as test type
        self.qality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'test_type_id': self.env.ref('quality.test_type_instructions').id
        })

        # Check that quality point created.
        self.assertTrue(self.qality_point_test, "Quality Point not created")

        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id})

        # Check that incoming shipment is created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")

        # Confirm incoming shipment.
        self.picking_in.action_confirm()

        # Check Quality Check for incoming shipment is created and check it's state is 'none'.
        self.assertEqual(len(self.picking_in.check_ids), 1)
        self.assertEqual(self.picking_in.check_ids.quality_state, 'none')

        # Check that the Quality Check on the picking has 'instruction' as test_type
        self.assertEqual(self.picking_in.check_ids[0].test_type, 'instructions')

    def test_02_picking_quality_check_type_picture(self):

        """ Test a Quality Check on a picking with 'Take Picture'
        as test type.
        """
        # Create Quality Point for incoming shipment with 'Take Picture' as test type
        self.qality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'test_type_id': self.env.ref('quality.test_type_picture').id
        })
        # Check that quality point created.
        self.assertTrue(self.qality_point_test, "Quality Point not created")
        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id})
        # Check that incoming shipment is created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")
        # Confirm incoming shipment.
        self.picking_in.action_confirm()
        # Check Quality Check for incoming shipment is created and check it's state is 'none'.
        self.assertEqual(len(self.picking_in.check_ids), 1)
        self.assertEqual(self.picking_in.check_ids.quality_state, 'none')

        # Check that the Quality Check on the picking has 'picture' as test_type
        self.assertEqual(self.picking_in.check_ids[0].test_type, 'picture')

    def test_03_lot_quality_check(self):
        """ Test a Quality Check at the lot level.
        """
        product_tracked_by_lot = self.env['product.product'].create({
            'name': 'Product tracked by lot',
            'tracking': 'lot',
        })

        product = self.env['product.product'].create({
            'name': 'Product',
            'tracking': 'none',
        })

        # Create Quality Point for incoming shipment on lots with 'Measure' as test type
        self.quality_point_test1 = self.env['quality.point'].create({
            'product_ids': [product_tracked_by_lot.id],
            'picking_type_ids': [self.picking_type_id],
            'test_type_id': self.env.ref('quality_control.test_type_measure').id,
            'testing_percentage_within_lot': 10.02,
            'measure_on': 'move_line',
            'norm': 5.,
            'tolerance_min': 4.,
            'tolerance_max': 6.,
        })

        # Create Quality Point for incoming shipment on lots for all products
        self.quality_point_test2 = self.env['quality.point'].create({
            'picking_type_ids': [self.picking_type_id],
            'test_type_id': self.env.ref('quality_control.test_type_measure').id,
            'measure_on': 'move_line',
        })

        # Create Quality Point for product without tracking
        self.quality_point_test3 = self.env['quality.point'].create({
            'product_ids': [product.id],
            'picking_type_ids': [self.picking_type_id],
            'test_type_id': self.env.ref('quality_control.test_type_measure').id,
            'measure_on': 'move_line',
        })

        # Check that the quality points are created
        self.assertTrue(self.quality_point_test1, "Quality Point not created")
        self.assertTrue(self.quality_point_test2, "Quality Point not created")
        self.assertTrue(self.quality_point_test3, "Quality Point not created")

        # Create incoming shipment
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })

        move = self.env['stock.move'].create({
            'name': product_tracked_by_lot.name,
            'product_id': product_tracked_by_lot.id,
            'product_uom_qty': 11,
            'product_uom': product_tracked_by_lot.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id})

        # Check that incoming shipment is created
        self.assertTrue(self.picking_in, "Incoming shipment not created.")

        # Creating move lines with the serial number widget
        move._generate_serial_numbers("1", next_serial_count=10)
        self.assertTrue(len(move.move_line_ids) == 10, "Not all move lines are created with _generate_serial_number")

        # Check that quality checks were created
        self.assertTrue(len(move.move_line_ids.check_ids) == 20, "Wrong number of Quality Checks created on the move lines")

        # Create move line without qty_done and setting it after
        move_line_vals = move._prepare_move_line_vals()
        move_line = self.env['stock.move.line'].create(move_line_vals)
        move_line.quantity = 1.
        self.assertTrue(len(move.move_line_ids.check_ids) == 22, "Wrong number of Quality Checks created on the move lines")

        # Updating quantity of one move line
        move.move_line_ids[0].quantity = 2
        check_line1 = move.move_line_ids[0].check_ids[0]
        check_line2 = move.move_line_ids[1].check_ids[0]

        # Check that the percentage of the lot to check is correct
        self.assertTrue(check_line1.qty_to_test == 0.21, "Quantity to test within lot not well calculated (check rounding)")
        self.assertTrue(check_line2.qty_to_test == 0.11, "Quantity to test within lot not well calculated (check rounding)")

        # Check that tests are failing and succeeding properly
        check_line1.measure = 3.
        check_line2.measure = 4.5
        check_line1.do_measure()
        check_line2.do_measure()
        self.assertTrue(check_line1.quality_state == 'fail', "Quality Check of type 'measure' not failing on move line")
        self.assertTrue(check_line2.quality_state == 'pass', "Quality Check of type 'measure' not passing on move line")

        # Create move with a product without tracking with done quantity
        move_without_tracking1 = self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'quantity': 1,
            'product_uom': product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        self.assertTrue(len(move_without_tracking1.move_line_ids.check_ids) == 2, "Wrong number of Quality Checks created on the move lines")

        # Create move with a product without tracking without done quantity and changing done quantity after
        move_without_tracking2 = self.env['stock.move'].create({
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'quantity': 0,
            'product_uom': product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        move_without_tracking2.quantity = 1
        self.assertTrue(len(move_without_tracking2.move_line_ids.check_ids) == 2, "Wrong number of Quality Checks created on the move lines")

    def test_04_picking_quality_check_creation_no_products_no_categories(self):

        """ Test Quality Check creation on incoming shipment from a Quality Point
        with no products and no product_categories set
        """
        # Create Quality Point for incoming shipment with no product or product_category set.
        self.quality_point_test = self.env['quality.point'].create({
            'picking_type_ids': [(4, self.picking_type_id)],
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        # Check that Quality Point has been created.
        self.assertTrue(self.quality_point_test, "Quality Point not created.")
        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Check that incoming shipment has been created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")
        # Confirm incoming shipment.
        self.picking_in.action_confirm()
        # Check that Quality Check for incoming shipment has been created.
        self.assertEqual(len(self.picking_in.check_ids), 1)

    def test_05_picking_quality_check_creation_with_product_no_categories(self):

        """ Test Quality Check creation on incoming shipment from a Quality Point
        with products and no product_categories set
        """
        # Create Quality Point for incoming shipment with only a product set.
        self.quality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        # Check that Quality Point has been created.
        self.assertTrue(self.quality_point_test, "Quality Point not created.")
        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with right product.
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with wrong product.
        self.env['stock.move'].create({
            'name': self.product_2.name,
            'product_id': self.product_2.id,
            'product_uom_qty': 2,
            'product_uom': self.product_2.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Check that incoming shipment has been created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")
        # Confirm incoming shipment.
        self.picking_in.action_confirm()
        # Check that only one Quality Check for incoming shipment has been created for the right product.
        self.assertEqual(len(self.picking_in.check_ids), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product.id)), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_2.id)), 0)

    def test_06_picking_quality_check_creation_no_product_with_categories(self):

        """ Test Quality Check creation on incoming shipment from a Quality Point
        with no products and product_categories set
        """
        # Create Quality Point for incoming shipment with only a product_category set.
        self.quality_point_test = self.env['quality.point'].create({
            'product_category_ids': [(4, self.product_category_base.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        # Check that Quality Point has been created.
        self.assertTrue(self.quality_point_test, "Quality Point not created.")
        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with product having right category (child of Quality Point set category).
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with product having wrong category (parent of Quality Point set category).
        self.env['stock.move'].create({
            'name': self.product_2.name,
            'product_id': self.product_2.id,
            'product_uom_qty': 2,
            'product_uom': self.product_2.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Check that incoming shipment has been created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")
        # Confirm incoming shipment.
        self.picking_in.action_confirm()
        # Check that only one Quality Check for incoming shipment has been created for the right category.
        self.assertEqual(len(self.picking_in.check_ids), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product.id)), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_2.id)), 0)

    def test_07_picking_quality_check_creation_with_product_and_categories(self):

        """ Test Quality Check creation on incoming shipment from a Quality Point
        with both products and product_categories set
        """
        # Create Quality Point for incoming shipment with only a product_category set.
        self.quality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product_2.id), (4, self.product_4.id)],
            'product_category_ids': [(4, self.product_category_base.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        # Check that Quality Point has been created.
        self.assertTrue(self.quality_point_test, "Quality Point not created.")
        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with wrong product but having right category (child of Quality Point set category.
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with right product but having wrong category (parent of Quality Point set category).
        self.env['stock.move'].create({
            'name': self.product_2.name,
            'product_id': self.product_2.id,
            'product_uom_qty': 2,
            'product_uom': self.product_2.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with wrong product and having wrong category (parent of Quality Point set category).
        self.env['stock.move'].create({
            'name': self.product_3.name,
            'product_id': self.product_3.id,
            'product_uom_qty': 2,
            'product_uom': self.product_3.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with right product having right category
        self.env['stock.move'].create({
            'name': self.product_4.name,
            'product_id': self.product_4.id,
            'product_uom_qty': 2,
            'product_uom': self.product_4.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Check that incoming shipment has been created.
        self.assertTrue(self.picking_in, "Incoming shipment not created.")
        # Confirm incoming shipment.
        self.picking_in.action_confirm()
        # Check that Quality Check for incoming shipment have been created only for the right product / category.
        self.assertEqual(len(self.picking_in.check_ids), 3)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product.id)), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_2.id)), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_3.id)), 0)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_4.id)), 1)

    def test_08_on_product_creation_with_product_and_categories(self):

        """ Test Quality Check creation on incoming shipment from a Quality Point
        with both products and product_categories set
        """
        # Create Quality Point for incoming shipment with only a product_category set.
        self.quality_point_test = self.env['quality.point'].create({
            'product_ids': [(4, self.product_2.id), (4, self.product_4.id)],
            'product_category_ids': [(4, self.product_category_base.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'move_line',
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        # Create incoming shipment.
        self.picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with wrong product but having right category (child of Quality Point set category.
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with right product but having wrong category (parent of Quality Point set category).
        self.env['stock.move'].create({
            'name': self.product_2.name,
            'product_id': self.product_2.id,
            'product_uom_qty': 2,
            'product_uom': self.product_2.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with wrong product and having wrong category (parent of Quality Point set category).
        self.env['stock.move'].create({
            'name': self.product_3.name,
            'product_id': self.product_3.id,
            'product_uom_qty': 2,
            'product_uom': self.product_3.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Create move with right product having right category
        self.env['stock.move'].create({
            'name': self.product_4.name,
            'product_id': self.product_4.id,
            'product_uom_qty': 2,
            'product_uom': self.product_4.uom_id.id,
            'picking_id': self.picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id
        })
        # Confirm incoming shipment.
        self.picking_in.action_confirm()
        self.picking_in.move_ids.picked = True

        # Check that Quality Check for incoming shipment have been created for all the good move lines
        self.assertEqual(len(self.picking_in.check_ids), 3)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product.id)), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_2.id)), 1)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_3.id)), 0)
        self.assertEqual(len(self.picking_in.check_ids.filtered(lambda c: c.product_id.id == self.product_4.id)), 1)

    def test_09_quality_check_on_operations(self):

        """ Test Quality Check creation of 'operation' type, meaning only one QC will be created per picking.
        """
        # Create Quality Point for incoming shipment with only a product_category set.
        quality_point_operation_type = self.env['quality.point'].create({
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'operation',
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create([{
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'product_uom': product.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        } for product in (self.product, self.product_2)])
        receipt.action_confirm()

        self.assertEqual(len(receipt.check_ids), 1)
        self.assertEqual(receipt.check_ids.point_id, quality_point_operation_type)
        self.assertEqual(receipt.check_ids.picking_id, receipt)

        with self.assertRaises(UserError):
            receipt._action_done()

        receipt.check_ids.do_pass()
        receipt._action_done()

    def test_checks_removal_on_SM_cancellation(self):
        """
        Configuration:
            - 2 storable products P1 and P2
            - Receipt in 2 steps
            - QCP for internal pickings
        Process a first receipt with P1 and P2 (an internal picking and two
        quality checks are created)
        Process a second receipt with P1. The SM input->stock should be merged
        into the existing one and the quality checks should still exist
        """
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        warehouse.reception_steps = 'two_steps'

        p01, p02 = self.env['product.product'].create([{
            'name': name,
            'is_storable': True,
        } for name in ('SuperProduct01', 'SuperProduct02')])

        self.env['quality.point'].create([{
            'product_ids': [(4, product.id)],
            'picking_type_ids': [(4, warehouse.store_type_id.id)],
        } for product in (p01, p02)])

        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
        })
        self.env['stock.move'].create([{
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1,
            'product_uom': product.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.location_id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
        } for product in (p01, p02)])
        receipt.action_confirm()
        receipt.move_ids.quantity = 1
        receipt.button_validate()

        storage_transfer = self.env['stock.picking'].search(
            [('location_id', '=', warehouse.wh_input_stock_loc_id.id), ('picking_type_id', '=', warehouse.store_type_id.id)],
            order='id desc', limit=1)
        self.assertEqual(storage_transfer.check_ids.product_id, p01 + p02)

        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
        })
        self.env['stock.move'].create({
            'name': p01.name,
            'product_id': p01.id,
            'product_uom_qty': 1,
            'product_uom': p01.uom_id.id,
            'picking_id': receipt.id,
            'location_id': self.location_id,
            'location_dest_id': warehouse.wh_input_stock_loc_id.id,
        })
        receipt.action_confirm()
        receipt.move_ids.quantity = 1
        receipt.button_validate()

        self.assertRecordValues(storage_transfer.move_ids, [
            {'product_id': p01.id, 'product_uom_qty': 2},
            {'product_id': p02.id, 'product_uom_qty': 1},
        ])
        self.assertEqual(storage_transfer.check_ids.product_id, p01 + p02)

    def test_propagate_sml_lot_name(self):
        self.env['quality.point'].create({
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'move_line',
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id
        })
        self.product.write({
            'is_storable': True,
            'tracking': 'serial',
        })

        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        move = self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 1,
            'product_uom': self.product.uom_id.id,
            'picking_id': receipt.id,
            'location_id': receipt.location_id.id,
            'location_dest_id': receipt.location_dest_id.id,
        })
        receipt.action_confirm()
        ml = move.move_line_ids

        ml.write({
            'quantity': 1,
            'lot_name': '1457',
        })
        self.assertEqual(ml.check_ids.lot_name, '1457')

        ml.lot_name = '1458'
        self.assertEqual(ml.check_ids.lot_name, '1458')
        # after validation check if lot_id is also propagated
        ml.check_ids.do_pass()
        receipt.button_validate()
        self.assertEqual(ml.check_ids.lot_line_id, ml.lot_id)
        self.assertEqual(ml.check_ids.lot_id, ml.lot_id)

        # Get lot from lot name
        self.assertEqual(ml.check_ids._get_check_action_name(), 'Quality Check : Office Chair - 1.0 Units - 1458')
        ml.lot_name = False
        # Get lot from lot id
        self.assertEqual(ml.check_ids._get_check_action_name(), 'Quality Check : Office Chair - 1.0 Units - 1458')

    def test_update_sml_done_qty(self):
        """
        When changing the done quantity of a SML, the related QC should be
        updated too
        """
        self.env['quality.point'].create({
            'product_ids': [(4, self.product.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'move_line',
        })

        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        move = self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        picking.action_confirm()

        move.quantity = 1.0
        self.assertEqual(picking.check_ids.qty_line, 1)

        move.quantity = 0.0
        self.assertEqual(picking.check_ids.qty_line, 0)

        move.quantity = 2.0
        self.assertEqual(picking.check_ids.qty_line, 2)

    def test_quality_check_with_backorder(self):
        """Test that a user without quality manager access rights can create a backorder"""
        # Create a user wtih stock and quality user rights
        user = self.env['res.users'].create({
            'name': 'Inventory Manager',
            'login': 'test',
            'email': 'test@test.com',
            'groups_id': [(6, 0, [self.env.ref('stock.group_stock_user').id, self.env.ref('quality.group_quality_user').id])]
        })

        self.env['quality.point'].create([{
            'product_ids': [(4, self.product.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'operation',
        }, {
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'move_line',
        }])

        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        move = self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 2,
            'product_uom': self.product.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        picking.action_confirm()
        move.quantity = 1.0
        self.assertEqual(len(picking.check_ids), 2)
        # 'Pass' Quality Checks of shipment.
        for check in picking.check_ids:
            check.do_pass()
        # Validate the picking and create a backorder
        Form.from_action(self.env, picking.button_validate()).save()\
            .with_user(user).process()

        # Check that the backorder is created and in assigned state
        self.assertEqual(picking.state, 'done')
        backorder = picking.backorder_ids
        self.assertEqual(backorder.state, 'assigned')
        self.assertEqual(len(backorder.check_ids), 2)
        # 'Pass' Quality Checks of backorder.
        for check in backorder.check_ids:
            check.do_pass()
        # Validate the backorder
        backorder.move_ids.quantity = 1.0
        backorder.with_user(user).button_validate()
        self.assertEqual(backorder.state, 'done')

    def test_failure_location_move(self):
        """ Quality point per quantity with failure locations list, a picking with 2 products / moves,
            fail one move with qty less than total move qty, a new move with the failing quantity is created,
            moving it to the failure location chosen
        """
        self.env['quality.point'].create({
            'picking_type_ids': [Command.link(self.picking_type_id)],
            'measure_on': 'move_line',
            'test_type_id': self.env.ref('quality_control.test_type_passfail').id,
            'failure_location_ids': [Command.link(self.failure_location.id)],
        })

        (self.product | self.product_2).write({
            'is_storable': True,
        })

        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })

        product_move, product2_move = self.env['stock.move'].create([
            {
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'picking_id': receipt.id,
                'location_id': receipt.location_id.id,
                'location_dest_id': receipt.location_dest_id.id,
            },
            {
                'name': self.product_2.name,
                'product_id': self.product_2.id,
                'product_uom_qty': 2,
                'picking_id': receipt.id,
                'location_id': receipt.location_id.id,
                'location_dest_id': receipt.location_dest_id.id,
            }
        ])
        receipt.action_confirm()
        self.assertEqual(len(receipt.check_ids), 2)
        # open the wizard to do the checks
        action = receipt.check_ids.action_open_quality_check_wizard()
        wizard = self.env[action['res_model']].with_context(action['context']).create({})
        self.assertEqual(len(wizard.check_ids), 2)
        self.assertEqual(wizard.current_check_id.move_line_id, product_move.move_line_ids)
        # pass the first quantity
        action = wizard.do_pass()
        wizard = self.env[action['res_model']].with_context(action['context']).create({})
        self.assertEqual(wizard.current_check_id.move_line_id, product2_move.move_line_ids)
        action = wizard.do_fail()
        wizard = self.env[action['res_model']].with_context(action['context']).browse(action['res_id'])

        self.assertEqual(wizard.qty_failed, 2)
        # only fail one qty of the two
        wizard.qty_failed = 1
        wizard.failure_location_id = self.failure_location.id
        wizard.confirm_fail()
        # there should be 3 moves and 3 checks
        self.assertEqual(len(receipt.move_ids), 3)
        self.assertRecordValues(receipt.check_ids, [
            {'quality_state': 'pass', 'product_id': self.product.id, 'qty_line': 2, 'failure_location_id': False},
            {'quality_state': 'fail', 'product_id': self.product_2.id, 'qty_line': 1, 'failure_location_id': self.failure_location.id},
            {'quality_state': 'pass', 'product_id': self.product_2.id, 'qty_line': 1, 'failure_location_id': False},
        ])

    def test_qp_with_product_ctg(self):
        """
        Test that the quality check is created based on the product category of product and quality point.
        """
        product_cat_2 = self.product_category_base.copy({'name': 'cat2'})
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'categ_id': product_cat_2.id,
        })
        product_b = self.env['product.product'].create({
            'name': 'Product B',
            'is_storable': True,
            'categ_id': self.product_category_base.id,
        })
        self.env['quality.point'].create({
            'title': 'QP1',
            'product_category_ids': [(4, product_cat_2.id), (4, self.product_category_base.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'move_line',
        })
        self.env['quality.point'].create({
            'title': 'QP2',
            'product_category_ids': [(4, self.product_category_base.id)],
            'picking_type_ids': [(4, self.picking_type_id)],
            'measure_on': 'move_line',
        })
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': product_a.id,
            'product_uom_qty': 1,
            'picking_id': picking.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': product_b.id,
            'product_uom_qty': 1,
            'picking_id': picking.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        picking.action_confirm()
        self.assertEqual(len(picking.check_ids), 3)

    def test_qc_with_partial_reception(self):
        """
        Test that the quality check is required only for move lines with quantity set.
        """
        self.env['quality.point'].create({
            'picking_type_ids': [self.picking_type_id],
            'test_type_id': self.env.ref('quality_control.test_type_measure').id,
            'measure_on': 'move_line',
        })
        (self.product_2 | self.product_3).is_storable = True
        self.product_2.tracking = 'serial'
        # Create incoming shipment.
        picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        move_tracked_product = self.env['stock.move'].create({
            'name': self.product_2.name,
            'product_id': self.product_2.id,
            'product_uom_qty': 1,
            'product_uom': self.product_2.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id})
        move_untracked = self.env['stock.move'].create({
            'name': self.product_3.name,
            'product_id': self.product_3.id,
            'product_uom_qty': 1,
            'product_uom': self.product_3.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id})
        # Confirm incoming shipment.
        picking_in.action_confirm()
        # Check Quality Check for incoming shipment is created
        self.assertEqual(len(picking_in.check_ids), 2)
        self.assertTrue(picking_in.quality_check_todo)
        # Set the quantity for the untracked product and complete its quality check.
        move_untracked.quantity = 1
        move_untracked.picked = True
        untracked_check_ids = picking_in.check_ids.filtered(lambda qc: qc.product_id == self.product_3)
        untracked_check_ids.do_pass()
        self.assertEqual(untracked_check_ids.quality_state, 'pass')
        # Update the move line of the tracked product to 0 and
        # ensure that its quality check is not as todo
        move_tracked_product.move_line_ids.quantity = 0
        self.env.invalidate_all()
        self.assertFalse(picking_in.quality_check_todo)
        # Validate incoming shipment.
        res_dict = picking_in.button_validate()
        wizard = Form(self.env[res_dict['res_model']].with_context(res_dict['context'])).save()
        wizard.process()
        backorder = picking_in.backorder_ids
        self.assertEqual(picking_in.state, 'done')
        self.assertEqual(len(backorder.check_ids), 1)
        backorder.check_ids.do_pass()
        self.assertTrue(backorder.check_ids.quality_state, 'pass')

    def test_quality_check_with_scrapped_moves(self):
        """
        Test that a quality check is not created for scrapped moves.
        """
        self.env['quality.point'].create({
            'picking_type_ids': [Command.link(self.picking_type_id)],
            'test_type_id': self.env.ref('quality_control.test_type_measure').id,
            'measure_on': 'operation',
        })
        self.product_3.is_storable = True
        # Create incoming shipment.
        picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        self.env['stock.move'].create({
            'name': self.product_3.name,
            'product_id': self.product_3.id,
            'product_uom_qty': 2,
            'product_uom': self.product_3.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        # Confirm incoming shipment.
        picking_in.action_confirm()
        # Check Quality Check for incoming shipment is created
        self.assertEqual(len(picking_in.check_ids), 1)
        # open the wizard to do the checks
        action = picking_in.check_ids.action_open_quality_check_wizard()
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
        self.assertEqual(len(wizard.check_ids), 1)
        wizard.do_fail()
        self.assertEqual(picking_in.check_ids.quality_state, 'fail')

        scrap = self.env['stock.scrap'].create({
            'picking_id': picking_in.id,
            'product_id': self.product_3.id,
            'product_uom_id': self.product_3.uom_id.id,
            'scrap_qty': 5.0,
        })
        scrap.do_scrap()
        self.assertEqual(len(picking_in.move_ids), 2)
        self.assertEqual(len(picking_in.check_ids), 1)

    def test_qc_by_product_with_partial_reception(self):
        """
        Test that a new quality check is created for the backorder.
        """
        self.env['quality.point'].create({
            'picking_type_ids': [self.picking_type_id],
            'test_type_id': self.env.ref('quality_control.test_type_measure').id,
            'measure_on': 'product',
        })
        picking_in = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id,
            'partner_id': self.partner_id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id,
        })
        move = self.env['stock.move'].create({
            'name': self.product_2.name,
            'product_id': self.product_2.id,
            'product_uom_qty': 10,
            'product_uom': self.product_2.uom_id.id,
            'picking_id': picking_in.id,
            'location_id': self.location_id,
            'location_dest_id': self.location_dest_id})
        picking_in.action_confirm()
        self.assertEqual(len(picking_in.check_ids), 1)
        self.assertTrue(picking_in.quality_check_todo)
        move.quantity = 5
        move.picked = True
        # validate the incoming picking and create a backorder
        action_quality_check = Form.from_action(self.env, picking_in.button_validate()).save().process()
        # Confirm the quality check wizard
        Form.from_action(self.env, action_quality_check).save().do_pass()
        # Check that the first quality check is still linked to the first picking
        self.assertEqual(len(picking_in.check_ids), 1)
        self.assertEqual(picking_in.check_ids.quality_state, 'pass')
        # Make sure that the backorder is correctly created
        backorder = picking_in.backorder_ids
        # Verify that a new quality check is created and linked to the backorder
        self.assertEqual(len(backorder.check_ids), 1)
        backorder.check_ids.do_pass()
        self.assertEqual(backorder.check_ids.quality_state, 'pass')

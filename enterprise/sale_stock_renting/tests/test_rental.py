# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo.fields import Command, Datetime, Date
from odoo.tests import Form, tagged

from odoo.addons.sale_stock_renting.tests.test_rental_common import TestRentalCommon


@tagged('post_install', '-at_install')
class TestRentalWizard(TestRentalCommon):

    def test_unavailable_qty_only_considers_active_rentals(self):
        self._set_product_quantity(10)
        from_date = Datetime.now() + relativedelta(days=1)
        to_date = Datetime.now() + relativedelta(days=5)
        # Ends before interval
        self._create_so_with_sol(
            rental_start_date=from_date - relativedelta(days=2),
            rental_return_date=from_date - relativedelta(days=1),
            product_uom_qty=1,
        )
        # Starts after interval
        self._create_so_with_sol(
            rental_start_date=to_date + relativedelta(days=1),
            rental_return_date=to_date + relativedelta(days=2),
            product_uom_qty=1,
        )
        # Ends during interval
        self._create_so_with_sol(
            rental_start_date=from_date - relativedelta(days=1),
            rental_return_date=to_date - relativedelta(days=1),
            product_uom_qty=1,
        )
        # Starts during interval
        self._create_so_with_sol(
            rental_start_date=from_date + relativedelta(days=1),
            rental_return_date=to_date + relativedelta(days=1),
            product_uom_qty=1,
        )
        # Covers interval
        self._create_so_with_sol(
            rental_start_date=from_date - relativedelta(days=1),
            rental_return_date=to_date + relativedelta(days=1),
            product_uom_qty=1,
        )
        # Doesn't increase unavailable.
        self._create_so_with_sol(
            rental_start_date=to_date - relativedelta(days=1),
            rental_return_date=to_date,
            product_uom_qty=1,
        )

        self.assertEqual(self.product_id._get_unavailable_qty(from_date, to_date), 3)

    def test_unavailable_qty_with_to_date_exclude_pickup_at_to_date(self):
        self._set_product_quantity(10)
        from_date = Datetime.now() + relativedelta(days=1)
        to_date = Datetime.now() + relativedelta(days=5)
        # Starts at to_date
        self._create_so_with_sol(
            rental_start_date=to_date,
            rental_return_date=to_date + relativedelta(days=1),
            product_uom_qty=1,
        )

        self.assertEqual(self.product_id._get_unavailable_qty(from_date, to_date), 0)

    def test_unavailable_qty_without_to_date_include_pickup_at_from_date(self):
        self._set_product_quantity(10)
        from_date = Datetime.now() + relativedelta(days=1)
        # Starts at from_date == to_date
        self._create_so_with_sol(
            rental_start_date=from_date,
            rental_return_date=from_date + relativedelta(days=1),
            product_uom_qty=1,
        )

        self.assertEqual(self.product_id._get_unavailable_qty(from_date), 1)

    def test_unavailable_qty_early_pickup(self):
        self._set_product_quantity(10)
        from_date = Datetime.now() + relativedelta(days=1)
        to_date = Datetime.now() + relativedelta(days=5)
        # Starts after interval
        so = self._create_so_with_sol(
            rental_start_date=to_date + relativedelta(days=1),
            rental_return_date=to_date + relativedelta(days=2),
            product_uom_qty=1,
        )
        self._pickup_so(so)

        self.assertEqual(self.product_id._get_unavailable_qty(from_date, to_date), 1)

    def test_unavailable_qty_early_return(self):
        self._set_product_quantity(10)
        from_date = Datetime.now() + relativedelta(days=1)
        to_date = Datetime.now() + relativedelta(days=5)
        # Ends during interval
        so = self._create_so_with_sol(
            rental_start_date=from_date - relativedelta(days=1),
            rental_return_date=to_date - relativedelta(days=1),
            product_uom_qty=1,
        )
        self._pickup_so(so)
        self._return_so(so)

        self.assertEqual(self.product_id._get_unavailable_qty(from_date, to_date), 0)

    def test_unavailable_lots_only_considers_active_rentals(self):
        self._set_product_quantity(10)
        from_date = Datetime.now() + relativedelta(days=1)
        to_date = Datetime.now() + relativedelta(days=5)
        lot1, lot2, lot3, lot4 = self.env['stock.lot'].create([{
            'product_id': self.tracked_product_id.id,
            'company_id': self.env.company.id,
        } for _i in range(4)])

        # Active
        self._create_so_with_sol(
            rental_start_date=from_date,
            rental_return_date=to_date,
            product_uom_qty=1,
            pickedup_lot_ids=[Command.set([lot1.id, lot2.id])],
            returned_lot_ids=[Command.set([lot2.id])],
            reserved_lot_ids=[Command.set([lot3.id])],
        )
        # Inactive
        self._create_so_with_sol(
            rental_start_date=to_date + relativedelta(days=1),
            rental_return_date=to_date + relativedelta(days=2),
            product_uom_qty=1,
            pickedup_lot_ids=[Command.set([lot4.id])],
        )

        self.assertEqual(self.product_id._get_unavailable_lots(from_date, to_date), lot1 + lot3)

    def test_rental_product_flow(self):

        self.assertEqual(
            self.product_id.qty_available,
            4
        )

        self.order_line_id1.write({
            'product_uom_qty': 3
        })

        """
            Total Pickup
        """

        self.order_line_id1.write({
            'qty_delivered': 3
        })

        """ In sale order warehouse """
        self.assertEqual(
            self.product_id.with_context(
                warehouse_id=self.order_line_id1.order_id.warehouse_id.id,
                from_date=self.order_line_id1.reservation_begin,
                to_date=self.order_line_id1.return_date,
            ).qty_available,
            1
        )

        self.env.invalidate_all()
        """ In company internal rental location (in stock valuation but not in available qty) """
        self.assertEqual(
            self.product_id.with_context(
                location=self.env.company.rental_loc_id.id,
                from_date=self.order_line_id1.start_date,
                to_date=self.order_line_id1.return_date,
            ).qty_available,
            3
        )

        """ In company warehouses """
        self.assertEqual(
            self.product_id.qty_available,
            1
        )

        """ In company stock valuation """
        self.assertEqual(
            self.product_id.quantity_svl,
            4
        )

        ####################################
        # Cancel deliver then re-apply
        ####################################

        self.order_line_id1.write({'qty_delivered': 0})
        self.assertEqual(self.product_id.qty_available, 4)
        self.order_line_id1.write({'qty_delivered': 3})

        """
            Partial Return
        """

        self.order_line_id1.write({
            'qty_returned': 2
        })

        """ In sale order warehouse """
        self.assertEqual(
            self.product_id.with_context(
                warehouse_id=self.order_line_id1.order_id.warehouse_id.id
            ).qty_available,
            3
        )

        """ In company internal rental location (in stock valuation but not in available qty) """
        self.assertEqual(
            self.product_id.with_context(
                location=self.env.company.rental_loc_id.id,
                from_date=self.order_line_id1.start_date,
                to_date=self.order_line_id1.return_date,
            ).qty_available,
            1
        )

        """ In company warehouses """
        self.assertEqual(
            self.product_id.qty_available,
            3
        )

        """ In company stock valuation """
        self.assertEqual(
            self.product_id.quantity_svl,
            4
        )

        """
            Total Return
        """

        self.order_line_id1.write({
            'qty_returned': 3
        })

        self.assertEqual(
            self.product_id.qty_available,
            4.0
        )

    def test_rental_lot_flow(self):
        self.lots_rental_order.action_confirm()

        lots = self.env['stock.lot'].search([('product_id', '=', self.tracked_product_id.id)])
        rentable_lots = self.env['stock.lot']._get_available_lots(self.tracked_product_id)
        self.assertEqual(set(lots.ids), set(rentable_lots.ids))  # set is here to ensure that order wont break test

        self.order_line_id2.reserved_lot_ids += self.lot_id1
        self.order_line_id2.product_uom_qty = 1.0

        self.order_line_id2.pickedup_lot_ids += self.lot_id2

        # Ensure lots are unreserved if other lots are picked up in their place
        # and qty pickedup = product_uom_qty (qty reserved)
        self.assertEqual(self.order_line_id2.reserved_lot_ids, self.order_line_id2.pickedup_lot_ids)

    def test_rental_lot_concurrent(self):
        """The purpose of this test is to mimmic a concurrent picking of a rental product.
        As the same lot is applied to the sol twice, its qty_delivered should be 1.
        """
        so = self.lots_rental_order
        sol = self.order_line_id2
        lot = self.lot_id2

        sol.product_uom_qty = 1.0
        so.action_confirm()

        wizard_vals = so.action_open_pickup()
        for _i in range(2):
            wizard = self.env[wizard_vals['res_model']].with_context(wizard_vals['context']).create({
                'rental_wizard_line_ids': [
                    (0, 0, {
                        'order_line_id': sol.id,
                        'product_id': sol.product_id.id,
                        'qty_delivered': 1.0,
                        'pickedup_lot_ids':[Command.set([lot.id])],
                    })
                ]
            })
            wizard.apply()

        self.assertEqual(sol.qty_delivered, len(sol.pickedup_lot_ids), "The quantity delivered should not exceed the number of picked up lots")

        for _i in range(2):
            wizard = self.env[wizard_vals['res_model']].with_context(wizard_vals['context']).create({
                'rental_wizard_line_ids': [
                    (0, 0, {
                        'order_line_id': sol.id,
                        'product_id': sol.product_id.id,
                        'qty_returned': 1.0,
                        'returned_lot_ids':[Command.set([lot.id])],
                    })
                ]
            })
            wizard.apply()

        self.assertEqual(sol.qty_returned, len(sol.returned_lot_ids), "The quantity returned should not exceed the number of returned lots")

    def test_schedule_report(self):
        """Verify sql scheduling view consistency.

        One sale.order.line with 3 different lots (reserved/pickedup/returned)
        is represented by 3 sale.rental.schedule to allow grouping reservation information
        by stock.lot .

        Note that a lot can be pickedup (sol.pickedup_lot_ids) even if not reserved (sol.reserved_lot_ids).
        """
        self.order_line_id2.reserved_lot_ids = self.lot_id1
        # Avoid magic setting pickedup lots as reserved when full quantity has been pickedup
        self.order_line_id2.product_uom_qty = 2.0

        # Lot pickedup but not reserved.
        self.order_line_id2.pickedup_lot_ids = self.lot_id2

        self.assertEqual(
            self.env["sale.rental.schedule"].search_count([('lot_id', '=', self.lot_id2.id)]),
            1,
        )
        scheduling_recs = self.env["sale.rental.schedule"].search([
            ('order_line_id', '=', self.order_line_id2.id),
        ])
        self.assertEqual(
            len(scheduling_recs),
            2, # 1 reserved, 1 pickedup
        )
        self.assertEqual(
            scheduling_recs.mapped('report_line_status'),
            ["reserved", "pickedup"],
        )

        # More generic behavior:
        # 2 reserved, 2 pickedup, 1 returned
        self.order_line_id2.returned_lot_ids = self.lot_id2
        self.order_line_id2.pickedup_lot_ids += self.lot_id1
        self.env.invalidate_all()
        scheduling_recs = self.env["sale.rental.schedule"].search([
            ('order_line_id', '=', self.order_line_id2.id)
        ])
        self.assertEqual(
            len(scheduling_recs),
            2,
        )
        self.assertEqual(
            scheduling_recs.lot_id,
            self.lot_id1 + self.lot_id2,
        )
        self.assertEqual(
            scheduling_recs.mapped('report_line_status'),
            ["pickedup", "returned"],
        )

    def test_lot_accuracy_in_schedule(self):
        """ Schedule should only display lots that are associated with
        rental order lines
        """
        self.env['res.company'].create_missing_rental_location()
        if self.env['ir.module.module'].search([('name', '=', 'purchase_stock'), ('state', '=', 'installed')], limit=1):
            self.env.user._get_default_warehouse_id().buy_to_resupply = False

        rental_schedule = self.env['sale.rental.schedule']
        rental_transfers_group = self.env.ref('sale_stock_renting.group_rental_stock_picking')
        self.env.user.groups_id = [(4, rental_transfers_group.id)]
        so = self.lots_rental_order
        self.order_line_id2.product_uom_qty = 1.0
        so.order_line = [(6, 0, self.order_line_id2.id)]
        so.action_confirm()

        # Rental schedule should have 1 out of the 3 total lots for `self.tracked_product_id`
        self.assertEqual(
            rental_schedule.search_count([('product_id', '=', self.tracked_product_id.id)]),
            1
        )

    ###############################
    #       PRIVATE METHODS       #
    ###############################

    def _set_product_quantity(self, quantity):
        quant = self.env['stock.quant'].create({
            'product_id': self.product_id.id,
            'inventory_quantity': quantity,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id
        })
        quant.action_apply_inventory()

    def _create_so_with_sol(self, rental_start_date, rental_return_date, **sol_values):
        so = self.env['sale.order'].with_context(in_rental_app=True).create({
            'partner_id': self.cust1.id,
            'rental_start_date': rental_start_date,
            'rental_return_date': rental_return_date,
            'order_line': [
                Command.create({
                    'product_id': self.product_id.id,
                    **sol_values,
                })
            ]
        })
        so.action_confirm()
        return so

    def _pickup_so(self, so):
        pickup_action = so.action_open_pickup()
        Form(self.env['rental.order.wizard'].with_context(pickup_action['context'])).save().apply()

    def _return_so(self, so):
        return_action = so.action_open_return()
        Form(self.env['rental.order.wizard'].with_context(return_action['context'])).save().apply()


class TestRentalPicking(TestRentalCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['res.config.settings'].create({'group_rental_stock_picking': True}).execute()

    def test_flow_1(self):
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 3, 'is_rental': True})
        rental_order_1.rental_start_date = self.rental_start_date
        rental_order_1.rental_return_date = self.rental_return_date
        rental_order_1.action_confirm()
        outgoing_picking = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming')
        self.assertEqual(len(rental_order_1.picking_ids), 2)
        self.assertEqual(incoming_picking.return_id.id, outgoing_picking.id, "The return picking should be the return of the delivery picking")
        self.assertEqual([d.date() for d in (outgoing_picking | incoming_picking).mapped('scheduled_date')],
                         [rental_order_1.rental_start_date.date(), rental_order_1.rental_return_date.date()])
        self.assertEqual(rental_order_1.picking_ids.move_ids.mapped('product_uom_qty'), [3.0, 3.0])

        outgoing_picking = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming')

        outgoing_picking.move_ids.quantity = 2
        Form.from_action(self.env, outgoing_picking.button_validate()).save().process()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 2)
        self.assertEqual(rental_order_1.rental_status, 'pickup')
        self.assertEqual(len(rental_order_1.picking_ids), 3)
        self.assertEqual(incoming_picking.move_ids.quantity, 2)

        incoming_picking.move_ids.quantity = 1
        Form.from_action(self.env, incoming_picking.button_validate()).save().process()
        self.assertEqual(rental_order_1.order_line.qty_returned, 1)
        self.assertEqual(rental_order_1.rental_status, 'pickup')
        self.assertEqual(len(rental_order_1.picking_ids), 4)

        outgoing_picking_2 = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing' and p.state == 'assigned')
        incoming_picking_2 = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming' and p.state == 'assigned')
        self.assertEqual(outgoing_picking_2.scheduled_date.date(), rental_order_1.rental_start_date.date())
        self.assertEqual(incoming_picking_2.scheduled_date.date(), rental_order_1.rental_return_date.date())
        self.assertEqual(outgoing_picking_2.move_ids.quantity, 1)
        self.assertEqual(incoming_picking_2.move_ids.quantity, 1)

        rental_order_1.order_line.write({'product_uom_qty': 5})
        self.assertEqual(outgoing_picking_2.move_ids.product_uom_qty, 3)
        self.assertEqual(incoming_picking_2.move_ids.product_uom_qty, 4)

        outgoing_picking_2.move_ids.quantity = 1
        Form.from_action(self.env, outgoing_picking_2.button_validate()).save().process()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 3)
        self.assertEqual(rental_order_1.rental_status, 'pickup')
        self.assertEqual(len(rental_order_1.picking_ids), 5)
        self.assertEqual(incoming_picking_2.move_ids.quantity, 2)

        rental_order_1.order_line.write({'product_uom_qty': 4})
        outgoing_picking_3 = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing' and p.state == 'assigned')
        self.assertEqual(outgoing_picking_3.scheduled_date.date(), rental_order_1.rental_start_date.date())
        self.assertEqual(outgoing_picking_3.move_ids.product_uom_qty, 1)
        self.assertEqual(incoming_picking_2.move_ids.product_uom_qty, 3)

        outgoing_picking_3.button_validate()
        self.assertEqual(incoming_picking_2.move_ids.quantity, 3)
        self.assertEqual(rental_order_1.order_line.qty_delivered, 4)
        self.assertEqual(rental_order_1.rental_status, 'return')

        incoming_picking_2.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_returned, 4)
        self.assertEqual(rental_order_1.rental_status, 'returned')

    def test_flow_multisteps(self):
        self.warehouse_id.delivery_steps = 'pick_pack_ship'
        self.warehouse_id.reception_steps = 'three_steps'

        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 3, 'is_rental': True})
        rental_order_1.rental_start_date = self.rental_start_date
        rental_order_1.rental_return_date = self.rental_return_date
        rental_order_1.action_confirm()
        self.assertEqual(len(rental_order_1.picking_ids), 2)
        self.assertEqual([d.date() for d in rental_order_1.picking_ids.mapped('scheduled_date')],
                         [rental_order_1.rental_start_date.date(), rental_order_1.rental_return_date.date()])
        self.assertEqual(rental_order_1.picking_ids.move_ids.mapped('product_uom_qty'), [3.0, 3.0])

        rental_order_1.order_line.write({'product_uom_qty': 4})
        self.assertEqual(len(rental_order_1.picking_ids), 2)
        self.assertEqual(rental_order_1.picking_ids.move_ids.mapped('product_uom_qty'), [4.0, 4.0])

        pick_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(pick_picking.location_dest_id, self.warehouse_id.wh_pack_stock_loc_id)
        pick_picking.button_validate()
        rental_order_1.order_line.write({'product_uom_qty': 1})
        self.assertEqual(len(rental_order_1.picking_ids), 4)

        return_pick_picking = rental_order_1.picking_ids.filtered(lambda p: p.location_id == self.warehouse_id.wh_pack_stock_loc_id and p.location_dest_id == self.warehouse_id.lot_stock_id)
        all_other_pickings = rental_order_1.picking_ids.filtered(lambda p: p.state != 'done' and p.id != return_pick_picking.id)
        self.assertEqual(return_pick_picking.move_ids.product_uom_qty, 3.0)
        self.assertEqual(return_pick_picking.state, 'assigned')
        self.assertEqual(all_other_pickings.move_ids.mapped('product_uom_qty'), [1.0, 1.0])

        return_pick_picking.move_ids.picked = True
        return_pick_picking.button_validate()
        self.assertEqual(return_pick_picking.state, 'done')

        pack_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        pack_picking.move_ids.quantity = 1
        pack_picking.move_ids.picked = True
        self.assertEqual(pack_picking.location_dest_id, self.warehouse_id.wh_output_stock_loc_id)
        pack_picking.with_context(skip_backorder=True, picking_ids_not_to_backorder=pack_picking.ids).button_validate()

        out_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(out_picking.move_ids.location_dest_id, self.env.company.rental_loc_id)
        out_picking.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 1)

        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(incoming_picking.location_dest_id, self.warehouse_id.wh_input_stock_loc_id)
        incoming_picking.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_returned, 1)

        qc_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(qc_picking.location_dest_id, self.warehouse_id.wh_qc_stock_loc_id)
        qc_picking.button_validate()

        final_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(final_picking.location_dest_id, self.warehouse_id.lot_stock_id)
        final_picking.button_validate()

    def test_flow_serial(self):
        empty_lot = self.env['stock.lot'].create({
            'product_id': self.tracked_product_id.id,
            'name': "Dofus Ocre",
            'company_id': self.env.company.id,
        })
        available_lot = self.env['stock.lot'].create({
            'product_id': self.tracked_product_id.id,
            'name': "Dofawa",
            'company_id': self.env.company.id,
        })
        available_quant = self.env['stock.quant'].create({
            'product_id': self.tracked_product_id.id,
            'inventory_quantity': 1.0,
            'lot_id': available_lot.id,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id
        })
        reserved_lot = self.env['stock.lot'].create({
            'product_id': self.tracked_product_id.id,
            'name': "Dolmanax",
            'company_id': self.env.company.id,
        })
        reserved_quant = self.env['stock.quant'].create({
            'product_id': self.tracked_product_id.id,
            'inventory_quantity': 1.0,
            'lot_id': reserved_lot.id,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id
        })
        (available_quant + reserved_quant).action_apply_inventory()

        # Reserve 1 serial
        reserved_rental = self.sale_order_id.copy()
        reserved_rental.order_line.write({'product_id': self.tracked_product_id.id, 'reserved_lot_ids': reserved_lot, 'product_uom_qty': 1})
        reserved_rental.order_line.is_rental = True
        reserved_rental.rental_start_date = self.rental_start_date
        reserved_rental.rental_return_date = self.rental_return_date
        reserved_rental.action_confirm()

        # Test with 3 serials: 1 available, 1 reserved and 1 empty
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({
            'product_id': self.tracked_product_id.id,
            'reserved_lot_ids': [Command.set((available_lot + reserved_lot + empty_lot).ids)],
            'product_uom_qty': 3,
        })
        rental_order_1.order_line.is_rental = True
        rental_order_1.rental_start_date = self.rental_start_date
        rental_order_1.rental_return_date = self.rental_return_date
        rental_order_1.action_confirm()
        self.assertEqual(len(rental_order_1.picking_ids), 2)

        outgoing_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(len(outgoing_picking.move_ids.move_line_ids), 3)
        self.assertEqual(outgoing_picking.move_ids.move_line_ids.lot_id, self.lot_id2 + self.lot_id3 + available_lot)

        outgoing_picking.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 3)
        self.assertEqual(available_lot.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.env.company.rental_loc_id)
        self.assertEqual(self.lot_id2.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.env.company.rental_loc_id)
        self.assertEqual(self.lot_id3.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.env.company.rental_loc_id)

        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(len(incoming_picking.move_ids.move_line_ids), 3)
        self.assertEqual(incoming_picking.move_ids.move_line_ids.lot_id, self.lot_id2 + self.lot_id3 + available_lot)

        incoming_picking.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_returned, 3)
        self.assertEqual(available_lot.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.warehouse_id.lot_stock_id)
        self.assertEqual(self.lot_id2.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.warehouse_id.lot_stock_id)
        self.assertEqual(self.lot_id3.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.warehouse_id.lot_stock_id)

    def test_late_fee(self):
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 1, 'is_rental': True})
        rental_order_1.rental_start_date = Datetime.now() - timedelta(days=7)
        rental_order_1.rental_return_date = Datetime.now() - timedelta(days=3)
        rental_order_1.action_confirm()

        outgoing_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(outgoing_picking.scheduled_date.date(), rental_order_1.rental_start_date.date())
        outgoing_picking.button_validate()

        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(incoming_picking.scheduled_date.date(), rental_order_1.rental_return_date.date())
        incoming_picking.button_validate()

        self.assertEqual(len(rental_order_1.order_line), 2)
        late_fee_order_line = rental_order_1.order_line.filtered(lambda l: l.product_id.type == 'service')
        self.assertEqual(late_fee_order_line.price_unit, 30)

    def test_buttons(self):
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 3, 'is_rental': True})
        rental_order_1.action_confirm()
        picking_out = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
        picking_in = rental_order_1.picking_ids - picking_out
        action_open_pickup = rental_order_1.action_open_pickup()
        action_open_return = rental_order_1.action_open_return()
        self.assertEqual(action_open_pickup.get('res_id'), picking_out.id)
        self.assertEqual(action_open_pickup.get('domain'), '')
        self.assertEqual(action_open_pickup.get('xml_id'), 'stock.action_picking_tree_all')
        self.assertEqual(action_open_return.get('res_id'), 0)
        self.assertEqual(action_open_return.get('domain'), [('id', 'in', rental_order_1.picking_ids.ids)])
        self.assertEqual(action_open_return.get('xml_id'), 'stock.action_picking_tree_all')

        ready_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        ready_picking.button_validate()
        self.assertEqual(rental_order_1.rental_status, 'return')
        action_open_return_2 = rental_order_1.action_open_return()
        self.assertEqual(action_open_return_2.get('res_id'), picking_in.id)
        self.assertEqual(action_open_return_2.get('domain'), '')
        self.assertEqual(action_open_return_2.get('xml_id'), 'stock.action_picking_tree_all')

    def test_create_rental_transfers(self):
        """ E.g., a public/portal user signs & pays for an order via the portal
        """
        public_user = self.env.ref('base.public_user')
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 1, 'is_rental': True})
        rental_order_1.with_user(public_user).sudo().action_confirm()
        self.assertTrue(rental_order_1.picking_ids)

    def test_reordering_rule_forecast(self):
        """ Test the rental orders will only consider outgoing rental move in the forecast
        computation. """
        # Set a fixed visibility_days
        self.product_id.stock_quant_ids.sudo().unlink()
        date = Date.today() + timedelta(days=7)

        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 1, 'is_rental': True})
        rental_order_1.rental_start_date = Datetime.now() + timedelta(days=2)
        rental_order_2 = self.sale_order_id.copy()
        rental_order_2.order_line.write({'product_uom_qty': 2, 'is_rental': True})
        rental_order_2.rental_start_date = Datetime.now() + timedelta(days=4)
        rental_order_2.rental_return_date = Datetime.now() + timedelta(days=5)
        self.assertEqual(self.product_id.with_context(date=date).qty_available, 0)
        (rental_order_1 | rental_order_2).action_confirm()
        self.env['stock.warehouse.orderpoint'].with_context(global_visibility_days=7).action_open_orderpoints()
        self.assertEqual(self.product_id.orderpoint_ids.with_context(global_visibility_days=7).lead_days_date, date)
        self.assertEqual(self.product_id.orderpoint_ids.with_context(global_visibility_days=7).qty_forecast, -2)

    def test_rental_available_reserved_lots(self):
        """
            The aim is to check if the `available_reserved_lots` compute
            field correctly determines whether a batch we want to reserve
            will be available or not.
        """
        # Create a sale order to reserve a lot.
        sale_order_id1 = self.env['sale.order'].create({
            'partner_id': self.cust1.id,
            'rental_start_date': Datetime.today() + timedelta(days=3),
            'rental_return_date': Datetime.today() + timedelta(days=4),
        })
        order_line_id1 = self.env['sale.order.line'].create({
            'order_id': sale_order_id1.id,
            'product_id': self.tracked_product_id.id,
            'reserved_lot_ids': [Command.set(self.lot_id1.ids)],
            'product_uom_qty': 1.0,
        })
        order_line_id1.update({'is_rental': True})
        sale_order_id1.action_confirm()

        # Create a second sale order and modify reserved lots, start date
        # and return date to check if `available_reserved_lots` is correct.
        sale_order_id = self.env['sale.order'].create({
            'partner_id': self.cust1.id,
            'rental_start_date': Datetime.today() + timedelta(days=3),
            'rental_return_date': Datetime.today() + timedelta(days=4),
        })
        order_line_id = self.env['sale.order.line'].create({
            'order_id': sale_order_id.id,
            'product_id': self.tracked_product_id.id,
            'product_uom_qty': 1.0,
        })
        order_line_id.update({'is_rental': True})

        self.assertEqual(order_line_id.available_reserved_lots, True)
        order_line_id.reserved_lot_ids = self.lot_id2
        self.assertEqual(order_line_id.available_reserved_lots, True)
        order_line_id.reserved_lot_ids += self.lot_id1
        self.assertEqual(order_line_id.available_reserved_lots, False)
        sale_order_id.write({
            'rental_start_date': Datetime.today() + timedelta(days=1),
            'rental_return_date': Datetime.today() + timedelta(days=2),
        })
        self.assertEqual(order_line_id.available_reserved_lots, True)
        sale_order_id.write({
            'rental_start_date': Datetime.today() + timedelta(days=5),
            'rental_return_date': Datetime.today() + timedelta(days=6),
        })
        # will return in stock in time
        self.assertEqual(order_line_id.available_reserved_lots, True)

        # Validate the delivery of the first order to test the flow
        # when the product is not in stock
        delivery = sale_order_id1.picking_ids.filtered(lambda p: p.picking_type_id == self.warehouse_id.out_type_id)
        delivery.button_validate()
        self.assertEqual(delivery.state, 'done')
        self.assertEqual(delivery.move_ids.lot_ids, self.lot_id1)
        self.assertEqual(order_line_id1.available_reserved_lots, True)
        sale_order_id.write({
            'rental_start_date': Datetime.today() + timedelta(days=3),
            'rental_return_date': Datetime.today() + timedelta(days=4),
        })
        order_line_id.reserved_lot_ids = self.lot_id2
        self.assertEqual(order_line_id.available_reserved_lots, True)
        order_line_id.reserved_lot_ids += self.lot_id1
        self.assertEqual(order_line_id.available_reserved_lots, False)
        sale_order_id.write({
            'rental_start_date': Datetime.today() + timedelta(days=1),
            'rental_return_date': Datetime.today() + timedelta(days=2),
        })
        self.assertEqual(order_line_id.available_reserved_lots, False)
        sale_order_id.write({
            'rental_start_date': Datetime.today() + timedelta(days=5),
            'rental_return_date': Datetime.today() + timedelta(days=6),
        })
        self.assertEqual(order_line_id.available_reserved_lots, True)

    def test_disable_rental_transfer(self):
        """
        Check that the rental transfers setting can be disabled
        """
        warehouse_rental_route = self.env.ref('sale_stock_renting.route_rental')
        self.env['res.config.settings'].write({
            "group_rental_stock_picking": True,
        })
        rental_stock_rules = warehouse_rental_route.rule_ids
        rental_order = self.sale_order_id.copy()
        rental_order.order_line.write({'product_uom_qty': 3, 'is_rental': True})
        rental_order.action_confirm()
        picking_out = rental_order.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
        picking_in = rental_order.picking_ids - picking_out
        self.assertEqual([len(picking_out), len(picking_in)], [1, 1])
        picking_out.button_validate()
        self.assertRecordValues(picking_out.move_ids, [{'state': 'done', 'quantity': 3.0}])
        picking_in.button_validate()
        self.assertRecordValues(picking_in.move_ids, [{'state': 'done', 'quantity': 3.0}])
        # disable the setting
        self.env.user.groups_id -= self.env.ref('sale_stock_renting.group_rental_stock_picking')
        settings = self.env['res.config.settings'].with_user(self.env.user).create({})
        settings.group_rental_stock_picking = False
        settings.set_values()
        # check that the rules of the rental route have been updated
        self.assertFalse(rental_stock_rules & warehouse_rental_route.rule_ids)

    def test_multi_step_route_revised_order_correct_transfer_amount(self):
        """ Ensure correct quantities are encoded on stock moves for rental transfers when an order
        gets revised and a multi-step route is used whose pick action sources product from a child
        location of lot_stock.
        """
        product = self.product_id
        warehouse = self.warehouse_id
        warehouse.delivery_steps = 'pick_ship'
        store_location = self.env['stock.location'].create({
            'name': 'storage location',
            'usage': 'internal',
            'location_id': warehouse.lot_stock_id.id,
        })
        warehouse.route_ids.filtered(
            lambda r: '2 steps' in r.name).rule_ids.filtered(
            lambda r: r.location_src_id == warehouse.lot_stock_id
        ).location_src_id = store_location.id

        rental_order = self.env['sale.order'].create({
            'is_rental_order': True,
            'partner_id': self.cust1.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_uom_qty': 1,
                'is_rental': True,
            })],
        })
        rental_order.action_confirm()
        rental_order.order_line[0].product_uom_qty = 2
        self.assertEqual(
            rental_order.picking_ids.move_ids.mapped('product_uom_qty'),
            [rental_order.order_line.product_uom_qty] * len(rental_order.picking_ids.move_ids)
        )

    def test_rental_transfer_custom_route(self):
        """
        Check that custom rental routes are used if set on the orde line.
        """
        # Enable rental transfers -> nrachive rental route
        self.env['res.config.settings'].write({
            "group_rental_stock_picking": True,
        })
        warehouse = self.warehouse_id
        warehouse_rental_route = self.env.ref('sale_stock_renting.route_rental')
        custom_rental_route = warehouse_rental_route.copy()
        custom_rental_route.sale_selectable = True
        custom_location = self.env['stock.location'].create({
            'name': 'Lovely location',
            'location_id': warehouse.lot_stock_id.id,
        })
        self.env['stock.rule'].create({
                'name': 'Custom rental delivery',
                'route_id': custom_rental_route.id,
                'location_dest_id': warehouse.company_id.rental_loc_id.id,
                'location_src_id': custom_location.id,
                'action': 'pull',
                'procure_method': 'make_to_stock',
                'picking_type_id': warehouse.out_type_id.id,
            })
        rental_order = self.sale_order_id.copy()
        rental_order.order_line.product_id.rent_ok = True
        rental_order.order_line.write({'product_uom_qty': 1, 'is_rental': True, 'route_id': custom_rental_route.id})
        rental_order.action_confirm()
        picking_out = rental_order.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
        picking_in = rental_order.picking_ids - picking_out
        self.assertEqual([len(picking_out), len(picking_in)], [1, 1])
        self.assertRecordValues(picking_out.move_ids, [{
            'location_id': custom_location.id,
            'location_dest_id': warehouse.company_id.rental_loc_id.id,
            'route_ids': custom_rental_route.ids,
        }])
        self.assertRecordValues(picking_in.move_ids, [{
            'location_id': warehouse.company_id.rental_loc_id.id,
            'location_dest_id': warehouse.lot_stock_id.id,
            'route_ids': custom_rental_route.ids,
        }])

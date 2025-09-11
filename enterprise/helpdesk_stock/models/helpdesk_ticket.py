# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
from odoo import api, fields, models, _


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    product_id = fields.Many2one('product.product', string='Product', tracking=True,
        check_company=True,
        domain="[('sale_ok', '=', True), ('id', 'in', suitable_product_ids)]",
        help="Product this ticket is about. If selected, only the sales orders, deliveries and invoices including this product will be visible.")
    suitable_product_ids = fields.Many2many(
        'product.product',
        compute='_compute_suitable_product_ids',
        export_string_translation=False,
        groups="stock.group_stock_user",
    )
    has_partner_picking = fields.Boolean(compute='_compute_suitable_product_ids')
    tracking = fields.Selection(related='product_id.tracking')
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial Number', domain="[('product_id', '=', product_id)]", tracking=True)
    pickings_count = fields.Integer('Return Orders Count', compute="_compute_pickings_count")
    picking_ids = fields.Many2many('stock.picking', string="Return Orders", copy=False)

    @api.depends('partner_id')
    def _compute_suitable_product_ids(self):
        suitable_partner_ids = self.env['res.partner'].search([('commercial_partner_id', 'in', self.commercial_partner_id.ids)]).ids

        sale_data = self.env['sale.order.line']._read_group([
            ('product_id', '!=', False),
            ('order_id.state', '=', 'sale'),
            ('order_partner_id', 'in', suitable_partner_ids)
        ], ['order_partner_id'], ['product_id:array_agg'])
        order_data = {order_partner.id: product_ids for order_partner, product_ids in sale_data}

        picking_data = self.env['stock.picking']._read_group([
            ('state', '=', 'done'),
            ('partner_id', 'in', suitable_partner_ids),
            ('picking_type_code', '=', 'outgoing'),
        ], ['partner_id'], ['id:array_agg'])

        # it was not correct, it took only products of stock_move_line from the first partner_id of self
        picking_ids = [id_ for __, ids in picking_data for id_ in ids]
        outgoing_product = {}
        if picking_ids:
            move_line_data = self.env['stock.move.line']._read_group([
                ('state', '=', 'done'),
                ('picking_id', 'in', picking_ids),
                ('picking_code', '=', 'outgoing'),
            ], ['picking_id'], ['product_id:array_agg'])
            move_lines = {picking.id: product_ids for picking, product_ids in move_line_data}
            if move_lines:
                for partner, picking_ids in picking_data:
                    product_lists = [move_lines[pick] for pick in picking_ids if pick in move_lines]
                    outgoing_product[partner.id] = list(itertools.chain(*product_lists))
        partners_in_sale = dict(zip(order_data.keys(), self.env['res.partner'].browse(order_data.keys())))

        for ticket in self:
            product_ids = {item for partner_id in suitable_partner_ids for item in order_data.get(partner_id, []) + outgoing_product.get(partner_id, [])}
            ticket.suitable_product_ids = [fields.Command.set(product_ids)]
            ticket.has_partner_picking = any(partner_id in outgoing_product for partner_id in suitable_partner_ids) or any(partner_id in partners_in_sale for partner_id in suitable_partner_ids)

    @api.onchange('suitable_product_ids')
    def onchange_product_id(self):
        if self.product_id not in self.suitable_product_ids:
            self.product_id = False

    @api.depends('picking_ids')
    def _compute_pickings_count(self):
        for ticket in self:
            ticket.pickings_count = len(ticket.picking_ids)

    @api.onchange('partner_id', 'team_id')
    def _compute_display_extra_info(self):
        show_product_id_records = self.filtered(lambda ticket:
            (ticket.partner_id or ticket.use_product_repairs) and\
            (ticket.use_credit_notes or ticket.use_product_returns or ticket.use_product_repairs)
        )
        show_product_id_records.display_extra_info = True
        super(HelpdeskTicket, self - show_product_id_records)._compute_display_extra_info()

    def write(self, vals):
        res = super().write(vals)
        if 'suitable_product_ids' in vals:
            self.filtered(lambda t: t.product_id not in t.suitable_product_ids).product_id = False
        return res

    def action_view_pickings(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Return Orders'),
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.picking_ids.ids)],
            'context': dict(self._context, create=False, default_company_id=self.company_id.id)
        }
        if self.pickings_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.picking_ids.id
            })
        return action

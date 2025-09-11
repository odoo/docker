# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import fields, models, _, api
from odoo.exceptions import UserError
from odoo.tools import file_open


class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    _start_name = "date_start"
    _stop_name = "date_finished"

    check_ids = fields.One2many('quality.check', 'production_id', string="Checks")

    employee_ids = fields.Many2many('hr.employee', string="working employees", compute='_compute_employee_ids')

    log_note = fields.Text(string="Log note")

    def write(self, vals):
        if 'lot_producing_id' in vals:
            self.sudo().workorder_ids.check_ids.filtered(lambda c: c.test_type_id.technical_name == 'register_production').write({'lot_id': vals['lot_producing_id']})
        return super().write(vals)

    def action_add_byproduct(self):
        self.ensure_one()
        action = self.env['stock.move'].with_context(order_id=self.id).action_add_from_catalog_byproduct()
        action['target'] = 'new'
        action['context']['dialog_size'] = 'extra-large'
        return action

    def action_add_component(self):
        self.ensure_one()
        action = self.env['stock.move'].with_context(order_id=self.id).action_add_from_catalog_raw()
        action['target'] = 'new'
        action['context']['dialog_size'] = 'extra-large'
        return action

    def action_add_workorder(self):
        default_blocking_wo_id = self.workorder_ids[-1].id if self.workorder_ids else False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp_production.additional.workorder',
            'views': [[self.env.ref('mrp_workorder.view_mrp_production_additional_workorder_wizard').id, 'form']],
            'name': _('Add Work Order'),
            'target': 'new',
            'context': {
                'default_production_id': self.id,
                'default_blocked_by_workorder_id': default_blocking_wo_id,
            }
        }

    def action_log_note(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'res_model': 'mrp.production',
            'views': [[self.env.ref('mrp_workorder.mrp_production_view_form_log_note').id, 'form']],
            'name': _('Add log note'),
            'target': 'new',
            'context': {
                'default_production_id': self.id,
            }
        }

    def action_open_shop_floor(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('mrp_workorder.action_mrp_display')
        action['context'] = {
            'show_all_workorders': True,
            'search_default_name': self.name,
            'shouldHideNewWorkcenterButton': True,
        }
        return action

    @api.depends('workorder_ids', 'workorder_ids.employee_ids')
    def _compute_employee_ids(self):
        for record in self:
            record.employee_ids = record.workorder_ids.employee_ids

    def _split_productions(self, amounts=False, cancel_remaining_qty=False, set_consumed_qty=False):
        productions = super()._split_productions(amounts=amounts, cancel_remaining_qty=cancel_remaining_qty, set_consumed_qty=set_consumed_qty)
        backorders = productions[1:]
        if not backorders:
            return productions
        for wo in backorders.workorder_ids:
            if wo.current_quality_check_id.component_id:
                wo.current_quality_check_id._update_component_quantity()
        return productions

    def pre_button_mark_done(self):
        res = super().pre_button_mark_done()
        if res is True:
            self.workorder_ids.verify_quality_checks()
        return res

    def _update_catalog_line_quantity(self, line, quantity, **kwargs):
        super()._update_catalog_line_quantity(line, quantity)
        if kwargs.get('from_shop_floor'):
            line.quantity = quantity
            line.manual_consumption = True

    def _get_new_catalog_line_values(self, product_id, quantity, **kwargs):
        values = super()._get_new_catalog_line_values(product_id, quantity)
        if kwargs.get('from_shop_floor'):
            values.update({
                'additional': True,
                'manual_consumption': True,
            })
        return values

    def can_load_samples(self):
        return self.sudo().env['mrp.production'].search_count([]) == 0

    def action_load_samples(self):
        if not self.can_load_samples():
            raise UserError(_('Unable to load samples when you already have existing manufacturing orders'))

        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)

        products = [{'xml_id': xmlid, 'noupdate': True, 'values': {
            'name': name,
            'categ_id': self.env.ref('product.product_category_all').id,
            'is_storable': True,
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'uom_po_id': self.env.ref('uom.product_uom_unit').id,
            'description': desc,
            'default_code': code,
            'image_1920': base64.b64encode(file_open(img, "rb").read()),
        }} for (xmlid, name, desc, code, img) in (
            (
                'mrp.product_product_computer_desk',
                'Table',
                'Solid wood table',
                'SAMPLE_TABLE',
                'mrp/static/img/table.png',
            ),
            (
                'mrp.product_product_computer_desk_head',
                'Table Top',
                'Solid wood is a durable natural material.',
                'SAMPLE_TABLE_TOP',
                'mrp/static/img/table_top.png'
            ),
            (
                'mrp.product_product_computer_desk_leg',
                'Table Leg',
                '18″ x 2½″ Square Leg',
                'SAMPLE_TABLE_LEG',
                'mrp/static/img/table_leg.png'
            ),
        )]
        table, tabletop, tableleg = self.env['product.product']._load_records(products, True)

        quants = [{'xml_id': xmlid, 'noupdate': True, 'values': {
            'product_id': prod,
            'inventory_quantity': qty,
            'location_id': warehouse.lot_stock_id.id,
        }} for (xmlid, prod, qty) in (
            ('mrp.mrp_inventory_1', tabletop.id, 1),
            ('mrp.mrp_inventory_2', tableleg.id, 4),
        )]
        self.env['stock.quant']._load_records(quants, True)._apply_inventory()

        bom = self.env['mrp.bom']._load_records([{'xml_id': 'mrp.mrp_bom_desk', 'noupdate': True, 'values': {
            'product_tmpl_id': table.product_tmpl_id.id,
            'product_uom_id': self.env.ref('uom.product_uom_unit').id,
            'sequence': 3,
            'consumption': 'flexible',
            'days_to_prepare_mo': 3,
        }}], True)

        bom_lines = [{'xml_id': xmlid, 'noupdate': True, 'values': {
            'product_id': prod,
            'product_qty': qty,
            'product_uom_id': self.env.ref('uom.product_uom_unit').id,
            'sequence': seq,
            'bom_id': bom.id,
        }} for (xmlid, prod, qty, seq) in (
            ('mrp.mrp_bom_desk_line_1', tabletop.id, 1, 1),
            ('mrp.mrp_bom_desk_line_2', tableleg.id, 4, 2),
        )]
        bom_lines = self.env['mrp.bom.line']._load_records(bom_lines, True)

        MO = self.env['mrp.production']._load_records([{'xml_id': 'mrp.mrp_production_3', 'noupdate': True, 'values': {
            'product_id': table.id,
            'product_uom_id': self.env.ref('uom.product_uom_unit').id,
            'product_qty': 1,
            'date_start': datetime.today() + relativedelta(days=1),
            'bom_id': bom.id,
        }}], True)
        self.env['procurement.group'].run_scheduler()
        MO.action_confirm()

        if self.env.user.has_group('mrp.group_mrp_routings'):
            WC = self.env['mrp.workcenter']._load_records([{'xml_id': 'mrp.mrp_workcenter_3', 'noupdate': True, 'values': {
                'name': 'Assembly line 1',
                'resource_calendar_id': self.env.ref('resource.resource_calendar_std').id,
            }}], True)

            routing = self.env['mrp.routing.workcenter']._load_records([{
                'xml_id': 'mrp.mrp_routing_workcenter_5', 'noupdate': True, 'values': {
                    'bom_id': bom.id,
                    'workcenter_id': WC.id,
                    'time_cycle': 120,
                    'sequence': 10,
                    'name': 'Assembly',
                    'worksheet_type': 'pdf',
                    'worksheet': base64.b64encode(
                        file_open('mrp/static/img/cutting-worksheet.pdf', "rb").read()
                    )
                }
            }], True)
            bom_lines.operation_id = routing

            quality_points = [{'xml_id': xmlid, 'noupdate': True, 'values': {
                'product_ids': [table.id],
                'picking_type_ids': [warehouse.manu_type_id.id],
                'operation_id': routing.id,
                'test_type_id': self.env.ref(testtype).id,
                'note': note,
                'title': title,
                'worksheet_page': page,
                'sequence': seq,
                'component_id': comp,
            }} for (xmlid, testtype, note, title, page, seq, comp) in (
                (
                    'mrp_workorder.quality_point_register_serial_production',
                    'mrp_workorder.test_type_register_production',
                    'Register the produced quantity.',
                    'Register production',
                    0,
                    5,
                    None,
                ),
                (
                    'mrp_workorder.quality_point_component_registration',
                    'mrp_workorder.test_type_register_consumed_materials',
                    'Please register consumption of the table top.',
                    'Component Registration: Table Head',
                    1,
                    20,
                    tabletop.id,
                ),
                (
                    'mrp_workorder.quality_point_instructions',
                    'quality.test_type_instructions',
                    'Please ensure you are using the new SRX679 screwdriver.',
                    'Choice of screwdriver',
                    1,
                    30,
                    None,
                ),
                (
                    'mrp_workorder.quality_point_component_registration_2',
                    'mrp_workorder.test_type_register_consumed_materials',
                    'Please register consumption of the table legs.',
                    'Component Registration: Table Legs',
                    4,
                    70,
                    tableleg.id,
                ),
                (
                    'mrp_workorder.quality_point_register_production',
                    'quality.test_type_instructions',
                    'Please attach the legs to the table as shown below.',
                    'Table Legs',
                    4,
                    60,
                    None,
                ),
                (
                    'mrp_workorder.quality_point_print_labels',
                    'mrp_workorder.test_type_print_label',
                    None,
                    'Print Labels',
                    0,
                    90,
                    None,
                ),
            )]
            self.env['quality.point']._load_records(quality_points, True)

            MO.action_update_bom()

import json

from odoo import models, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def sync_from_ui(self, orders):
        data = super().sync_from_ui(orders)

        if len(orders) > 0:
            orders = self.browse([o['id'] for o in data["pos.order"]])
            for order in orders:
                if order.state == 'paid':
                    self.env['pos_preparation_display.order'].process_order(order.id)

        return data

    def _process_preparation_changes(self, cancelled=False, general_note=None, note_history=None):
        self.ensure_one()
        flag_change = False
        sound = False

        pdis_order = self.env['pos_preparation_display.order'].search(
            [('pos_order_id', '=', self.id)]
        )

        pdis_lines = pdis_order.preparation_display_order_line_ids
        pdis_ticket = False
        quantity_data = {}
        category_ids = set()

        # If cancelled flag, we flag all lines as cancelled
        if cancelled:
            for line in pdis_lines:
                line.product_cancelled = line.product_quantity
                category_ids.update(line.product_id.pos_categ_ids.ids)
            return {'change': True, 'sound': False, 'category_ids': category_ids}

        # create a dictionary with the key as a tuple of product_id, internal_note and attribute_value_ids
        for pdis_line in pdis_lines:
            key = (pdis_line.product_id.id, pdis_line.internal_note or '', json.dumps(pdis_line.attribute_value_ids.ids), pdis_line.pos_order_line_uuid)
            line_qty = pdis_line.product_quantity - pdis_line.product_cancelled
            if not quantity_data.get(key):
                quantity_data[key] = {
                    'attribute_value_ids': pdis_line.attribute_value_ids.ids,
                    'note': pdis_line.internal_note or '',
                    'product_id': pdis_line.product_id.id,
                    'display': line_qty,
                    'order': 0,
                    'uuid': pdis_line.pos_order_line_uuid,
                }
            else:
                quantity_data[key]['display'] += line_qty

        for line in self.lines.filtered(lambda li: not li.skip_change):
            line_note = line.note or ""
            key = (line.product_id.id, line_note, json.dumps(line.attribute_value_ids.ids), line.uuid)

            if not quantity_data.get(key):
                quantity_data[key] = {
                    'attribute_value_ids': line.attribute_value_ids.ids,
                    'note': line_note or '',
                    'product_id': line.product_id.id,
                    'display': 0,
                    'order': line.qty,
                    'uuid': line.uuid,
                }
            else:
                quantity_data[key]['order'] += line.qty

        # Update quantity_data with note_history
        if note_history:
            for line in pdis_lines[::-1]:
                product_id = str(line.product_id.id)
                for note in note_history.get(product_id, []):
                    if note["uuid"] == line.pos_order_line_uuid and line.internal_note == note['old'] and note['qty'] > 0 and line.product_quantity <= note['qty'] - note.get('used_qty', 0):
                        if not note.get('used_qty'):
                            note['used_qty'] = line.product_quantity
                        else:
                            note['used_qty'] += line.product_quantity

                        key = (line.product_id.id, line.internal_note or '', json.dumps(line.attribute_value_ids.ids), line.pos_order_line_uuid)
                        key_new = (line.product_id.id, note['new'] or '', json.dumps(line.attribute_value_ids.ids), line.pos_order_line_uuid)

                        line.internal_note = note['new']
                        flag_change = True
                        category_ids.update(line.product_id.pos_categ_ids.ids)

                        if not quantity_data.get(key_new):
                            quantity_data[key_new] = {
                                'attribute_value_ids': line.attribute_value_ids.ids,
                                'note': note['new'] or '',
                                'product_id': line.product_id.id,
                                'display': 0,
                                'order': 0,
                                'uuid': line.pos_order_line_uuid,
                            }

                        # Merge the two lines, so that if the quantity was changed it's also applied
                        old_quantity = quantity_data.pop(key, None)
                        quantity_data[key_new]["display"] += old_quantity["display"]
                        quantity_data[key_new]["order"] += old_quantity["order"]

        # Check if pos_order have new lines or if some lines have more quantity than before
        if any([quantities['order'] > quantities['display'] for quantities in quantity_data.values()]):
            flag_change = True
            sound = True
            pdis_ticket = self.env['pos_preparation_display.order'].create({
                'displayed': True,
                'pos_order_id': self.id,
                'pos_config_id': self.config_id.id,
                'pdis_general_note': self.general_note or '',
            })

        product_ids = self.env['product.product'].browse([data['product_id'] for data in quantity_data.values()])
        for data in quantity_data.values():
            product_id = data['product_id']
            product = product_ids.filtered(lambda p: p.id == product_id)
            if data['order'] > data['display']:
                missing_qty = data['order'] - data['display']
                filtered_lines = self.lines.filtered(lambda li: li.uuid == data['uuid'])
                line_qty = 0

                for line in filtered_lines:

                    if missing_qty == 0:
                        break

                    if missing_qty > line.qty:
                        line_qty += line.qty
                        missing_qty -= line.qty
                    elif missing_qty <= line.qty:
                        line_qty += missing_qty
                        missing_qty = 0

                    if missing_qty == 0 and line_qty > 0:
                        flag_change = True
                        category_ids.update(product.pos_categ_ids.ids)
                        self.env['pos_preparation_display.orderline'].create({
                            'todo': True,
                            'internal_note': line.note or "",
                            'attribute_value_ids': line.attribute_value_ids.ids,
                            'product_id': product_id,
                            'product_quantity': line_qty,
                            'preparation_display_order_id': pdis_ticket.id,
                            'pos_order_line_uuid': line.uuid,
                        })
            elif data['order'] < data['display']:
                qty_to_cancel = data['display'] - data['order']
                for line in pdis_lines.filtered(lambda li: li.product_id.id == product_id and li.internal_note == data['note'] and li.attribute_value_ids.ids == data['attribute_value_ids']):
                    flag_change = True
                    line_qty = 0
                    pdis_qty = line.product_quantity - line.product_cancelled

                    if qty_to_cancel == 0:
                        break

                    if pdis_qty > qty_to_cancel:
                        line.product_cancelled += qty_to_cancel
                        qty_to_cancel = 0
                    elif pdis_qty <= qty_to_cancel:
                        line.product_cancelled += pdis_qty
                        qty_to_cancel -= pdis_qty
                    category_ids.update(line.product_id.pos_categ_ids.ids)

        if general_note is not None:
            for order in pdis_order:
                if order.pdis_general_note != general_note:
                    order.pdis_general_note = general_note or ''
                    flag_change = True
                    category_ids.update(pdis_lines[0].product_id.pos_categ_ids.ids)  # necessary to send when only ordernote changed

        return {'change': flag_change, 'sound': sound, 'category_ids': category_ids}

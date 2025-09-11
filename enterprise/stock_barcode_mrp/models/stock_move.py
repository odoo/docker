from odoo import models
from odoo.tools.float_utils import float_compare


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_fields_stock_barcode(self):
        return super()._get_fields_stock_barcode() + ['product_uom']

    def split_uncompleted_moves(self):
        production_moves = self.filtered(lambda m: m.picking_type_id.code == 'mrp_operation')
        new_move_line_vals = []
        for move in production_moves:
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(move.quantity, 0, precision_digits=rounding) > 0 and float_compare(move.quantity, move.product_uom_qty, precision_digits=rounding) < 0 and move.picked:
                qty_split = move.product_uom._compute_quantity(move.product_uom_qty - move.quantity, move.product_id.uom_id, rounding_method='HALF-UP')
                move_line_vals = move._prepare_move_line_vals(quantity=qty_split)
                move_line_vals['picked'] = False
                new_move_line_vals.append(move_line_vals)
        if new_move_line_vals:
            self.env['stock.move.line'].create(new_move_line_vals)
        return super(StockMove, self - production_moves).split_uncompleted_moves()

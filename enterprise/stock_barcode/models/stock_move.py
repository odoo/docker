
from odoo import models


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_fields_stock_barcode(self):
        return [
            'product_id',
            'location_id',
            'product_uom_qty',
            'move_line_ids',
        ]

    def split_uncompleted_moves(self):
        """ Creates a new move for every uncompleted move in order to get one picked move
        with the picked quantity, and one not picked move with the remaining quantity."""
        moves_to_reset = self.filtered(lambda m: m.picked and m.quantity == 0)
        moves_to_backorder = (self - moves_to_reset).filtered('picked')
        for move in moves_to_reset:
            move.move_line_ids.unlink()
            move.quantity = move.product_uom_qty
            move.picked = False
        new_moves = moves_to_backorder._create_backorder()
        # mto moves should be assigned manually as they are not by the `_action_confirm`
        new_moves.with_context(bypass_entire_pack=True).filtered(lambda m: m.procure_method == 'make_to_order')._action_assign()
        if new_moves:
            # In some case, we already split the move lines in the front end.
            # Those move lines are linked to the original move. If their quantity
            # is 0 and they already picked, there is no reason to keep them.
            moves_to_clean = self - new_moves
            for move in moves_to_clean:
                for move_line in move.move_line_ids:
                    if move_line.quantity == 0 and move_line.picked:
                        move_line.unlink()
        return new_moves

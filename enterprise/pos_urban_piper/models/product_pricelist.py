from odoo import models, api


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    @api.model
    def write(self, vals):
        res = super().write(vals)
        for pricelist in self:
            urban_piper_configs = self.env['pos.config'].sudo().search([
                ('company_id', '=', pricelist.company_id.id),
                ('module_pos_urban_piper', '=', True),
                ('urbanpiper_pricelist_id', '=', pricelist.id),
            ])
            if urban_piper_configs:
                linked_urban_piper_status = self.env['product.template'].sudo().search([('urbanpiper_pos_config_ids', 'in', urban_piper_configs.ids)])\
                    .mapped('urban_piper_status_ids')\
                    .filtered(lambda s: s.is_product_linked)
                linked_urban_piper_status.write({'is_product_linked': False})
        return res

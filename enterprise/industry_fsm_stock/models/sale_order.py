# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_product_catalog_order_data(self, products, **kwargs):
        product_catalog = super()._get_product_catalog_order_data(products, **kwargs)
        if not self.env.context.get('fsm_task_id'):
            return product_catalog
        for product in products:
            if product.id in product_catalog:
                product_catalog[product.id]['tracking'] = product.tracking not in ['none', False]
        return product_catalog

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.osv import expression


class QuantPackage(models.Model):
    _inherit = 'stock.quant.package'
    _barcode_field = 'name'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        domain = self.env.company.nomenclature_id._preprocess_gs1_search_args(domain, ['package'], 'name')
        return super()._search(domain, offset=offset, limit=limit, order=order)

    @api.model
    def action_create_from_barcode(self, vals_list):
        """ Creates a new package then returns its data to be added in the client side cache.
        """
        res = self.create(vals_list)
        return {
            'stock.quant.package': res.read(self._get_fields_stock_barcode(), False)
        }

    @api.model
    def _get_fields_stock_barcode(self):
        return ['name', 'location_id', 'package_type_id', 'quant_ids']

    @api.model
    def _get_usable_packages(self):
        usable_packages_domain = [
            '|',
            ('package_use', '=', 'reusable'),
            ('location_id', '=', False),
        ]
        # Limit the number of records to load if param is set.
        records_limit = int(self.env['ir.config_parameter'].sudo().get_param('stock_barcode.usable_packages_limit'))
        packages = self.env['stock.quant.package'].search(usable_packages_domain, limit=records_limit, order='create_date desc')
        loc_ids = self._context.get('pack_locs')
        if loc_ids:
            packages |= self.env['stock.quant.package'].search([('location_id', 'in', loc_ids)])
        return packages

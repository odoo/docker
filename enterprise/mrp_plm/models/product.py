# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    version = fields.Integer('Version', default=1, copy=False, help="The current version of the product.")
    eco_count = fields.Integer('# ECOs',compute='_compute_eco_count')
    eco_ids = fields.One2many('mrp.eco', 'product_tmpl_id', 'ECOs')

    def _compute_eco_count(self):
        for p in self:
            p.eco_count = len(p.eco_ids)

    def mrp_eco_action_product_tmpl(self):
        action = self.env["ir.actions.actions"]._for_xml_id("mrp_plm.mrp_eco_action_product_tmpl")
        action['domain'] = ['&', ('product_tmpl_id', '=', self.id),
            ('type', '=', 'product')]
        return action


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def mrp_eco_action_product_tmpl(self):
        action = self.product_tmpl_id.mrp_eco_action_product_tmpl()
        action['context'] = {'default_product_tmpl_id': self.product_tmpl_id.id}
        action['domain'] = ['&', ('product_tmpl_id', '=', self.product_tmpl_id.id),
            ('type', '=', 'product')]
        return action

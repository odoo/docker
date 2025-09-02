# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.account_intrastat.models.account_intrastat_code import SUPPLEMENTARY_UNITS


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    intrastat_code_id = fields.Many2one(
        'account.intrastat.code',
        compute='_compute_intrastat_values',
        inverse='_inverse_intrastat_code_id',
        string='Commodity Code',
        readonly=False,
    )
    intrastat_supplementary_unit = fields.Selection(selection=SUPPLEMENTARY_UNITS, compute='_compute_intrastat_values')
    intrastat_supplementary_unit_amount = fields.Float(
        compute='_compute_intrastat_values',
        inverse='_inverse_intrastat_supplementary_unit_amount',
        help='The number of supplementary units per product quantity.',
        readonly=False,
    )
    intrastat_origin_country_id = fields.Many2one(
        'res.country',
        compute='_compute_intrastat_values',
        inverse='_inverse_intrastat_origin_country_id',
        string='Country of Origin',
        readonly=False,
    )

    @api.depends('product_variant_ids')
    def _compute_intrastat_values(self):
        for product_template in self:
            variant = product_template.product_variant_ids[:1]
            product_template.intrastat_code_id = variant.intrastat_code_id
            product_template.intrastat_supplementary_unit = variant.intrastat_code_id.supplementary_unit
            product_template.intrastat_supplementary_unit_amount = variant.intrastat_supplementary_unit_amount
            product_template.intrastat_origin_country_id = variant.intrastat_origin_country_id

    def _inverse_intrastat_code_id(self):
        for product_template in self:
            product_template.product_variant_ids.intrastat_code_id = product_template.intrastat_code_id

    def _inverse_intrastat_supplementary_unit_amount(self):
        for product_template in self:
            product_template.product_variant_ids.intrastat_supplementary_unit_amount = product_template.intrastat_supplementary_unit_amount

    def _inverse_intrastat_origin_country_id(self):
        for product_template in self:
            product_template.product_variant_ids.intrastat_origin_country_id = product_template.intrastat_origin_country_id

    def _get_related_fields_variant_template(self):
        fields = super()._get_related_fields_variant_template()
        fields += ['intrastat_code_id', 'intrastat_origin_country_id', 'intrastat_supplementary_unit', 'intrastat_supplementary_unit_amount']
        return fields

class ProductProduct(models.Model):
    _inherit = 'product.product'

    intrastat_code_id = fields.Many2one(comodel_name='account.intrastat.code', string='Commodity code', domain="[('type', '=', 'commodity')]")
    # The supplementary unit of the current commodity code
    intrastat_supplementary_unit = fields.Selection(related='intrastat_code_id.supplementary_unit')
    # The ratio of product to the number of supplementary units
    intrastat_supplementary_unit_amount = fields.Float(
        string='Supplementary Units',
        help='The number of supplementary units per product quantity.',
    )
    intrastat_origin_country_id = fields.Many2one('res.country', string='Country of Origin')

    @api.depends('intrastat_supplementary_unit')
    def _compute_intrastat_supplementary_unit_amount(self):
        """ In the case when the product has no supplementary unit (i.e. we are using weight) the supplementary unit amount is set to 0 """
        for product in self:
            if not product.intrastat_supplementary_unit:
                product.intrastat_supplementary_unit_amount = 0

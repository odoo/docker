# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class Document(models.Model):
    _name = 'documents.document'
    _inherit = ['documents.document']

    website_id = fields.Many2one('website', ondelete='cascade', compute='_compute_website_id',
                                 readonly=False, store=True, domain="[('company_id', '=', company_id)]")

    @api.depends('website_id')
    def _compute_access_url(self):
        return super()._compute_access_url()

    @api.depends('company_id')
    def _compute_website_id(self):
        for document in self.filtered(lambda d: not d.website_id or d.website_id.company_id != d.company_id):
            document.website_id = document.company_id.website_id or self.env.company.website_id

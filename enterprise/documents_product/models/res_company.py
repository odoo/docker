# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    documents_product_settings = fields.Boolean()
    product_folder_id = fields.Many2one(
        'documents.document', string="Product Workspace", check_company=True,
        default=lambda self: self.env.ref('document_product_folder', raise_if_not_found=False),
        domain=[('type', '=', 'folder'), ('shortcut_document_id', '=', False)])
    product_tag_ids = fields.Many2many('documents.tag', 'product_tags_table')

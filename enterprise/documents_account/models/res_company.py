# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    documents_account_settings = fields.Boolean()
    account_folder_id = fields.Many2one(
        'documents.document', string="Accounting Workspace", check_company=True,
        default=lambda self: self.env.ref('documents.document_finance_folder', raise_if_not_found=False),
        domain=[('type', '=', 'folder'), ('shortcut_document_id', '=', False)])

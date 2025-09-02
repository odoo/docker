from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    documents_account_peppol_folder_id = fields.Many2one(
        comodel_name='documents.document',
        string="Document Workspace",
        check_company=True,
        domain=[('type', '=', 'folder'), ('shortcut_document_id', '=', False)]
    )
    documents_account_peppol_tag_ids = fields.Many2many(
        comodel_name='documents.tag',
        string="Document Tags",
    )

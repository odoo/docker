# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = "res.company"

    documents_recruitment_settings = fields.Boolean(default=False)
    recruitment_folder_id = fields.Many2one('documents.document', string="Recruitment Workspace", check_company=True,
                                            domain=[('type', '=', 'folder'), ('shortcut_document_id', '=', False)],
                                            default=lambda self: self.env.ref('documents_hr_recruitment.document_recruitment_folder',
                                                                              raise_if_not_found=False))
    recruitment_tag_ids = fields.Many2many('documents.tag', 'recruitment_tags_rel')

from odoo import models, _
from odoo.exceptions import UserError


class DocumentsDocument(models.Model):
    _inherit = 'documents.document'

    def document_sign_create_sign_template_x(self, create_model, folder_id=False):
        if create_model not in ('sign.template.new', 'sign.template.direct'):
            raise UserError(_("Invalid model %s", create_model))
        if create_model == 'sign.template.direct' and len(self) != 1:
            raise UserError(_("This action can only be applied on a single record."))
        if self.filtered(lambda doc: doc.type != 'binary' or doc.shortcut_document_id
                                     or not doc.mimetype or 'pdf' not in doc.mimetype.lower()):
            raise UserError(_("This action can only be applied on pdf document."))

        create_values_list = []
        for document in self:
            create_values = {
                'attachment_id': document.attachment_id.id,
                'favorited_ids': [(4, self.env.user.id)],
                'folder_id': folder_id or document.folder_id.id,
            }
            if document.tag_ids:
                create_values['documents_tag_ids'] = [(6, 0, document.tag_ids.ids)]
            create_values_list.append(create_values)

        templates = self.env['sign.template'].create(create_values_list)

        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'sign.template',
            'name': _("New templates"),
            'view_id': False,
            'view_mode': 'kanban',
            'views': [(False, "kanban"), (False, "form")],
            'domain': [('id', 'in', templates.ids)],
            'context': self._context,
        }

        if len(templates.ids) == 1:
            return templates.go_to_custom_template(sign_directly_without_mail=create_model == 'sign.template.direct')
        return action

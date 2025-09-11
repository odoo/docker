# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
from odoo.exceptions import ValidationError


class DocumentAccess(models.Model):
    _inherit = "documents.access"

    @api.constrains("document_id", "partner_id", "role")
    def _check_spreadsheet(self):
        """Check that only internal user can edit a spreadsheet."""
        for access in self:
            if (access.document_id.handler == 'spreadsheet'
                and (not access.partner_id.user_ids or access.partner_id.user_ids.share)
                and access.role == 'edit'):
                raise ValidationError(_('Spreadsheets can not be shared in edit mode to non-internal users.'))

            if access.document_id.handler == 'frozen_spreadsheet' and access.role == 'edit':
                raise ValidationError(_('Frozen Spreadsheets can not be editable.'))

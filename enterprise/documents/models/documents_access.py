from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class DocumentAccess(models.Model):
    _name = 'documents.access'
    _description = 'Document / Partner'
    _log_access = False

    document_id = fields.Many2one('documents.document', required=True, auto_join=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)
    role = fields.Selection(
        [('view', 'Viewer'), ('edit', 'Editor')],
        string='Role', required=False, index=True)
    last_access_date = fields.Datetime('Last Accessed On', required=False)
    expiration_date = fields.Datetime('Expiration', index=True)

    _sql_constraints = [
        ('unique_document_access_partner', 'unique(document_id, partner_id)',
         'This partner is already set on this document.'),
        ('role_or_last_access_date', 'check (role IS NOT NULL or last_access_date IS NOT NULL)',
         'NULL roles must have a set last_access_date'),
    ]

    def _prepare_create_values(self, vals_list):
        vals_list = super()._prepare_create_values(vals_list)
        documents = self.env['documents.document'].browse(
            [vals['document_id'] for vals in vals_list])
        documents.check_access('write')
        return vals_list

    def write(self, vals):
        if 'partner_id' in vals or 'document_id' in vals:
            raise AccessError(_('Access documents and partners cannot be changed.'))

        self.document_id.check_access('write')
        return super().write(vals)

    @api.autovacuum
    def _gc_expired(self):
        self.search([('expiration_date', '<=', fields.Datetime.now())], limit=1000).unlink()

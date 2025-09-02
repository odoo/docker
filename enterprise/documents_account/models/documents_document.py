# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import binascii
import contextlib
from itertools import chain
from xml.etree import ElementTree

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DocumentsDocument(models.Model):
    _inherit = 'documents.document'

    # once we parsed the XML to know if a PDF is embedded inside,
    # we store that information so we don't need to parse it again
    has_embedded_pdf = fields.Boolean('Has Embedded PDF', compute='_compute_has_embedded_pdf', store=True)

    @api.depends('has_embedded_pdf')
    def _compute_thumbnail(self):
        """Compute the thumbnail and thumbnail status.

        If the XML invoices contain an embedded PDF, the thumbnail / thumbnail_status
        must have the same behavior as a standard PDF.
        """
        xml_documents = self.filtered(lambda doc: doc.has_embedded_pdf)
        xml_documents.thumbnail = False
        xml_documents.thumbnail_status = 'client_generated'
        super(DocumentsDocument, self - xml_documents)._compute_thumbnail()

    @api.depends('checksum')
    def _compute_has_embedded_pdf(self):
        for document in self:
            document.has_embedded_pdf = bool(document._extract_pdf_from_xml())

    def _extract_pdf_from_xml(self):
        """Parse the XML file and return the PDF content if one is found.

        For some invoice files (in the XML format), we can have a PDF embedded inside
        in base 64. We want to be able to preview it in documents.

        We support the UBL format
        > https://docs.peppol.eu/poacc/billing/3.0/syntax/ubl-invoice
        """
        self.ensure_one()

        if not self.mimetype:
            return False

        if not (self.mimetype.endswith('/xml')
                or (self.mimetype == 'text/plain' and self.name.lower().endswith('.xml'))):
            return False

        try:
            xml_file_content = self.with_context(bin_size=False).raw.decode()
        except UnicodeDecodeError:
            return False

        # quick filters, to not parse the XML most of the cases
        if "EmbeddedDocumentBinaryObject" not in xml_file_content and "Attachment" not in xml_file_content:
            return False

        try:
            tree = ElementTree.fromstring(xml_file_content)
        except ElementTree.ParseError:
            return False

        attachment_nodes = tree.iterfind('.//{*}EmbeddedDocumentBinaryObject')
        attachment_nodes = chain(attachment_nodes, tree.iterfind('.//{*}Attachment'))

        for attachment_node in attachment_nodes:
            if len(attachment_node):  # the node has children
                continue

            with contextlib.suppress(TypeError, binascii.Error):
                # check file header in case many file are embedded in the XML
                if (pdf_attachment_content := base64.b64decode(attachment_node.text + "====")).startswith(b'%PDF-'):
                    return pdf_attachment_content

        return False

    def account_create_account_move(self, move_type, journal_id=None, partner_id=None, skip_activities=False):
        if not skip_activities:
            for record in self:
                record.activity_ids.action_feedback(feedback="completed")
        if any(document.type == 'folder' for document in self):
            raise UserError(_('You can not create account move on folder.'))

        if journal_id is None:
            company_journals = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(self.env.company),
            ])
            if move_type == 'statement':
                journal_id = company_journals.filtered(lambda journal: journal.type == 'bank')[:1]
            else:
                move = self.env['account.move'].new({'move_type': move_type})
                journal_id = move.suitable_journal_ids[:1]._origin

        move = None
        invoices = self.env['account.move']

        # 'entry' are outside of document loop because the actions
        #  returned could be differents (cfr. l10n_be_soda)
        if move_type == 'entry':
            return journal_id.create_document_from_attachment(attachment_ids=self.attachment_id.ids)

        for document in self:
            if document.res_model == 'account.move' and document.res_id:
                move = self.env['account.move'].browse(document.res_id)
            else:
                move = journal_id\
                    .with_context(default_move_type=move_type)\
                    ._create_document_from_attachment(attachment_ids=document.attachment_id.id)
            partner = partner_id or document.partner_id
            if partner:
                move.partner_id = partner
            if move.statement_line_id:
                move['suspense_statement_line_id'] = move.statement_line_id.id

            invoices |= move

        context = dict(self._context, default_move_type=move_type)
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'name': _("Invoices"),
            'view_id': False,
            'view_mode': 'list',
            'views': [(False, "list"), (False, "form")],
            'domain': [('id', 'in', invoices.ids)],
            'context': context,
        }
        if len(invoices) == 1:
            record = move or invoices[0]
            view_id = record.get_formview_id() if record else False
            action.update({
                'view_mode': 'form',
                'views': [(view_id, "form")],
                'res_id': invoices[0].id,
                'view_id': view_id,
            })
        return action

    def account_create_account_bank_statement(self, journal_id=None):
        # only the journal type is checked as journal will be retrieved from
        # the bank account later on. Also it is not possible to link the doc
        # to the newly created entry as they can be more than one. But importing
        # many times the same bank statement is later checked.
        default_journal = journal_id or self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
        return default_journal.create_document_from_attachment(attachment_ids=self.attachment_id.ids)

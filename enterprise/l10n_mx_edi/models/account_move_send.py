from odoo import _, api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_mx_edi_applicable(self, move):
        return all([
            not move.invoice_pdf_report_id,
            move.l10n_mx_edi_is_cfdi_needed,
            move.l10n_mx_edi_cfdi_state not in ('sent', 'global_sent'),
        ])

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({'mx_cfdi': {'label': _("CFDI"), 'is_applicable': self._is_mx_edi_applicable}})
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if invalid_mx_partners := moves.filtered(
            lambda m: 'mx_cfdi' in moves_data[m]['extra_edis'] and self._is_mx_edi_applicable(m) and not m.partner_id.country_id
        ).partner_id:
            alerts['partner_country_missing'] = {
                "message": _("The following partner(s) have an RFC but no country configured."),
                "action_text": _("View Partner(s)"),
                "action": invalid_mx_partners._get_records_action(
                    name=_("Check Country on Partner(s)")
                ),
            }
        return alerts

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        attachments = super()._get_invoice_extra_attachments(move)
        if move.l10n_mx_edi_cfdi_state == 'sent':
            attachments += move.l10n_mx_edi_cfdi_attachment_id
        return attachments

    def _get_placeholder_mail_attachments_data(self, move, extra_edis=None):
        # EXTENDS 'account'
        results = super()._get_placeholder_mail_attachments_data(move, extra_edis=extra_edis)

        if not move.l10n_mx_edi_cfdi_attachment_id and 'mx_cfdi' in extra_edis:
            filename = move._l10n_mx_edi_get_invoice_cfdi_filename()
            results.append({
                'id': f'placeholder_{filename}',
                'name': filename,
                'mimetype': 'application/xml',
                'placeholder': True,
            })

        return results

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        for invoice, invoice_data in invoices_data.items():

            if 'mx_cfdi' in invoice_data['extra_edis']:
                # Sign it.
                invoice._l10n_mx_edi_cfdi_invoice_try_send()

                # Check for success.
                if invoice.l10n_mx_edi_cfdi_state == 'sent':
                    continue

                # Check for error.
                errors = []
                for document in invoice.l10n_mx_edi_invoice_document_ids:
                    if document.state == 'invoice_sent_failed':
                        errors.append(document.message)
                        break

                invoice_data['error'] = {
                    'error_title': _("Error when sending the CFDI to the PAC:"),
                    'errors': errors,
                }

# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib
import json
import jwt
from datetime import datetime, date
from markupsafe import Markup

from odoo import api, Command, fields, models, tools, _
from odoo.tools import split_every
from .irn_exception import IrnException

UOM_REF_MAP = {
    "CMS": "uom.product_uom_cm",
    "CBM": "uom.product_uom_cubic_meter",
    "DOZ": "uom.product_uom_dozen",
    "GMS": "uom.product_uom_gram",
    "KGS": "uom.product_uom_kgm",
    "KME": "uom.product_uom_km",
    "LTR": "uom.product_uom_litre",
    "MTR": "uom.product_uom_meter",
    "QTL": "uom.product_uom_yard",
    "SQF": "uom.uom_square_foot",
    "SQM": "uom.uom_square_meter",
    "TON": "uom.product_uom_ton",
    "UNT": "uom.product_uom_unit",
    "YDS": "uom.product_uom_yard",
}


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_in_exception = fields.Html("Exception")
    l10n_in_gst_return_period_id = fields.Many2one("l10n_in.gst.return.period", "GST Return Period")
    l10n_in_gstr2b_reconciliation_status = fields.Selection(selection=[
        ("pending", "Pending"),
        ("matched", "Fully Matched"),
        ("partially_matched", "Partially Matched"),
        ("exception", "Exception"),
        ("bills_not_in_gstr2", "Bills Not in GSTR-2"),
        ("gstr2_bills_not_in_odoo", "GSTR-2 Bills not in Odoo")],
        string="GSTR-2B Reconciliation",
        readonly=True,
        default="pending"
    )
    l10n_in_reversed_entry_warning = fields.Boolean('Display reversed entry warning', compute="_compute_l10n_in_reversed_entry_warning")
    l10n_in_irn_number = fields.Char('IRN Number', readonly=True)
    l10n_in_gstr_activate_einvoice_fetch = fields.Selection(related="company_id.l10n_in_gstr_activate_einvoice_fetch")

    @api.depends('move_type', 'reversed_entry_id', 'state', 'invoice_date', 'invoice_line_ids.tax_ids')
    def _compute_l10n_in_reversed_entry_warning(self):
        for move in self:
            if move.country_code == 'IN' and move.move_type == 'out_refund' and move.state == 'draft' and move.invoice_date and move.reversed_entry_id and move.invoice_line_ids.tax_ids:
                move.l10n_in_reversed_entry_warning = move.reversed_entry_id.invoice_date < move.get_fiscal_year_start_date(move.company_id, move.invoice_date)
            else:
                move.l10n_in_reversed_entry_warning = False

    def get_fiscal_year_start_date(self, company, invoice_date):
        fiscal_year_start_month = (int(company.fiscalyear_last_month) % 12) + 1
        fiscal_year_start_date = date(invoice_date.year, fiscal_year_start_month, 1)
        if invoice_date.month <= 11:
            fiscal_year_start_date = fiscal_year_start_date.replace(year=invoice_date.year - 1)
        return fiscal_year_start_date

    def _post(self, soft=True):
        for invoice in self:
            if invoice.l10n_in_gstr2b_reconciliation_status == "gstr2_bills_not_in_odoo":
                invoice.l10n_in_gstr2b_reconciliation_status = "pending"
        return super(AccountMove, self)._post(soft=soft)

    def l10n_in_update_move_using_irn(self):
        """ Fetch the attachment from IRN and use it to update the invoice.

        If an appropriate attachment already exists, update the invoice with that attachment instead,
        reversing modifications to the invoice.

        :returns: action to refresh the form view.
        """
        context = {'active_id': self.ids, 'active_model': 'account.move'}
        self.env['l10n_in.gst.return.period'].with_context(context)._check_config(next_gst_action='fetch_irn_from_account_move', company=self.env.company)

        JSON_MIMETYPE = 'application/json'
        STATUS_CANCELLED = 'CNL'
        for move in self:
            # Filter valid JSON attachments
            attachment = move.attachment_ids.filtered(
                lambda a: a.mimetype == JSON_MIMETYPE and self._is_l10n_in_irn_json(a.raw)
            )[:1]
            if attachment:
                move._extend_with_attachments(attachment)
                continue
            try:
                # Retrieve IRN details if no valid attachment is found
                gov_json_data = self._l10n_in_retrieve_details_from_irn(move.l10n_in_irn_number, move.company_id)
            except IrnException as e:
                move.message_post(body=Markup("Fetching IRN details failed with error(s):<br/> %s") % str(e))
                continue
            attachment = self.env['ir.attachment'].create({
                'name': f'{move.l10n_in_irn_number}.json',
                'mimetype': JSON_MIMETYPE,
                'raw': json.dumps(gov_json_data),
                'res_model': 'account.move',
                'res_id': move.id,
            })
            move._extend_with_attachments(attachment, new=True)
            if gov_json_data.get('Status') == STATUS_CANCELLED and move.state != 'cancel':
                move.message_post(body=_("This bill has been marked as canceled based on the e-invoice status."))
                move.button_cancel()
        return {'type': 'ir.actions.act_window_close'}  # Refresh the form to show the key

    # ========================================
    # Cron Method
    # ========================================

    def _l10n_in_cron_update_with_irn(self, job_count=10):
        """ Update draft account moves with IRN details for Indian companies.

        :param job_count: the number of moves to process in each batch.
        """
        indian_companies = self.env['res.company'].search([('account_fiscal_country_id.code', '=', 'IN')])
        for indian_company in indian_companies:
            if indian_company._is_l10n_in_gstr_token_valid():
                domain = [
                    ('company_id', '=', indian_company.id),
                    ('state', '=', 'draft'),
                    ('company_id.l10n_in_gstr_activate_einvoice_fetch', '=', 'automatic'),
                    ('l10n_in_irn_number', '!=', False),
                    ('posted_before', '=', False),
                    ('line_ids', 'not any', [(1, '=', 1)]),
                ]
                moves = self.env['account.move'].search(domain)
                for move_batch in split_every(job_count, moves):
                    for move in move_batch:
                        move.l10n_in_update_move_using_irn()
                    if not (tools.config['test_enable'] or tools.config['test_file']):
                        self._cr.commit()

    # ========================================
    # Import Vendor Bills and Credit Notes
    # ========================================

    @api.model
    def _is_l10n_in_irn_json(self, content):
        """ Determine whether the given file content is a vendor bill JSON retrieved from IRN. """
        with contextlib.suppress(json.JSONDecodeError, UnicodeDecodeError):
            content = json.loads(content)
            return all(key in content for key in (
                'Irn', 'AckNo', 'AckDt', 'SignedInvoice', 'Status',
            ))

    def _get_edi_decoder(self, file_data, new=False):
        # EXTENDS 'account'
        if file_data['type'] == 'binary' and self._is_l10n_in_irn_json(file_data['content']):
            return self._l10n_in_irn_import_invoice
        return super()._get_edi_decoder(file_data, new=new)

    def _l10n_in_irn_import_invoice(self, invoice, data, is_new):
        """ Import invoice details from IRN data and update the corresponding invoice.

        Signed invoice data is decoded before being passed to the import function.

        :param invoice: the invoice record to be updated.
        :param data: dict representing the signed invoice attachment.
        :param is_new: indicates if the invoice is newly created.

        :returns: True if the import was successful, False if it fails.
        """
        try:
            # Load content from the data
            attachment_content = json.loads(data['content'])
            signed_invoice = attachment_content['SignedInvoice']
        except (json.JSONDecodeError, KeyError):
            return False
        # Decode the signed invoice using JWT
        try:
            decoded_data = jwt.decode(signed_invoice, options={'verify_signature': False})
            decoded_invoice_data = json.loads(decoded_data.get('data', '{}'))
        except (json.JSONDecodeError, jwt.exceptions.DecodeError):
            # Post a message on the invoice regarding the failure
            invoice.message_post(body="Failed to decode signed invoice.")
            return False
        # Update the invoice with decoded data
        with self._get_edi_creation() as self:
            return self._l10n_in_update_bill_with_irn_details(decoded_invoice_data)

    def _l10n_in_update_bill_with_irn_details(self, content):
        """ Update the invoice with details retrieved from IRN.

        :param content: dict representing all invoice details.

        :returns: True if the update was successful

        """
        def _get_tax(rate, tag):
            tax = self.env['account.tax'].search([
                ('type_tax_use', '=', 'purchase'),
                ('amount', '=', rate),
                '|', ('repartition_line_ids.tag_ids', 'in', tag),
                     ('children_tax_ids.repartition_line_ids.tag_ids', 'in', tag)
            ], limit=1)
            return tax

        bill_details = content['DocDtls']
        seller_details = content['SellerDtls']
        item_list = content['ItemList']
        value_details = content['ValDtls']

        self.l10n_in_irn_number = content.get('Irn', False)
        self.move_type = {
            'INV': 'in_invoice',
            'CRN': 'in_refund',
            'DBN': 'in_invoice'
        }.get(bill_details.get('Typ'), 'in_invoice')

        # Find a partner if one exists, else create one
        if seller_details.get('Gstin'):
            seller_partner = self.env['res.partner'].search([
                ('vat', '=', seller_details['Gstin']),
            ], limit=1)
            if not seller_partner:
                partner_vals = self.env['res.partner']._l10n_in_get_partner_vals_by_vat(seller_details['Gstin'])
                if partner_vals:
                    seller_partner = self.env['res.partner'].create(partner_vals)
            self.partner_id = seller_partner

        if (bill_date := bill_details.get('Dt')):
            self.invoice_date = datetime.strptime(bill_date, '%d/%m/%Y').strftime('%Y-%m-%d')

        self.ref = bill_details.get('No')
        igst_tag_id = self.env.ref('l10n_in.tax_tag_igst')
        cgst_tag_id = self.env.ref('l10n_in.tax_tag_cgst')
        sgst_tag_id = self.env.ref('l10n_in.tax_tag_sgst')
        gst_tag_ids = cgst_tag_id + sgst_tag_id

        uom_map = {
            irn_uom: self.env['ir.model.data']._xmlid_to_res_id(xmlid)
            for irn_uom, xmlid in UOM_REF_MAP.items()
        }

        invoice_lines = []
        other_charges = value_details.get('OthChrg', 0)
        cess_charges = 0
        for item in item_list:
            line_dict = {}
            if 'GstRt' in item:
                tag_id = igst_tag_id.ids if item.get('IgstAmt') else gst_tag_ids.ids
                taxes = _get_tax(item['GstRt'], tag_id)
                if taxes:
                    line_dict['tax_ids'] = [Command.link(taxes.id)]

            line_dict['discount'] = (item.get('Discount', 0.0) / item.get('TotAmt', 1.0)) * 100.0 if item.get('TotAmt') else 0.0
            line_dict['product_uom_id'] = uom_map.get(item.get('Unit'))
            invoice_lines.append(
                Command.create({
                    **line_dict,
                    'name': item.get('PrdDesc'),
                    'l10n_in_hsn_code': item.get('HsnCd'),
                    # For service-type products where the quantity might be 0, therefore, replace 0 with 1 to ensure proper handling.
                    'quantity': item.get('Qty') or 1,
                    'price_unit': item.get('UnitPrice'),
                })
            )
            other_charges += item.get('OthChrg', 0)
            cess_charges += sum(item.get(key, 0) for key in ['CesAmt', 'CesNonAdvlAmt', 'StateCesAmt', 'StateCesNonAdvlAmt'])

        # Create other charges line
        if other_charges:
            invoice_lines.append(Command.create({
                'name': "Other Charges",
                'price_unit': other_charges,
            }))
        # Create cess charges line
        if cess_charges:
            invoice_lines.append(Command.create({
                'name': "CESS Charges",
                'price_unit': cess_charges,
            }))
        # Create rounding value line
        if (rounding_amount := value_details.get('RndOffAmt')):
            invoice_lines.append(Command.create({
                'name': "Rounding Value",
                'price_unit': rounding_amount,
            }))
        # Create discount value line
        if (discount_amount := value_details.get('Discount')):
            invoice_lines.append(Command.create({
                'name': "Discount Value",
                'price_unit': discount_amount * -1,
            }))
        if self.invoice_line_ids:
            self.invoice_line_ids.unlink()
        self.invoice_line_ids = invoice_lines
        return True

    def _l10n_in_retrieve_details_from_irn(self, irn_number, company_id):
        """ Retrieve signed invoice details for a given IRN number via the IAP proxy service.

        :param irn_number: IRN number for which signed details are to be retrieved.
        :param company_id: company for which the request is made.

        :returns: dict containing signed IRN details.
        """
        response = self.env['l10n_in.gst.return.period']._request(
            url="/iap/l10n_in_reports/1/einvoice/irndtl",
            params={
                "irn_number": irn_number,
                "auth_token": company_id.sudo().l10n_in_gstr_gst_token,
            },
            company=company_id,
        )
        data = response.get('data', {}).get('data', {})
        if data and 'SignedInvoice' in data:
            return data
        errors = response.get('error', {})
        raise IrnException(errors)

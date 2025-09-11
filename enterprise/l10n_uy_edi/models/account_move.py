import base64
import stdnum.uy
from lxml import etree
from markupsafe import Markup

from odoo import _, api, fields, models

from odoo.exceptions import ValidationError
from odoo.tools import float_repr, float_round, cleanup_xml_node, format_amount, html2plaintext


def format_float(amount, digits=2, valid_zero=None):
    if not amount and not valid_zero:
        return None
    return float_repr(float_round(amount, digits), digits)


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_uy_edi_document_id = fields.Many2one("l10n_uy_edi.document", string="Uruguay E-Invoice CFE", copy=False)
    l10n_uy_edi_addenda_ids = fields.Many2many(
        "l10n_uy_edi.addenda",
        string="Addenda & Disclosure",
        domain="[('type', 'in', ['issuer', 'receiver', 'cfe_doc', 'addenda'])]",
        help="Addendas and Mandatory Disclosure to add on the CFE. They can be added either to the issuer, receiver,"
        " or CFE document's additional information section, or to the addenda section. However, the item type should"
        " not be set in this field; instead, it should be specified in the invoice lines.",
        ondelete="restrict")
    l10n_uy_edi_cfe_sale_mode = fields.Selection(
        string="Sales Modality",
        selection=[
            ("1", "General Regime"),
            ("2", "Consignment"),
            ("3", "Reviewable Price"),
            ("4", "Own goods to customs exclaves"),
            ("90", "General Regime - exportation of services"),
            ("99", "Other transactions"),
        ],
        help="This field is used in the XML to create an Export e-Invoice",
    )
    l10n_uy_edi_cfe_transport_route = fields.Selection(
        string="Transportation Route",
        selection=[
            ("1", "Maritime"),
            ("2", "Air"),
            ("3", "Ground"),
            ("8", "N/A"),
            ("9", "Other"),
        ],
        help="This field is used in the XML to create an Export e-Invoice",
    )

    # Related fields
    l10n_uy_edi_cfe_uuid = fields.Char(related="l10n_uy_edi_document_id.uuid")
    l10n_uy_edi_cfe_state = fields.Selection(related="l10n_uy_edi_document_id.state", store=True)
    l10n_uy_edi_error = fields.Text(related="l10n_uy_edi_document_id.message")
    l10n_uy_edi_journal_type = fields.Selection(related="journal_id.l10n_uy_edi_type")

    # Compute fields
    l10n_uy_edi_is_needed = fields.Boolean(compute="_compute_l10n_uy_edi_is_needed")
    l10n_uy_edi_xml_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Uruguay E-Invoice XML",
        compute="_compute_l10n_uy_edi_xml_attachment_id",
        help="Uruguay: the most recent e-invoice XML returned by Uruware.",
    )

    # Compute method

    def _compute_name(self):
        uy_invoices = self.filtered(
            lambda m: m.l10n_uy_edi_is_needed
            and m.state == "posted"
        )

        super(AccountMove, self - uy_invoices)._compute_name()
        for move in uy_invoices:
            if not move.name or move.name == "/":
                move.name = "* %s" % move.id

    @api.depends("l10n_uy_edi_cfe_state", "country_code", "move_type")
    def _compute_l10n_uy_edi_is_needed(self):
        for move in self:
            move.l10n_uy_edi_is_needed = (
                move.country_code == "UY"
                and move.journal_id.l10n_latam_use_documents
                and move.journal_id.l10n_uy_edi_type == "electronic"
                and move.is_sale_document()
                and (not move.l10n_uy_edi_cfe_state or move.l10n_uy_edi_cfe_state == "error")
            )

    @api.depends("l10n_uy_edi_document_id.state")
    def _compute_l10n_uy_edi_xml_attachment_id(self):
        for move in self:
            doc = move.l10n_uy_edi_document_id
            move.l10n_uy_edi_xml_attachment_id = doc.state == "accepted" and doc.attachment_id

    @api.depends("state", "l10n_uy_edi_document_id.state")
    def _compute_show_reset_to_draft_button(self):
        """ Hide reset to draft button if the edi document has been already processed by DGI """
        # EXTEND from account
        super()._compute_show_reset_to_draft_button()
        for move in self.filtered(
            lambda x: x.country_code == "UY" and x.is_sale_document(include_receipts=True) and x.l10n_uy_edi_document_id
        ):
            move.show_reset_to_draft_button = move.l10n_uy_edi_document_id._can_edit()

    # Constraints method

    @api.constrains("l10n_uy_edi_addenda_ids")
    def _l10n_uy_edi_check_addenda_type_item(self):
        """ avoid letting the user add/create a disclosure of type Product/Service Detail in the Addenda
        and Disclosure field. Product/Service Detail type can only be added in the invoice lines """
        if self.l10n_uy_edi_addenda_ids.filtered(lambda x: x.type == "item"):
            raise ValidationError(_("Product/Service Detail type Disclosure can only be added on invoice lines"))

    # Extend existing methods

    def action_post(self):
        # EXTEND account
        """ If journal configured to auto open the send and print wizard is set then
        will do it. """
        res = super().action_post()
        if any(self.journal_id.mapped("l10n_uy_edi_send_print")):
            return self.action_send_and_print()
        return res

    def button_draft(self):
        """ When an invoice sent to DGI returns errors (e.g., wrong partner or other data issues), users can reset it
        to draft and make corrections. However, changing the partner triggers a validation error because the invoice
        lacks a valid latam document number (only provided by DGI after processing). To avoid this, resetting the
        invoice to draft clears the invoice name, allowing users to fix any errors without triggering the validation
        """
        super().button_draft()
        self.filtered(
            lambda x: x.country_code == "UY" and
            x.journal_id.l10n_uy_edi_type == "electronic" and
            x.is_sale_document() and (
                not x.l10n_uy_edi_document_id or
                x.l10n_uy_edi_document_id.state not in ["received", "accepted", "rejected"]
            )
        ).name = False

    def _is_manual_document_number(self):
        # EXTEND l10n_latam_invoice_document
        """ If we have an UY Sales Manual journal then the document number should always be manually add by the user """
        if self.country_code == 'UY' and self.journal_id.type == 'sale' and self.journal_id.l10n_uy_edi_type == 'manual':
            return True
        return super()._is_manual_document_number()

    def _get_last_sequence(self, relaxed=False, with_prefix=None):
        # EXTEND account
        """ l10n_latam_document_number is required in the view if no highest_name is set and so we provide a dummy one,
        so the user does not have to set the document_number.

        :return: string with the sequence, something like "E-ticket 0000001"""
        res = super()._get_last_sequence(relaxed=relaxed, with_prefix=with_prefix)
        if self.country_code == "UY" and not res and self.l10n_uy_edi_is_needed and self.l10n_latam_document_type_id:
            res = "%s 00000000" % self.l10n_latam_document_type_id.doc_code_prefix
        return res

    def _get_l10n_latam_documents_domain(self):
        # EXTEND l10n_latam_invoice_document
        """ Only return the implemented electronic document types so far if the user want to issue from Odoo """
        self.ensure_one()
        domain = super()._get_l10n_latam_documents_domain()
        if (
            self.country_code == "UY"
            and self.journal_id.type == "sale"
            and self.journal_id.l10n_uy_edi_type == "electronic"
        ):
            domain += [('code', 'in', ["101", "102", "103", "111", "112", "113", "121", "122", "123"])]
        return domain

    # Helpers

    def l10n_uy_edi_action_update_dgi_state(self):
        return self.l10n_uy_edi_document_id.action_update_dgi_state()

    def l10n_uy_edi_action_download_preview_xml(self):
        if self.l10n_uy_edi_document_id.attachment_id:
            return self.l10n_uy_edi_document_id.action_download_file()

    def _l10n_uy_edi_cfe_A_iddoc(self):
        """ XML Section A (Encabezado) """

        if self.invoice_line_ids.product_id.filtered(lambda x: x.type in ("consu", "product")):
            incoterm = self.invoice_incoterm_id.code
        else:
            incoterm = "N/A"
            self.l10n_uy_edi_cfe_transport_route = "8"

        return {
            "FchEmis": fields.Date.to_string(self.date),  # A5
            "MntBruto":  # A10 - Tax Included
                1 if self.line_ids.tax_ids.filtered(lambda x: x.l10n_uy_tax_category == "vat" and x.price_include)
                else None,
            "FmaPago":  # A11: (1 cash, 2 credit). If the payment date is same as invoice date, and payment term only
                # have one line then is cash, if not then credit
                2 if self.invoice_date_due > self.invoice_date or len(self.invoice_payment_term_id.line_ids) > 1
                else 1,
            "FchVenc": fields.Date.to_string(self.invoice_date_due),  # A12
            "ClauVenta": self._l10n_uy_edi_is_expo_cfe() and incoterm or None,  # A13
            "ModVenta": self._l10n_uy_edi_is_expo_cfe() and self.l10n_uy_edi_cfe_sale_mode or None,  # A14
            "ViaTransp": self._l10n_uy_edi_is_expo_cfe() and self.l10n_uy_edi_cfe_transport_route or None,  # A15
            "InfoAdicionalDoc": self.l10n_uy_edi_document_id._get_legends("cfe_doc", self) or None,  # A16
        }

    def _l10n_uy_edi_cfe_A_issuer(self):
        """ XML Section A (Encabezado / Emisor) """
        self.ensure_one()
        edi_doc = self.l10n_uy_edi_document_id
        return {
            "RUCEmisor": stdnum.uy.rut.compact(self.company_id.vat),  # A40
            "RznSoc": self.company_id.name[:150],  # A41
            "CdgDGISucur": self.company_id.l10n_uy_edi_branch_code,  # A47
            "DomFiscal": self.company_id.partner_id._l10n_uy_edi_get_fiscal_address(),  # A48
            "Ciudad": self.company_id.city[:30],  # A49
            "Departamento": self.company_id.state_id.name[:30],  # A50
            "InfoAdicionalEmisor": edi_doc._get_legends("issuer", self) or None,  # A51
        }

    def _l10n_uy_edi_cfe_A_receptor(self):
        """ XML Section A (Encabezado / Receptor) """
        self.ensure_one()
        receptor_required = self.l10n_uy_edi_document_id._cfe_needs_partner_info(self)

        # If we do not have the necessary receiver information, but the receiver information is not required,
        # we will not send it.
        if not self.partner_id.vat and not receptor_required:
            return {}

        doc_type = self.partner_id._l10n_uy_edi_get_doc_type()

        # If we have the information available about the receiver, we send it no matter the case
        # (this is what Uruware does)
        return {
            "TipoDocRecep": doc_type or None,  # A60
            "CodPaisRecep": self.partner_id.country_id.code or ("UY" if doc_type in [2, 3] else "99"),  # A61
            "DocRecep": self.commercial_partner_id.vat if doc_type in [1, 2, 3] else None,  # A62
            "DocRecepExt": self.commercial_partner_id.vat if doc_type not in [1, 2, 3] else None,  # A62.1
            "RznSocRecep": self.commercial_partner_id.name[:150] or None,  # A63
            "DirRecep": self.partner_id._l10n_uy_edi_get_fiscal_address() or None,  # A64
            "CiudadRecep": self.partner_id.city and self.partner_id.city[:30] or None,  # A65
            "DeptoRecep": self.partner_id.state_id and self.partner_id.state_id.name[:30] or None,  # A66
            "PaisRecep": self.partner_id.country_id and self.partner_id.country_id.name or None,  # A66.1
            "InfoAdicional": self.l10n_uy_edi_document_id._get_legends("receiver", self) or None,  # A68
            "CompraID": self.ref and self.ref[:50] or None,  # A70
        }

    def _l10n_uy_edi_cfe_B_details(self, tax_details):
        """ XML Section B (Detalle de Productos y Servicios)

        Check the restriction on the maximum number of lines that we can report, launch a prior exception from Odoo
        to avoid sending and receiving a rejection by DGI if we do not meet the specification.

        :return:  list of the prepare data of each line we are going to inform for the CFE """
        self.ensure_one()
        res = []

        # NOTE: all amounts to be reported must be in the currency of the receipt not in Uruguayan pesos,
        # that is why we use price_subtotal instead of another field

        for k, base_line in enumerate(tax_details['base_lines'], start=1):
            line = base_line['record']
            values = next(iter(tax_details['tax_details_per_record'][line]['tax_details'].values()))
            tax_included = values['_tax_price_include']

            # B4 IndFact
            if self._l10n_uy_edi_is_expo_cfe():
                invoice_ind = 10  # Exportación y asimiladas
            else:
                ind_code = {
                    0.0: 1,   # 1: Exento de IVA
                    10.0: 2,  # 2: Gravado a Tasa Mínima
                    22.0: 3,  # 3: Gravado a Tasa Básica
                }
                # IMPORTANT: By the moment, this is working for one VAT tax per move lines
                invoice_ind = ind_code.get(line.tax_ids.amount)
            if line.discount == 100 and (line.price_total if tax_included else line.price_subtotal) == 0:
                # Entrega Gratuita - We made this in separate if because expo invoices can also have entrega gratuita
                invoice_ind = 5

            item_description = self._l10n_uy_edi_get_line_desc(line)
            nom_item = (line.product_id.display_name or "-")[:80]
            temp = {
                "NroLinDet": k,  # B1
                "IndFact": invoice_ind,  # B4
                "NomItem": nom_item,  # B7
                "DscItem": item_description if item_description and item_description != nom_item else None,  # B8
                "Cantidad": line.quantity,  # B9
                "UniMed": line.product_uom_id.name[:4] if line.product_uom_id else "N/A",  # B10
                "PrecioUnitario": line.price_unit,  # B11
                "DescuentoPct": line.discount,  # B12
                "DescuentoMonto":  # B13
                    (line.quantity * line.price_unit - (line.price_total if tax_included else line.price_subtotal))
                    if line.discount else None,
                "MontoItem": line.price_total if tax_included else line.price_subtotal,  # B24
            }

            if invoice_ind == 5:
                temp.update({}.fromkeys(['PrecioUnitario', 'DescuentoMonto', 'DescuentoPct'], 0.0))

            res.append(temp)
        return res

    def _l10n_uy_edi_cfe_C_totals(self, tax_details):
        """ XML Section C (SUBTOTALES INFORMATIVOS) """
        self.ensure_one()
        currency_name = self.currency_id.name if self.currency_id else self.company_id.currency_id.name

        expo_doc = self._l10n_uy_edi_is_expo_cfe()

        neto = {10.0: 0.0, 22.0: 0.0, 0.0: 0.0}
        base = neto.copy()
        for grouping_key, tax_dict in tax_details['tax_details'].items():
            neto[grouping_key['_tax_amount']] = tax_dict['base_amount_currency']
            base[grouping_key['_tax_amount']] = tax_dict['tax_amount_currency']

        res = {
            "TpoMoneda": currency_name,  # A110
            "TpoCambio": None if currency_name == "UYU" else self._l10n_uy_edi_get_used_rate(),  # A111
            "MntExpoyAsim": self.amount_total if expo_doc else None,  # A113
            "MntNoGrv": neto[0.0] if not expo_doc else None,  # A112
            "MntNetoIvaTasaMin": neto[10.0] if not expo_doc else None,  # A116
            "IVATasaMin": 10 if not expo_doc and neto[10.0] else None,  # A119
            "MntNetoIVATasaBasica": neto[22.0] if not expo_doc else None,  # A117
            "IVATasaBasica": 22 if not expo_doc and neto[22.0] else None,  # A120
            "MntIVATasaMin": base[10.0] if not expo_doc else None,  # A121
            "MntIVATasaBasica": base[22.0] if not expo_doc else None,  # A122
            "MntTotal": self.amount_total,  # A124
            "CantLinDet": len(self.invoice_line_ids.filtered(lambda x: x.display_type == "product")),  # A126
            "MntPagar": self.amount_total,  # A130
        }
        return res

    def _l10n_uy_edi_cfe_F_reference(self):
        """ XML Section F (REFERENCE INFORMATION). If is a debit/credit note cfe then we need to inform the reference tag """
        res = []
        if self.l10n_latam_document_type_id.internal_type in ["credit_note", "debit_note"]:
            related_doc = self._l10n_uy_edi_found_related_cfe()
            for k, related_cfe in enumerate(related_doc, 1):
                cfe_serie, cfe_number = self.l10n_uy_edi_document_id._get_doc_parts(related_cfe)
                res.append({
                    "NroLinRef": k,  # F1
                    "TpoDocRef": int(related_cfe.l10n_latam_document_type_id.code),  # F3
                    "Serie": cfe_serie,  # F4
                    "NroCFERef": cfe_number,  # F5
                })
        return res

    def _l10n_uy_edi_check_move(self):
        """ Need to fullfil next conditions:

        * Check receiver has a valid identification number
        * Check that we do not sent any tax on exportation invoices
        * Check that domestic CFE always has a vat tax per line
        * Check that Doc type is set and is a valid one
        * Check that the Partner address info is set if required for the doc type

        return: an error list if the minimal conditions to be a valid CFE does not fulfill """
        self.ensure_one()
        errors = []
        if not (self.company_id.country_code == "UY" and self.l10n_latam_use_documents):
            return errors

        edi_model = self.env["l10n_uy_edi.document"]

        # Check Issuer data
        if config_errors := self.company_id._l10n_uy_edi_validate_company_data():
            errors.append(_(
                "To create the CFE document first complete your company data (%(company_name)s):\n\t- %(errors)s",
                errors="\n\t- ".join(config_errors),
                company_name=self.company_id.name))

        # Check Uruware Config
        if msg := edi_model._is_connection_info_incomplete(self.company_id):
            errors.append(msg)

        # Check receiver has a valid identification number
        try:
            self.partner_id.check_vat()
        except ValidationError as exp:
            errors.append(_("Problem with Receiver identification number: %(exp_msg)s", exp_msg=str(exp)))

        # Check currency configuration works to be able to report to DGI
        uy_edi_currencies = [
            # partial iso 4217
            "ARS", "BRL", "CAD", "CLP", "CNY", "COP", "EUR", "JPY", "MXN", "PYG", "PEN", "USD", "UYU", "VEF",
            # other_currencies
            "UYI", "UYR",
        ]
        currency_names = self.currency_id.mapped("name") + self.company_id.currency_id.mapped("name")
        for currency_name in currency_names:
            if currency_name not in uy_edi_currencies:
                errors.append(_("The currency does not exist on DGI currencies table %s", currency_name))

        # Rates Configuration
        if self.currency_id and self.currency_id.name != "UYU":
            used_rate = self._l10n_uy_edi_get_used_rate()
            if used_rate <= 0.0:
                errors.append(_(
                    "Not valid Currency Rate, need to be greater than 0 to be accepted by DGI"
                    " (%(used_rate)s)", used_rate=used_rate)
                )

        # If debit or credit, we need to ensure that the original related document exists and is accepted by DGI
        if self.l10n_latam_document_type_id.internal_type in ["credit_note", "debit_note"]:
            related_doc = self._l10n_uy_edi_found_related_cfe()
            if not related_doc:
                errors.append(_("To validate a DN/CN the original document should be informed"))
            if not int(related_doc.l10n_latam_document_type_id.code):
                errors.append(_("To validate a DN/CN the original document should be informed and it should be electronic"))

        # For e-Ticket and related DN/CN max lines <= 700
        lines = self.invoice_line_ids.filtered(lambda x: x.display_type not in ("line_section", "line_note"))
        if self.l10n_latam_document_type_id.code in [101, 102, 103, 131, 132, 133] and len(lines) > 700:
            errors.append(_("For e-Ticket and related DN and CN you can only report up to 700 lines"))
        elif len(lines) > 200:  # Other CFE types: Max 200
            errors.append(_("For this type of CFE you can only report up to 200 lines"))

        # We check that not other taxes are being used (not supported for EDI)
        if not_supported_taxes := lines.tax_ids.filtered(lambda x: x.l10n_uy_tax_category != "vat"):
            errors.append(_(
                "Not valid Uruguayan tax, only VAT taxes are supported (%(taxes_name)s)",
                taxes_name=', '.join(not_supported_taxes.mapped('name'))),
            )

        # Check expo conditions
        expo_doc = int(self.l10n_latam_document_type_id.code) in [121, 122, 123]
        # Where: 121 "Export e-Invoice" / 122 "Export e-Invoice Credit Note" / 123 "Export e-Invoice Debit Note"
        # Ensure required fields for expo invoices
        if expo_doc:
            missing_expo_fields = []
            has_products = self.invoice_line_ids.product_id.filtered(lambda x: x.type in ("consu", "product"))
            if has_products and not self.invoice_incoterm_id:
                missing_expo_fields.append("Incoterm")
            if not self.l10n_uy_edi_cfe_sale_mode:
                missing_expo_fields.append("Sales Modality")
            if has_products and not self.l10n_uy_edi_cfe_transport_route:
                missing_expo_fields.append("Transportation Route")

            if missing_expo_fields:
                errors.append(_(
                    "To report an export invoice you must fill the next fields. "
                    "You can indicate this value in the Other Information tab: "
                    " \n\t * %s", "\n\t * ".join(missing_expo_fields)))

        # Check lines
        for line in lines:
            errors += edi_model._check_field_size("B8_DscItem", self._l10n_uy_edi_get_line_desc(line), 1000)
            # We check that there is one and o nly one vat tax per line
            vat_taxes = line.tax_ids.filtered(lambda x: x.l10n_uy_tax_category == "vat")
            if len(vat_taxes) != 1:
                errors.append(_(
                    "All lines should have a VAT tax (only one per line). "
                    "Check line '%(line_name)s' (Id Invoice: %(move_id)s)",
                    line_name=line.product_id.name or line.name,
                    move_id=line.move_id.id,
                ))
            elif expo_doc:
                if line.tax_ids.amount != 0.0:
                    errors.append(_(
                        "Export CFE can only have 0%% vat taxes. Check line '%(line_name)s' (Id Invoice: %(move_id)s)",
                        line_name=line.product_id.name,
                        move_id=line.move_id.id,
                    ))

        # Check the type of vat taxes used (all included or not included)
        taxes = self.line_ids.tax_ids.filtered(lambda t: t.l10n_uy_tax_category == "vat")
        tax_included = set(taxes.mapped("price_include"))
        if tax_included and len(tax_included) != 1:
            errors.append(_("You cannot combine included and not included taxes on the same invoice"))

        # Check the receiver info depending on the doc type
        edi_model = self.env["l10n_uy_edi.document"]
        document_type = int(self.l10n_latam_document_type_id.code)
        cond_e_fact = document_type in [111, 112, 113, 141, 142, 143]
        # Where:
        # 111 e-Invoice
        # 112 e-Invoice Credit Note
        # 113 e-Invoice Debit Note
        # 141 e-Invoice Sale By Third Party
        # 142 e-Invoice Sale By Third Party Credit Note
        # 143 e-Invoice Sale By Third Party Debit Note
        cond_e_ticket = document_type in [101, 102, 103, 131, 132, 133]
        # Where:
        # 101 e-Ticket
        # 102 e-Ticket Credit Note
        # 103 e-Ticket Debit Note
        # 131 e-Ticket Sale By Third Party
        # 132 e-Ticket Sale By Third Party Credit Note
        # 133 e-Ticket Sale By Third Party Debit Note

        cond_e_fact_expo = self._l10n_uy_edi_is_expo_cfe()
        receptor_required = edi_model._cfe_needs_partner_info(self)
        doc_type = self.partner_id._l10n_uy_edi_get_doc_type()
        min_amount = edi_model._get_minimum_legal_amount(self.company_id, self.date)

        if min_amount == 1.0:
            errors.append(_("You need to have UYI rate before validating invoices"))

        if not doc_type:
            errors.append(_("%(dtype)s is not an Uruguayan Identification Type or "
                            "a Generic one (VAT, Passport, or Foreign ID). You need to select a valid ID to be able "
                            "to invoice", dtype=self.partner_id.l10n_latam_identification_type_id.name))

        # Validations to have all the receiver data if the receiver is required
        if receptor_required:
            if not self.partner_id.l10n_latam_identification_type_id:
                errors.append(_("The partner of the CFE needs to have an Identification Type"))

        if cond_e_fact_expo or cond_e_fact or (cond_e_ticket and receptor_required):
            if not all([self.partner_id.street, self.partner_id.city, self.partner_id.state_id,
                        self.partner_id.country_id, self.partner_id.vat]):
                msg = _("You need to fill in the receiver details: address, city, province, country and ID number")
                if cond_e_ticket:
                    msg += _(
                        "\n\nNOTE: This is required since the e-Ticket exceeds the minimum amount."
                        "\nMinimum amount = 5000 Uruguayan Indexed Unit (>%(min_amount)s)",
                        min_amount=format_amount(self.env, min_amount, self.company_currency_id),
                    )
                errors.append(msg)

        # Check field length of special tags that have mandatory disclosure included and warn the user if the text
        # length is more that the MAX (this way we avoid that mandatory disclosure can result incomplete on the XML,
        # we need this validation because the mandatory disclosure have legal implication, and we need to ensure
        # that all the needed text is in the CFE)
        errors += edi_model._check_field_size(
            "A51_InfoAdicionalEmisor", edi_model._get_legends("issuer", self) or None, 150)
        errors += edi_model._check_field_size(
            "A16_InfoAdicionalDoc", edi_model._get_legends("cfe_doc", self) or None, 150)
        errors += edi_model._check_field_size(
            "A68_InfoAdicional", edi_model._get_legends("receiver", self) or None, 150)

        # Check that the document type has been implemented, if not do not let the user create the doc
        if not edi_model._get_cfe_tag(self):
            errors.append(_("This CFE is not implemented yet %(doc_name)s", doc_name=self.l10n_latam_document_type_id.display_name))
        return errors

    def _l10n_uy_edi_cron_update_dgi_status(self, batch_size=10):
        res = self.search([("l10n_uy_edi_cfe_state", "=", "received"), ("journal_id.type", "=", "sale")])
        res[:batch_size].l10n_uy_edi_document_id.action_update_dgi_state()
        if len(res) > batch_size:
            self.env.ref("l10n_uy_edi.ir_cron_update_dgi_state")._trigger()

    def _l10n_uy_edi_dummy_validation(self):
        """ When we want to skip DGI and validate only in Odoo """
        self.l10n_uy_edi_document_id.state = "accepted"
        self.write({
            "l10n_latam_document_number": "DE%07d" % self.id,
            "ref": "*DEMO",
        })
        return self._l10n_uy_edi_get_preview_xml()

    def _l10n_uy_edi_found_related_cfe(self):
        """ Return the related/origin CFE of a given CFE. """
        self.ensure_one()
        res = self.env["account.move"]
        if self.l10n_latam_document_type_id.internal_type == "credit_note":
            res = self.reversed_entry_id
        elif self.l10n_latam_document_type_id.internal_type == "debit_note":
            res = self.debit_origin_id
        if res:
            if res.l10n_uy_edi_cfe_state != "accepted":
                res.l10n_uy_edi_document_id.action_update_dgi_state()
        return res

    def _l10n_uy_edi_get_addenda(self):
        """ return string with the addenda """
        addenda = self.l10n_uy_edi_document_id._get_legends("addenda", self)
        if self.narration:
            term_and_conditions = html2plaintext(self.narration)
            addenda = addenda + "\n\n" + term_and_conditions if addenda else term_and_conditions
        return addenda

    def _l10n_uy_edi_get_line_desc(self, aml):
        # B8 DscItem
        item_description = ["{ %s }" % addenda.content if addenda.is_legend else addenda.content
                            for addenda in aml.l10n_uy_edi_addenda_ids]
        if aml.name and aml.product_id.display_name != aml.name:
            item_description.append(aml.name)
        item_description = "\n".join(item_description)
        return item_description

    def _l10n_uy_edi_get_pdf(self):
        """ Call endpoint to get PDF file from Uruware (Standard Representation)
        return: dictionary with {"errors": str(): "pdf_file"attachment object } """
        res = {}
        if "out" not in self.move_type or self.journal_id.l10n_uy_edi_type != "electronic":
            return {"errors": _("Only can get the legal representation of the CFE for customer electronic invoices")}

        result = self.l10n_uy_edi_document_id._get_pdf()

        if file_content := result.get("file_content"):
            pdf_file = self.env["ir.attachment"].create({
                "res_model": "account.move",
                "res_id": self.id,
                "res_field": "invoice_pdf_report_file",
                "name": (self.name or _("INV")).replace("/", "_") + ".pdf",
                "type": "binary",
                "datas": file_content,
            })
            res["pdf_file"] = pdf_file

        return res

    def _l10n_uy_edi_get_preview_xml(self):
        self.ensure_one()
        edi_doc = self.l10n_uy_edi_document_id
        edi_doc.attachment_id.res_field = False
        xml_file = self.env["ir.attachment"].create({
            "res_model": "l10n_uy_edi.document",
            "res_field": "attachment_file",
            "res_id": edi_doc.id,
            "name": edi_doc._get_xml_attachment_name(),
            "type": "binary",
            "datas": base64.b64encode(self._l10n_uy_edi_get_xml_content().encode()),
        })
        edi_doc.invalidate_recordset(["attachment_id", "attachment_file"])
        return xml_file

    def _l10n_uy_edi_get_used_rate(self):
        self.ensure_one()
        if self.amount_total == 0.0:
            return self.currency_id._convert(
                1.0, self.company_id.currency_id, self.company_id, self.date or fields.Date.today(), round=False)
        # We need to use abs to avoid error on Credit Notes (amount_total_signed is negative)
        return abs(self.amount_total_signed) / self.amount_total

    def _l10n_uy_edi_get_xml_content(self):
        """ Create the CFE xml structure and validate it
            :return: string the xml content to send to DGI """
        self.ensure_one()

        def grouping_key_generator(base_line, tax_data):
            tax = tax_data['tax']
            return {
                'l10n_uy_tax_category': tax.l10n_uy_tax_category,
                '_tax_amount': tax.amount,
                '_tax_price_include': tax.price_include,
            }

        tax_details = self._prepare_invoice_aggregated_taxes(grouping_key_generator=grouping_key_generator)
        template_name = "l10n_uy_edi." + self.l10n_uy_edi_document_id._get_cfe_tag(self) + "_template"
        cfe = self.env["ir.qweb"]._render(template_name, values={
            "cfe": self,
            "IdDoc": self._l10n_uy_edi_cfe_A_iddoc(),
            "emisor": self._l10n_uy_edi_cfe_A_issuer(),
            "receptor": self._l10n_uy_edi_cfe_A_receptor(),
            "item_detail": self._l10n_uy_edi_cfe_B_details(tax_details),
            "totals_detail": self._l10n_uy_edi_cfe_C_totals(tax_details),
            "referencia_lines": self._l10n_uy_edi_cfe_F_reference(),
            "format_float": format_float,
        })
        return etree.tostring(cleanup_xml_node(cfe)).decode()

    def _l10n_uy_edi_is_expo_cfe(self):
        """ True of False if the CFE is an Export type """
        self.ensure_one()
        return int(self.l10n_latam_document_type_id.code) in [121, 122, 123]

    def _l10n_uy_edi_prepare_req_data(self):
        """ Creating dictionary with the request to generate a DGI EDI document """
        self.ensure_one()
        edi_doc = self.l10n_uy_edi_document_id
        xml_content = self._l10n_uy_edi_get_xml_content()
        req_data = {
            "Uuid": edi_doc.uuid,
            "TipoCfe": int(self.l10n_latam_document_type_id.code),
            "HoraReq": edi_doc.request_datetime.strftime("%H%M%S"),
            "FechaReq": edi_doc.request_datetime.date().strftime("%Y%m%d"),
            "CfeXmlOTexto": xml_content}

        if addenda := self._l10n_uy_edi_get_addenda():
            req_data["Adenda"] = addenda
        return req_data

    def _l10n_uy_edi_send(self):
        """ Create CFE Document and send it to Uruware """
        for move in self:
            move.l10n_uy_edi_document_id.filtered(lambda doc: doc.state == "error").unlink()
            edi_doc = self.env['l10n_uy_edi.document'].create({
                "move_id": move.id,
                "uuid": self.env['l10n_uy_edi.document']._get_uuid(move),
            })
            move.l10n_uy_edi_document_id = edi_doc

            if move.company_id.l10n_uy_edi_ucfe_env == "demo":
                attachments = move._l10n_uy_edi_dummy_validation()
                msg = _("This CFE has been generated in DEMO Mode. It is considered as accepted and it won\"t be sent to DGI.")
            else:
                request_data = move._l10n_uy_edi_prepare_req_data()
                result = edi_doc._send_dgi(request_data)
                edi_doc._update_cfe_state(result)

                response = result.get("response")

                if edi_doc.message:
                    move.message_post(
                        body=Markup("<font style='color:Tomato;'><strong>{}:</strong></font> <i>{}</<i>").format(("ERROR"), edi_doc.message)
                    )
                elif edi_doc.state in ["received", "accepted"]:
                    # If everything is ok we save the return information
                    move.l10n_latam_document_number = \
                        response.findtext(".//{*}Serie") + "%07d" % int(
                            response.findtext(".//{*}NumeroCfe"))

                    msg = response.findtext(".//{*}MensajeRta", "")
                    msg += _("The electronic invoice was created successfully")

                if response is not None:
                    attachments = move._l10n_uy_edi_update_xml_and_pdf_file(response)

            if edi_doc.state in ["received", "accepted", "rejected"]:
                move.with_context(no_new_invoice=True).message_post(
                    body=msg,
                    attachment_ids=attachments.ids if attachments else False,
                )

    def _l10n_uy_edi_update_xml_and_pdf_file(self, response):
        """ Clean up the pdf and xml fields. Create new ones with the response """
        self.ensure_one()
        res_files = self.env["ir.attachment"]
        edi_doc = self.l10n_uy_edi_document_id

        self.invoice_pdf_report_id.res_field = False
        edi_doc.attachment_id.res_field = False

        xml_content = response.findtext(".//{*}XmlCfeFirmado")
        if xml_content:
            res_files = self.env["ir.attachment"].create({
                "res_model": "l10n_uy_edi.document",
                "res_field": "attachment_file",
                "res_id": edi_doc.id,
                "name": edi_doc._get_xml_attachment_name(),
                "type": "binary",
                "datas": base64.b64encode(
                    xml_content.encode() if self.l10n_uy_edi_cfe_state in ["received", "accepted"]
                    else self._l10n_uy_edi_get_xml_content().encode()
                ),
            })

            edi_doc.invalidate_recordset(["attachment_id", "attachment_file"])

            # If the record has been posted automatically print and attach the legal report to the record.
            if self.l10n_uy_edi_cfe_state and self.l10n_uy_edi_cfe_state != "error":
                pdf_result = self._l10n_uy_edi_get_pdf()
                if pdf_file := pdf_result.get("pdf_file"):
                    # make sure latest PDF shows to the right of the chatter
                    pdf_file.register_as_main_attachment(force=True)
                    self.invalidate_recordset(fnames=["invoice_pdf_report_id", "invoice_pdf_report_file"])
                    res_files |= pdf_file
                if errors := pdf_result.get("errors"):
                    msg = _("Error getting the PDF file: %s", errors)
                    self.l10n_uy_edi_error = (self.l10n_uy_edi_error or "") + msg
                    self.message_post(body=msg)
        else:
            self._l10n_uy_edi_get_preview_xml()
        return res_files

    def _compute_l10n_latam_document_type(self):
        """
        The following considerations apply for determining document types based on the partner's identification:
        RUT/RUC (Uruguay): Automatically select e-factura.
        Other documents (Example: CI, PAS, NIE, NIFE, etc.): Automatically select e-ticket
        """
        if uy_einvoices := self.filtered(lambda m: m.country_code == 'UY' and
            m.move_type in ('out_invoice', 'out_refund') and
            m.state == 'draft' and
            not m.posted_before and
            m.journal_id.l10n_uy_edi_type == 'electronic' and
            m.partner_id.l10n_latam_identification_type_id == self.env.ref('l10n_uy.it_rut')):
            uy_einvoices.l10n_latam_document_type_id = self.env.ref('l10n_uy.dc_e_inv')
        super(AccountMove, self - uy_einvoices)._compute_l10n_latam_document_type()

import logging
from lxml import etree
import re
from requests.exceptions import Timeout, ConnectionError, HTTPError

from odoo import _, api, fields, models

from odoo.tools import float_compare
from odoo.tools.zeep import Client, Settings
from odoo.tools.zeep.wsse.username import UsernameToken


RESPONSE_CODE_TO_STATE = {
    # Irreversible states
    "00": "accepted",  # Petición aceptada y procesada
    "06": "accepted",  # CFE observado por DGI
    "11": "received",  # CFE aceptado por UCFE, en espera de respuesta de DGI
    "05": "rejected",  # CFE rechazado por DGI (Anulado). Do not sent again to UCFE neither create CREDIT NOTES

    # Errors
    "01": "error",  # Petición denegada

    # Related to configuration of UCFE. Please fix it and then try to send CFE again
    "03": "error",  # Comercio inválido
    "89": "error",  # Terminal inválida

    # UCFE does not receive the CFE
    "12": "error",  # Requerimiento inválido
    "94": "error",
    "99": "error",  # Sesión no iniciada

    "30": "error",  # Error en formato (Format error on the query)
    "31": "error",  # Error en formato de CFE (Fortmat error of the xml)
    "96": "error",  # Error en sistema (UFCE Internal error). Example: Bugs, down database, disk full, etc.
}

_logger = logging.getLogger(__name__)


class L10nUyEdiDocument(models.Model):
    _name = "l10n_uy_edi.document"
    _description = "Electronic Fiscal Document (CFE - UY)"
    _rec_name = "l10n_latam_document_number"

    uuid = fields.Char(
        string="Key or UUID CFE",
        copy=False,
        readonly=True,
        help="Unique identification per CFE in UCFE: concatenation of the model name initials plus the record id",
    )
    request_datetime = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True)
    state = fields.Selection(
        string="CFE Status",
        selection=[
            ("received", "Waiting response from DGI"),
            ("accepted", "CFE Accepted by DGI"),
            ("rejected", "CFE Rejected by DGI"),
            ("error", "ERROR")
        ],
        copy=False,
        readonly=True,
        help="State of the electronic document",
    )
    move_id = fields.Many2one("account.move", readonly=True)
    message = fields.Text(
        string="Uruguay E-Invoice Error",
        copy=False,
        readonly=True,
        help="error details for CFEs in the 'error' state.",
    )
    # Attachment
    attachment_id = fields.Many2one(
        "ir.attachment",
        compute=lambda self: self._compute_linked_attachment_id("attachment_id", "attachment_file"),
        depends=["attachment_file"],
    )
    attachment_file = fields.Binary(copy=False, attachment=True)

    # Related fields from origin record
    l10n_latam_document_type_id = fields.Many2one(related="move_id.l10n_latam_document_type_id")
    l10n_latam_document_number = fields.Char(related="move_id.l10n_latam_document_number")
    company_id = fields.Many2one(related="move_id.company_id")
    partner_id = fields.Many2one(related="move_id.partner_id")

    # Compute methods

    def _compute_linked_attachment_id(self, attachment_field, binary_field):
        """Helper to retrieve Attachment from Binary fields
        This is needed because fields.Many2one("ir.attachment") makes all
        attachments available to the user.
        """
        attachments = self.env["ir.attachment"].search([
            ("res_model", "=", self._name),
            ("res_id", "in", self.ids),
            ("res_field", "=", binary_field)
        ])
        edi_vals = {att.res_id: att for att in attachments}
        for edi_doc in self:
            edi_doc[attachment_field] = edi_vals.get(edi_doc._origin.id, False)

    # Action Methods

    def action_download_file(self):
        """ Be able to download the XML file related to this EDI document

        * If document received/accepted it will be the valid CFE
        * If document is in error state will download the preview of the XML that we are trying to send to
        Uruware-DGI """
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{self.attachment_id.id}?download=true",
        }

    def action_update_dgi_state(self):
        """ Call endpoint that return the updated state of the EDI document on DGI.
        Make a query to UCFE in order to know if DGI give us a definitive state for the invoice (Used only for all the
        electronic invoices that are state waiting DGI response). Only applies to customer invoices

        Will return None and the result will be update the cfe_state field (error field
        if applies)"""
        for edi_doc in self:
            result = edi_doc._ucfe_inbox("360", {"Uuid": edi_doc.uuid})
            edi_doc._update_cfe_state(result)

    # Extended methods

    def unlink(self):
        self.attachment_id.unlink()
        return super().unlink()

    # Helpers

    def _can_edit(self):
        """ The CFE cannot be modified once processed by DGI """
        self.ensure_one()
        return self.state not in ["accepted", "rejected", "received"]

    @api.model
    def _cfe_needs_partner_info(self, move):
        """ Whether the partner address is required.
        For e-ticket, if the amount is less than 5000 UYI, it's optional. """
        move.ensure_one()
        document_type = int(move.l10n_latam_document_type_id.code)
        min_amount = self._get_minimum_legal_amount(move.company_id, move.date)
        return (
            document_type in [101, 102, 103, 131, 132, 133]
            and float_compare(abs(move.amount_total_signed), min_amount, precision_digits=2) == 1
        )

    @api.model
    def _validate_credentials(self, company):
        """ Make a ECHO test to UCFE to see if the server is running and that the environment
        params have been properly configured """
        error = self.env["l10n_uy_edi.document"]._is_connection_info_incomplete(company)
        if error:
            return error

        company_missing_data = company._l10n_uy_edi_validate_company_data()
        if company_missing_data:
            return _(
                "Not able to check credentials, first complete your company data:\n\t- %(errors)s",
                errors="\n\t- ".join(company_missing_data),
            )

        now = fields.Datetime.now()
        result = self._ucfe_inbox("820", {"FechaReq": now.date().strftime("%Y%m%d"), "HoraReq": now.strftime("%H%M%S")})
        if errors := result.get("errors"):
            return "\n".join(errors)
        return ""

    @api.model
    def _check_field_size(self, field_name, res, limit):
        errors = []
        if res and len(res) > limit:
            errors.append(_(
                "We cannot generate the CFE because the field length is not valid.\nCheck if disclosure/addenda are"
                " being applied.\n\n * Name of the field: %(xml_tag)s (%(xml_tag_len)s)\n * Content:"
                " (%(value_len)s)\n %(value_content)s",
                xml_tag=field_name, xml_tag_len=limit, value_len=len(res), value_content=res))
        return errors

    @api.model
    def _get_cfe_tag(self, move):
        move.ensure_one()
        cfe_code = int(move.l10n_latam_document_type_id.code)
        if cfe_code in [101, 102, 103, 201]:
            return "eTck"
        elif cfe_code in [111, 112, 113]:
            return "eFact"
        elif cfe_code in [121, 122, 123]:
            return "eFact_Exp"
        else:
            return False

    @api.model
    def _get_doc_parts(self, record):
        """ return list [serie, number] """
        return re.findall(r"([A-Z])[-]*([0-9]*)", record.l10n_latam_document_number)[-1]

    @api.model
    def _get_legends(self, addenda_type, move_id):
        """ This method check return the legends and info to be used per xml tag. also will automatically add ̱̰{ } to
        the legends when needed, which indicates Uruware the presence
        of Mandatory Disclosure
        Return type: string  """
        res = []
        addendas = move_id.l10n_uy_edi_addenda_ids.filtered(lambda x: x.type == addenda_type)
        for addenda in addendas:
            res.append("{ %s }" % addenda.content if addenda.is_legend else addenda.content)
        return "\n".join(res)

    @api.model
    def _get_minimum_legal_amount(self, company, date):
        """ Converts 50000 UYI in the company currency """
        return self.env.ref("base.UYI")._convert(50000, company.currency_id, company=company, date=date)

    def _get_pdf(self):
        """ Connect to Uruware with the info of CFE and return the corresponding PDF file
        Legal representation.
        return: {"errors"; strg(), "file_content": bytes string file content}"""
        res = {}
        document_number = re.search(r"([A-Z]*)([0-9]*)", self.l10n_latam_document_number).groups()
        req_data = {
            "rut": self.company_id.partner_id.vat,
            "tipoCfe": int(self.l10n_latam_document_type_id.code),
            "serieCfe": document_number[0],
            "numeroCfe": document_number[1],
        }
        report_params, extra_params = self._get_report_params()
        req_data.update(extra_params)

        result = self._ucfe_query(report_params, req_data)
        response = result.get("response")

        if response is not None:
            res.update({"file_content": response.findtext(".//{*}ObtenerPdfResult").encode()})

        if result.get("errors"):
            res.update({"errors": result.get("errors")})

        return res

    def _get_report_params(self):
        """ Print the default representation of the PDF report, extra params not needed.
        This has been implemented in a separate method to be inheritable for some
        partner and customer custom reports """
        return "ObtenerPdf", {}

    def _get_ucfe_username(self, company):
        return re.sub("[^0-9]", "", company.vat) if company.vat else False

    def _get_uuid(self, move):
        """ Uruware UUID to identify the edi document and also A4.1 (NroInterno) DGI field. Spec (V24) ALFA50.
        We did not make it as default value because we need the move to set """
        res = move._name + "-" + str(move.id)
        if move.company_id.l10n_uy_edi_ucfe_env == "testing":
            res = "am" + str(move.id) + "-" + self.env.cr.dbname
        return res[:50]

    def _get_ws_url(self, ws_endpoint, company):
        """
        Get the Uruware endpoint to be called, or False if we are in demo mode.
        The endpoints are read from the config parameters:
        * `l10n_uy_edi.l10n_uy_edi_ucfe_inbox_url`
        * `l10n_uy_edi.l10n_uy_edi_ucfe_query_url`

        :param ws_endpoint: "inbox" or "query"
        :param company: res.company
        """
        if company.l10n_uy_edi_ucfe_env == "demo":
            return False
        elif company.l10n_uy_edi_ucfe_env == 'production':
            base_url = "https://prod6109.ucfe.com.uy/"
        else:
            base_url = "https://odootest.ucfe.com.uy/"

        if ws_endpoint == "inbox":
            url = self.env["ir.config_parameter"].sudo().get_param(
                key="l10n_uy_edi.l10n_uy_edi_ucfe_inbox_url",
                default=base_url + "inbox115/cfeservice.svc",
            )
            pattern = r"https://.*\.ucfe\.com\.uy/inbox.*/cfeservice\.svc"
        elif ws_endpoint == "query":
            url = self.env["ir.config_parameter"].sudo().get_param(
                key="l10n_uy_edi.l10n_uy_edi_ucfe_query_url",
                default=base_url + "query116/webservicesfe.svc",
            )
            pattern = r"https://.*\.ucfe\.com\.uy/query.*/webservicesfe\.svc"
        else:
            url = pattern = None

        return url if re.match(pattern, url, re.IGNORECASE) is not None else False

    def _get_xml_attachment_name(self):
        if self and self.move_id.company_id.l10n_uy_edi_ucfe_env == "demo":
            return "demo-cfe-%s.xml" % self.l10n_latam_document_number
        if self.state in ["received", "accepted"]:
            return f"CFE_{self.l10n_latam_document_number}.xml"
        return "preview-cfe-move-%s.xml" % self.move_id.id

    @api.model
    def _is_connection_info_incomplete(self, company):
        """ False if everything is ok, Message if there is a problem or something missing """
        if company.l10n_uy_edi_ucfe_env == "demo":
            return False

        field_data = company.fields_get([])
        missing_info = []
        for field in (
            "l10n_uy_edi_ucfe_env",
            "l10n_uy_edi_ucfe_password",
            "l10n_uy_edi_ucfe_commerce_code",
            "l10n_uy_edi_ucfe_terminal_code",
        ):
            if not company[field]:
                missing_info.append(field_data[field]["string"])
        inbox_url = self._get_ws_url("inbox", company)
        if not inbox_url:
            missing_info.append(_("Uruware Inbox URL"))
        query_url = self._get_ws_url("query", company)
        if not query_url:
            missing_info.append(_("Uruware Query URL"))
        username = self._get_ucfe_username(company)
        if not username:
            missing_info.append(_("Uruware Username"))

        if missing_info:
            return _(
                "Incomplete Data to connect to Uruware on company %(company)s: Please complete the UCFE data to test "
                "the connection: %(missing)s",
                company=company.name,
                missing=", ".join(missing_info),
            )

        return False

    @api.model
    def _process_response(self, soap_response, errors):
        response_tree = False
        if errors and soap_response is None:
            return {"errors": errors}
        if soap_response is None:
            return {"errors": _("No response")}

        if soap_response.content is None:
            return {"errors": _("EMPTY response")}

        try:
            response_tree = etree.fromstring(soap_response.content)
        except etree.LxmlError as exp:
            return {"errors": _("Error processing the response %(exp_rep)s", exp_rep=str(exp))}

        # Capture any other errors in the connection
        if response_tree is not None:
            error_code = response_tree.findtext(".//{*}ErrorCode")
            if error_code and int(error_code):
                error_msg = response_tree.findtext(".//{*}ErrorMessage")
                errors.append(_("Response Error - Code: %(code)s %(msg)s", code=error_code, msg=error_msg or ""))
            if fault_string := response_tree.findtext(".//{*}faultstring"):
                errors.append(_("Fault Error - %(msg)s", msg=fault_string))

        return {"response": response_tree, "errors": errors}

    def _send_dgi(self, request_data):
        """ Call endpoint that lets us post a DGI Invoice (310 - Signature and sending of CFE (individual)) """
        self.ensure_one()
        return self._ucfe_inbox("310", request_data)

    def _ucfe_inbox(self, msg_type, extra_req):
        """ Call Operation on UCFE inbox webservice
        :param msg_type: integer that represents the query we are going to call. For instance:
            360 - Check CFE State
            310 - Create CFE on DGI (send)
            820 - Check Credentials
        :returns: dictionary ({"response" etree obj }, "errors": str()) """
        now = fields.Datetime.now()
        company = self.company_id or self.env.company
        data = {
            "CodComercio": company.l10n_uy_edi_ucfe_commerce_code,
            "CodTerminal": company.l10n_uy_edi_ucfe_terminal_code,
            "RequestDate": now.replace(microsecond=0).isoformat(),
            "Tout": "30000",
            "Req": {
                "TipoMensaje": msg_type,
                "CodComercio": company.l10n_uy_edi_ucfe_commerce_code,
                "CodTerminal": company.l10n_uy_edi_ucfe_terminal_code,
                "IdReq": 1,
                **extra_req,
            },
        }
        return self._ucfe_ws_call(company, "inbox", "Invoke", [data])

    def _ucfe_query(self, method, req_data):
        """ Call Query on UCFE Query Webservices """
        company = self.company_id or self.env.company
        return self._ucfe_ws_call(company, "query", method, **req_data)

    def _ucfe_ws_call(self, company, endpoint, method, *args, **kwargs):
        response = None
        errors = []
        url = self._get_ws_url(endpoint, company)

        if not url.endswith("?wsdl"):
            url += "?wsdl"
        try:
            username_token = UsernameToken(self._get_ucfe_username(company), company.l10n_uy_edi_ucfe_password)
            client = Client(url, wsse=username_token, settings=Settings(raw_response=True))
            if args:
                response = client.service[method](*args)
            else:
                response = client.service[method](**kwargs)
        except (Timeout, ConnectionError, HTTPError) as exp:
            errors.append(_("There was a problem with the connection with Uruware: %s", repr(exp)))

        return self._process_response(response, errors)

    def _update_cfe_state(self, result):
        """ Update the CFE State and update the error message field if applies.
        It depends on the Uruware/DGI state, response(CodRta)

        If CFE have been accepted, received or rejected cannot be sent again to UCFE
        because they cannot be changed (they have been already sent to DGI) """
        errors = result.get("errors")
        if errors:
            self.write({
                'state': "error",
                'message': "\n - ".join(errors),
            })
        else:
            response = result.get("response")
            if response is not None:
                ucfe_result_code = response.findtext(".//{*}CodRta")
                self.state = RESPONSE_CODE_TO_STATE.get(ucfe_result_code, "error")
                if self.state in ["error", "rejected"]:
                    result_msg = response.findtext(".//{*}MensajeRta")
                    self.message = _("CODE %(code)s: %(msg)s", code=ucfe_result_code, msg=result_msg)
                elif self.state in ["received", "accepted"]:
                    self.message = False

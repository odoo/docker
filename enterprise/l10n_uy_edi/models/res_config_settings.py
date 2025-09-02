import logging

from odoo import models, fields, _

from odoo.exceptions import UserError, AccessError
from odoo.addons.iap.tools import iap_tools
from odoo.addons.iap import InsufficientCreditError

_logger = logging.getLogger(__name__)

TEST_ENDPOINT = "https://l10n-uy-uruware.test.odoo.com/"
PROD_ENDPOINT = "https://l10n-uy-uruware.api.odoo.com/"


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_uy_edi_ucfe_env = fields.Selection(related="company_id.l10n_uy_edi_ucfe_env", readonly=False)
    l10n_uy_edi_ucfe_password = fields.Char(related="company_id.l10n_uy_edi_ucfe_password", readonly=False)
    l10n_uy_edi_ucfe_commerce_code = fields.Char(related="company_id.l10n_uy_edi_ucfe_commerce_code", readonly=False)
    l10n_uy_edi_ucfe_terminal_code = fields.Char(related="company_id.l10n_uy_edi_ucfe_terminal_code", readonly=False)

    def l10n_uy_edi_action_check_credentials(self):
        """ Make a ECHO test to UCFE to see if the server is running and that the environment
        params have been properly configured """
        error_msg = self.env["l10n_uy_edi.document"]._validate_credentials(self.company_id)
        if error_msg:
            _logger.info("Error Checking Uruware Credentials: %s", error_msg)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "danger" if error_msg else "warning",
                "message": error_msg or _("Everything is ok"),
                "next": {"type": "ir.actions.act_window_close"},
            }
        }

    def l10n_uy_edi_action_create_uruware_account(self):
        self.ensure_one()
        error = False

        if not self.company_id.vat:
            raise UserError(_('Please configure your company RUT first'))
        try:
            res = iap_tools.iap_jsonrpc(
                (TEST_ENDPOINT if self.l10n_uy_edi_ucfe_env == "testing" else PROD_ENDPOINT) + "api/l10n_uy_reg_proxy/1/create_account",
                params={
                    "db_uuid": self.env["ir.config_parameter"].sudo().get_param("database.uuid", "FAKETESTID"),
                    "company": self.company_id.id,
                    "company_name": self.company_id.name,
                    "company_vat": self.company_id.vat,
                })
            if res.get("success") is not True:
                error = _("Error connection to Odoo IAP to create Uruware account")
                error_code = res.get('error')
                if error_code == 'error_invalid_dbuuid':
                    error = _('Make sure you have a valid enterprise contract in this database. '
                              'If it is new, it might take some time for the system to recognize your contract. ')
                elif error_code == 'error_sending_mail':
                    error = _('Your database is valid, but an error happened on our side. ')
                elif error_code:
                    error += ":" + error_code

        except (UserError, InsufficientCreditError, AccessError) as exp:
            error = str(exp)

        if error:
            _logger.info("Error creating Uruware account: %s", error)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "danger" if error else "warning",
                "message":
                    _("Error creating the Uruware account. Please contact support: ") + error if error else
                    _("The account creating request has been successfully sent. "
                      "Please check your email for more instructions"),
                "next": {"type": "ir.actions.act_window_close"},
                "sticky": True,
            }
        }

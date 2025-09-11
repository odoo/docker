import hashlib
import hmac
import json
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import _, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import hmac as hmac_tool

from odoo.addons.sale_amazon import utils as amazon_utils


_logger = logging.getLogger(__name__)


def compute_oauth_signature(account_id):
    """ Compute a signature for the OAuth flow.

    :param int account_id: The account being authorized, as an `amazon.account` id.
    :param odoo.api.Environment env: The current environment.
    :return: The computed signature.
    :rtype: str
    """
    secret = request.env['ir.config_parameter'].sudo().get_param('database.secret')
    message = repr(('amazon_compute_oauth_signature', str(account_id)))
    return hmac_tool(request.env(su=True), secret.encode(), message.encode(), hashlib.sha256)


class AmazonController(http.Controller):

    @http.route(
        '/amazon/return', type='http', methods=['GET'], auth='user', website=True, sitemap=False
    )
    def amazon_return_from_authorization(self, **data):
        """ Request a refresh token from the OAuth token and redirect to the account form.

        :param dict data: The authorization data provided by Amazon upon redirection, including the
                          custom `state` parameter.
        :raise Forbidden: If the received signature does not match the expected signature.
        :raise ValidationError: If the account id does not match any Amazon account.
        """
        _logger.info("Returning from authorization with data:\n%s", pprint.pformat(data))

        # Retrieve the Amazon data and Odoo metadata from the redirect data.
        seller_key = data['selling_partner_id']
        authorization_code = data['spapi_oauth_code']
        state = json.loads(data['state'])
        account_id = state['account_id']
        received_signature = state['signature']

        # Compare the received signature with the expected signature.
        expected_signature = compute_oauth_signature(account_id)
        if not hmac.compare_digest(received_signature, expected_signature):
            _logger.warning("Signature computed from data does not match the expected signature.")
            raise Forbidden()

        # Store the Amazon data on the account.
        account = request.env['amazon.account'].browse(account_id).exists()
        if not account:
            raise ValidationError(_("Could not find Amazon account with id %s", account_id))
        account.seller_key = seller_key

        # Craft the URL of the Amazon account.
        account_url = f'/odoo/action-sale_amazon.list_amazon_account_action/{account_id}'

        # Request and set the refresh token on the account and finalize the set up.
        try:
            amazon_utils.exchange_authorization_code(authorization_code, account)
            account.action_update_available_marketplaces()
        except (UserError, ValidationError) as e:
            return request.render(
                'sale_amazon.authorization_error',
                qcontext={'error_message': str(e), 'account_url': account_url},
            )

        return request.redirect(account_url, local=False)

# -*- coding: utf-8 -*-
from odoo import _, api, models, fields, Command
from odoo.addons.l10n_mx_edi.models.l10n_mx_edi_document import CANCELLATION_REASON_SELECTION, CFDI_DATE_FORMAT, USAGE_SELECTION
from odoo.exceptions import UserError, ValidationError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_mx_edi_is_cfdi_needed = fields.Boolean(
        compute='_compute_l10n_mx_edi_is_cfdi_needed',
        store=True,
    )
    l10n_mx_edi_document_ids = fields.Many2many(
        comodel_name='l10n_mx_edi.document',
        relation='l10n_mx_edi_pos_order_document_ids_rel',
        column1='pos_order_id',
        column2='document_id',
        copy=False,
        readonly=True,
    )
    l10n_mx_edi_cfdi_state = fields.Selection(
        string="CFDI status",
        selection=[
            ('sent', 'Signed'),
            ('global_sent', 'Signed Global'),
            ('global_cancel', 'Cancelled Global'),
        ],
        store=True,
        copy=False,
        compute="_compute_l10n_mx_edi_cfdi_state_and_attachment",
    )
    l10n_mx_edi_cfdi_sat_state = fields.Selection(
        string="SAT status",
        selection=[
            ('valid', "Validated"),
            ('cancelled', "Cancelled"),
            ('not_found', "Not Found"),
            ('not_defined', "Not Defined"),
            ('error', "Error"),
        ],
        store=True,
        copy=False,
        compute="_compute_l10n_mx_edi_cfdi_state_and_attachment",
    )
    l10n_mx_edi_cfdi_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="CFDI",
        store=True,
        copy=False,
        compute='_compute_l10n_mx_edi_cfdi_state_and_attachment',
    )
    # Technical field indicating if the "Update SAT" button needs to be displayed on pos order view.
    l10n_mx_edi_update_sat_needed = fields.Boolean(compute='_compute_l10n_mx_edi_update_sat_needed')
    # Indicate if you send the invoice to the SAT using 'Publico En General' meaning
    # the customer is unknown by the SAT. This is mainly used when the customer doesn't have
    # a VAT number registered to the SAT.
    l10n_mx_edi_cfdi_to_public = fields.Boolean(
        string="CFDI to public",
        compute='_compute_l10n_mx_edi_cfdi_to_public',
        store=True,
        readonly=False,
        help="Send the CFDI with recipient 'publico en general'",
    )
    l10n_mx_edi_usage = fields.Selection(
        selection=USAGE_SELECTION,
        string="Usage",
        default="G03",
        help="The code that corresponds to the use that will be made of the receipt by the recipient.",
    )
    l10n_mx_edi_cfdi_uuid = fields.Char(
        string="Fiscal Folio",
        compute='_compute_l10n_mx_edi_cfdi_uuid',
        copy=False,
        store=True,
        help="Folio in electronic invoice, is returned by SAT when send to stamp.",
    )
    l10n_mx_edi_payment_method_id = fields.Many2one(
        comodel_name='l10n_mx_edi.payment.method',
        string="Payment Way",
        compute='_compute_l10n_mx_edi_payment_method_id',
    )

    def action_pos_order_invoice(self):
        # EXTENDS 'point_of_sale'
        if self.company_id.country_id.code == 'MX':
            if self.refunded_order_id and not self.refunded_order_id.account_move:
                raise UserError(_("You cannot invoice this refund since the related order is not invoiced yet."))
        action_values = super().action_pos_order_invoice()

        for order in self:
            if order.l10n_mx_edi_cfdi_state == 'global_sent':
                order._l10n_mx_edi_cfdi_invoice_try_send()

        return action_values

    def _l10n_mx_edi_check_autogenerate_cfdi_refund(self):
        for order in self:
            if (
                order.company_id.country_id.code == 'MX'
                and not order.l10n_mx_edi_cfdi_state
                and order.refunded_order_id and order.refunded_order_id.l10n_mx_edi_cfdi_state == 'global_sent'
            ):
                order._l10n_mx_edi_cfdi_invoice_try_send()

    @api.model
    def sync_from_ui(self, orders):
        # EXTENDS 'point_of_sale'
        for order in orders:
            if order.get('to_invoice', False) and self.env['pos.session'].browse(order['session_id']).company_id.country_id.code == 'MX':
                order['l10n_mx_edi_cfdi_to_public'] = order.get('l10n_mx_edi_cfdi_to_public', False)
                order['l10n_mx_edi_usage'] = order.get('l10n_mx_edi_usage', False)

        data = super().sync_from_ui(orders)
        if len(orders) > 0:
            orders = self.browse([o['id'] for o in data["pos.order"]])
            orders._l10n_mx_edi_check_autogenerate_cfdi_refund()

        return data

    def _refund(self):
        # EXTENDS 'point_of_sale'
        orders = super()._refund()
        orders._l10n_mx_edi_check_autogenerate_cfdi_refund()
        return orders

    def _prepare_invoice_vals(self):
        # EXTENDS 'point_of_sale'
        vals = super()._prepare_invoice_vals()
        if self.company_id.country_id.code == 'MX':
            vals.update({
                'l10n_mx_edi_cfdi_to_public': self.l10n_mx_edi_cfdi_to_public,
                # If the invoice was created through the QRCode on the ticket we take the usage from the filled form
                'l10n_mx_edi_usage': self.env.context.get('default_l10n_mx_edi_usage') or self.l10n_mx_edi_usage,
                'l10n_mx_edi_payment_method_id': self.l10n_mx_edi_payment_method_id.id,
            })
            account_fiscal_folio = self.refunded_order_id.account_move.l10n_mx_edi_cfdi_uuid
            if account_fiscal_folio:
                vals['l10n_mx_edi_cfdi_origin'] = self.env['account.move']._l10n_mx_edi_write_cfdi_origin('03', [account_fiscal_folio])
        return vals

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_collect_orders_in_chain(self):
        """ Collect all involved orders by resolving all refund links between orders.

        :return: A recordset of orders.
        """
        orders = self
        while True:
            new_orders = orders.refunded_order_id
            new_orders |= self.env['pos.order.line']\
                .search([('refunded_orderline_id.order_id', 'in', (orders + new_orders).ids)])\
                ._l10n_mx_edi_cfdi_lines()\
                .order_id
            new_orders -= orders
            if new_orders:
                orders += new_orders
            else:
                break
        return orders

    def _l10n_mx_edi_check_orders_for_global_invoice(self, origin=None):
        """ Ensure the current records are eligible for the creation of a global invoice.

        :param origin: The origin of the GI when cancelling an existing one.
        """
        orders = self._l10n_mx_edi_collect_orders_in_chain()

        if len(orders.company_id) != 1:
            raise UserError(_("You can only process orders sharing the same company."))
        if len(self.currency_id) != 1:
            raise UserError(_("You can only process orders sharing the same currency."))

        if not origin:
            failed_orders = orders.filtered(lambda x: (
                not x.l10n_mx_edi_is_cfdi_needed
                or x.l10n_mx_edi_cfdi_state in ('sent', 'global_sent')
                or x.account_move
            ))
            if failed_orders:
                orders_str = ", ".join(failed_orders.mapped('name'))
                raise UserError(_("Orders %s are already sent or not eligible for CFDI.", orders_str))
        return orders

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('company_id')
    def _compute_l10n_mx_edi_is_cfdi_needed(self):
        """ Check whatever or not the CFDI is needed on this invoice.
        """
        for order in self:
            order.l10n_mx_edi_is_cfdi_needed = \
                order.country_code == 'MX' \
                and order.company_id.currency_id.name == 'MXN'

    @api.depends('l10n_mx_edi_document_ids.state', 'l10n_mx_edi_document_ids.sat_state')
    def _compute_l10n_mx_edi_cfdi_state_and_attachment(self):
        for order in self:
            order.l10n_mx_edi_cfdi_sat_state = order.l10n_mx_edi_cfdi_sat_state
            order.l10n_mx_edi_cfdi_state = None
            order.l10n_mx_edi_cfdi_attachment_id = None
            for doc in order.l10n_mx_edi_document_ids.sorted():
                if doc.state == 'invoice_sent' and order.refunded_order_id:
                    if doc.sat_state != 'skip':
                        order.l10n_mx_edi_cfdi_sat_state = doc.sat_state
                    order.l10n_mx_edi_cfdi_state = 'sent'
                    order.l10n_mx_edi_cfdi_attachment_id = doc.attachment_id
                    break
                elif doc.state == 'ginvoice_sent':
                    if doc.sat_state != 'skip':
                        order.l10n_mx_edi_cfdi_sat_state = doc.sat_state
                    order.l10n_mx_edi_cfdi_state = 'global_sent'
                    order.l10n_mx_edi_cfdi_attachment_id = doc.attachment_id
                    break
                elif doc.state == 'ginvoice_cancel' and doc.cancellation_reason != '01':
                    order.l10n_mx_edi_cfdi_sat_state = doc.sat_state
                    order.l10n_mx_edi_cfdi_state = 'global_cancel'
                    order.l10n_mx_edi_cfdi_attachment_id = doc.attachment_id
                    break

    @api.depends('l10n_mx_edi_is_cfdi_needed', 'partner_id', 'company_id')
    def _compute_l10n_mx_edi_cfdi_to_public(self):
        for order in self:
            if order.l10n_mx_edi_is_cfdi_needed and order.partner_id and order.company_id:
                cfdi_values = self.env['l10n_mx_edi.document']._get_company_cfdi_values(order.company_id)
                self.env['l10n_mx_edi.document']._add_customer_cfdi_values(
                    cfdi_values,
                    customer=order.partner_id,
                )
                order.l10n_mx_edi_cfdi_to_public = cfdi_values['receptor']['rfc'] == 'XAXX010101000'
            else:
                order.l10n_mx_edi_cfdi_to_public = order.l10n_mx_edi_is_cfdi_needed

    @api.depends('l10n_mx_edi_document_ids.state')
    def _compute_l10n_mx_edi_update_sat_needed(self):
        for order in self:
            order.l10n_mx_edi_update_sat_needed = bool(order.l10n_mx_edi_document_ids.filtered_domain(
                self.env['l10n_mx_edi.document']._get_update_sat_status_domain(from_cron=False)
            ))

    @api.depends('l10n_mx_edi_cfdi_attachment_id')
    def _compute_l10n_mx_edi_cfdi_uuid(self):
        for order in self:
            if order.l10n_mx_edi_cfdi_attachment_id:
                cfdi_infos = self.env['l10n_mx_edi.document']._decode_cfdi_attachment(order.l10n_mx_edi_cfdi_attachment_id.raw)
                order.l10n_mx_edi_cfdi_uuid = cfdi_infos.get('uuid')
            else:
                order.l10n_mx_edi_cfdi_uuid = None

    @api.depends('payment_ids', 'refunded_order_id')
    def _compute_l10n_mx_edi_payment_method_id(self):
        for order in self:
            order.l10n_mx_edi_payment_method_id = order.payment_ids\
                .sorted(lambda p: -p.amount).payment_method_id.l10n_mx_edi_payment_method_id[:1]
            if not order.l10n_mx_edi_payment_method_id and order.refunded_order_id:
                order.l10n_mx_edi_payment_method_id = order.refunded_order_id.l10n_mx_edi_payment_method_id[:1]

    # -------------------------------------------------------------------------
    # CONSTRAINTS METHODS
    # -------------------------------------------------------------------------

    @api.constrains('amount_total')
    def _l10n_mx_edi_constrains_amount_total(self):
        for order in self:
            order_lines = order.lines._l10n_mx_edi_cfdi_lines()
            if (
                order_lines
                and order.l10n_mx_edi_is_cfdi_needed
                and (
                    (
                        order.refunded_order_id
                        and any(line.price_subtotal > 0.0 for line in order_lines)
                    )
                    or (not order.refunded_order_id and order.amount_total < 0.0)
                )
            ):
                raise ValidationError(_("The amount of the order must be positive for a sale and negative for a refund."))

    # -------------------------------------------------------------------------
    # CFDI Generation
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_cfdi_check_order_config(self):
        """ Prepare the CFDI xml for the current pos order. """
        self.ensure_one()
        errors = []

        # == Check the 'l10n_mx_edi_decimal_places' field set on the currency  ==
        currency_precision = self.currency_id.l10n_mx_edi_decimal_places
        if currency_precision is False:
            errors.append(_(
                "The SAT does not provide information for the currency %s.\n"
                "You must get manually a key from the PAC to confirm the "
                "currency rate is accurate enough.",
                self.currency_id,
            ))

        # == Check the order ==
        base_lines = self.lines._l10n_mx_edi_cfdi_lines()._prepare_tax_base_line_values()
        negative_lines = [
            x
            for x in base_lines
            if (x['record'].price_subtotal > 0.0 and x['is_refund']) or (x['record'].price_subtotal < 0.0 and not x['is_refund'])
        ]
        if negative_lines:
            # Discount line without taxes is not allowed.
            if [x for x in negative_lines if not x['tax_ids']]:
                errors.append(_(
                    "Order lines having a negative amount without a tax set is not allowed to "
                    "generate the CFDI.",
                ))
        return errors

    # -------------------------------------------------------------------------
    # CFDI: DOCUMENTS
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_cfdi_invoice_document_sent_failed(self, error, cfdi_filename=None, cfdi_str=None):
        """ Create/update the invoice document for 'sent_failed'.
        The parameters are provided by '_l10n_mx_edi_prepare_invoice_cfdi'.

        :param error:           The error.
        :param cfdi_filename:   The optional filename of the cfdi.
        :param cfdi_str:        The optional content of the cfdi.
        :return:                The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'pos_order_ids': [Command.set(self.ids)],
            'state': 'invoice_sent_failed',
            'sat_state': None,
            'message': error,
        }
        if cfdi_filename and cfdi_str:
            document_values['attachment_id'] = {
                'name': cfdi_filename,
                'raw': cfdi_str,
            }
        return self.env['l10n_mx_edi.document']._create_update_invoice_document_from_pos_order(self, document_values)

    def _l10n_mx_edi_cfdi_invoice_document_sent(self, cfdi_filename, cfdi_str):
        """ Create/update the invoice document for 'sent'.
        The parameters are provided by '_l10n_mx_edi_prepare_invoice_cfdi'.

        :param cfdi_filename:   The filename of the cfdi.
        :param cfdi_str:        The content of the cfdi.
        :return:                The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'pos_order_ids': [Command.set(self.ids)],
            'state': 'invoice_sent',
            'sat_state': 'not_defined',
            'message': None,
            'attachment_id': {
                'name': cfdi_filename,
                'raw': cfdi_str,
                'description': "CFDI",
            },
        }
        return self.env['l10n_mx_edi.document']._create_update_invoice_document_from_pos_order(self, document_values)

    def _l10n_mx_edi_cfdi_invoice_document_empty(self):
        """ Create/update the invoice document for 'sent'.
        The parameters are provided by '_l10n_mx_edi_prepare_invoice_cfdi'.

        :return: The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'pos_order_ids': [Command.set(self.ids)],
            'state': 'invoice_sent',
            'sat_state': 'skip',
            'message': None,
        }
        return self.env['l10n_mx_edi.document']._create_update_invoice_document_from_pos_order(self, document_values)

    def _l10n_mx_edi_cfdi_invoice_document_cancel_failed(self, error, cfdi, cancel_reason):
        """ Create/update the invoice document for 'cancel_failed'.

        :param error:           The error.
        :param cfdi:            The source cfdi attachment to cancel.
        :param cancel_reason:   The reason for this cancel.
        :return:                The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'pos_order_ids': [Command.set(self.ids)],
            'state': 'invoice_cancel_failed',
            'sat_state': None,
            'message': error,
            'attachment_id': cfdi.attachment_id.id,
            'cancellation_reason': cancel_reason,
        }
        return self.env['l10n_mx_edi.document']._create_update_invoice_document_from_pos_order(self, document_values)

    def _l10n_mx_edi_cfdi_invoice_document_cancel(self, cfdi, cancel_reason):
        """ Create/update the invoice document for 'cancel'.

        :param cfdi:            The source cfdi attachment to cancel.
        :param cancel_reason:   The reason for this cancel.
        :return:                The created/updated document.
        """
        self.ensure_one()

        document_values = {
            'pos_order_ids': [Command.set(self.ids)],
            'state': 'invoice_cancel',
            'sat_state': 'not_defined',
            'message': None,
            'attachment_id': cfdi.attachment_id.id,
            'cancellation_reason': cancel_reason,
        }
        return self.env['l10n_mx_edi.document']._create_update_invoice_document_from_pos_order(self, document_values)

    def _l10n_mx_edi_cfdi_global_invoice_document_sent_failed(self, error, cfdi_filename=None, cfdi_str=None):
        """ Create/update the global invoice document for 'sent_failed'.

        :param error:           The error.
        :param cfdi_filename:   The optional filename of the cfdi.
        :param cfdi_str:        The optional content of the cfdi.
        :return:                The created/updated document.
        """
        document_values = {
            'pos_order_ids': [Command.set(self.ids)],
            'state': 'ginvoice_sent_failed',
            'sat_state': None,
            'message': error,
        }
        if cfdi_filename and cfdi_str:
            document_values['attachment_id'] = {
                'name': cfdi_filename,
                'raw': cfdi_str,
            }
        return self.env['l10n_mx_edi.document']._create_update_global_invoice_document_from_pos_orders(self, document_values)

    def _l10n_mx_edi_cfdi_global_invoice_document_sent(self, cfdi_filename, cfdi_str):
        """ Create/update the global invoice document for 'sent'.

        :param cfdi_filename:   The filename of the cfdi.
        :param cfdi_str:        The content of the cfdi.
        :return:                The created/updated document.
        """
        document_values = {
            'pos_order_ids': [Command.set(self.ids)],
            'state': 'ginvoice_sent',
            'sat_state': 'not_defined',
            'message': None,
            'attachment_id': {
                'name': cfdi_filename,
                'raw': cfdi_str,
                'description': "CFDI",
            },
        }
        return self.env['l10n_mx_edi.document']._create_update_global_invoice_document_from_pos_orders(self, document_values)

    def _l10n_mx_edi_cfdi_global_invoice_document_empty(self):
        """ Create/update the global invoice document for 'sent'.

        :return:                The created/updated document.
        """
        document_values = {
            'pos_order_ids': [Command.set(self.ids)],
            'state': 'ginvoice_sent',
            'sat_state': 'skip',
            'message': None,
        }
        return self.env['l10n_mx_edi.document']._create_update_global_invoice_document_from_pos_orders(self, document_values)

    def _l10n_mx_edi_cfdi_global_invoice_document_cancel_failed(self, error, cfdi, cancel_reason):
        """ Create/update the invoice document for 'cancel_failed'.

        :param error:           The error.
        :param cfdi:            The source cfdi attachment to cancel.
        :param cancel_reason:   The reason for this cancel.
        :return:                The created/updated document.
        """
        document_values = {
            'pos_order_ids': [Command.set(self.ids)],
            'state': 'ginvoice_cancel_failed',
            'sat_state': None,
            'message': error,
            'attachment_id': cfdi.attachment_id.id,
            'cancellation_reason': cancel_reason,
        }
        return self.env['l10n_mx_edi.document']._create_update_global_invoice_document_from_pos_orders(self, document_values)

    def _l10n_mx_edi_cfdi_global_invoice_document_cancel(self, cfdi, cancel_reason):
        """ Create/update the invoice document for 'cancel'.

        :param cfdi:            The source cfdi attachment to cancel.
        :param cancel_reason:   The reason for this cancel.
        :return:                The created/updated document.
        """
        self.l10n_mx_edi_cfdi_attachment_id.ensure_one()

        document_values = {
            'pos_order_ids': [Command.set(self.ids)],
            'state': 'ginvoice_cancel',
            'sat_state': 'not_defined',
            'message': None,
            'attachment_id': cfdi.attachment_id.id,
            'cancellation_reason': cancel_reason,
        }
        return self.env['l10n_mx_edi.document']._create_update_global_invoice_document_from_pos_orders(self, document_values)

    # -------------------------------------------------------------------------
    # CFDI: FLOWS
    # -------------------------------------------------------------------------

    def _l10n_mx_edi_cfdi_invoice_try_send(self):
        """ Try to generate and send the CFDI for the current pos order refund. """
        self.ensure_one()

        # == Check the config ==
        errors = self._l10n_mx_edi_cfdi_check_order_config()
        if errors:
            self._l10n_mx_edi_cfdi_invoice_document_sent_failed("\n".join(errors))
            return

        # == Lock ==
        self.env['res.company']._with_locked_records(self)

        # == Send ==
        def on_populate(cfdi_values):
            self.ensure_one()
            Document = self.env['l10n_mx_edi.document']
            order_lines = self.lines._l10n_mx_edi_cfdi_lines()
            base_lines = order_lines._prepare_tax_base_line_values()
            Document._add_base_lines_tax_amounts(base_lines, cfdi_values['company'])
            lines_dispatching = Document._dispatch_cfdi_base_lines(base_lines)
            if lines_dispatching['orphan_negative_lines']:
                cfdi_values['errors'] = [_("Failed to distribute some negative lines")]
                return

            cfdi_lines = lines_dispatching['result_lines']
            if not cfdi_lines:
                cfdi_values['errors'] = ['empty_cfdi']
                return

            self.env['account.tax']._round_base_lines_tax_details(cfdi_lines, self.company_id)

            cfdi_values['tipo_de_comprobante'] = 'E'
            if self.amount_total < 0:
                # The order is a refund.
                Document._add_document_origin_cfdi_values(cfdi_values, f"01|{self.refunded_order_id.l10n_mx_edi_cfdi_uuid}")
            else:
                # Refund of the pos order itself.
                Document._add_document_origin_cfdi_values(cfdi_values, f'01|{self.l10n_mx_edi_cfdi_uuid}')

            Document._add_base_cfdi_values(cfdi_values)
            Document._add_currency_cfdi_values(cfdi_values, self.currency_id)
            Document._add_document_name_cfdi_values(cfdi_values, self.name)
            Document._add_customer_cfdi_values(
                cfdi_values,
                self.partner_id,
                usage=self.l10n_mx_edi_usage,
                to_public=self.l10n_mx_edi_cfdi_to_public,
            )
            Document._add_tax_objected_cfdi_values(cfdi_values, cfdi_lines)
            Document._add_base_lines_cfdi_values(cfdi_values, cfdi_lines)
            Document._add_payment_policy_cfdi_values(cfdi_values, payment_method=self.l10n_mx_edi_payment_method_id)
            cfdi_values['condiciones_de_pago'] = None

            # Dates.
            timezoned_now = Document._get_datetime_now_with_mx_timezone(cfdi_values)
            cfdi_values['fecha'] = timezoned_now.strftime(CFDI_DATE_FORMAT)

            # Currency.
            if self.currency_id.name == 'MXN':
                cfdi_values['tipo_cambio'] = None
            else:
                company_currency = self.company_id.currency_id
                rate = self.currency_id._get_conversion_rate(self.currency_id, company_currency, self.company_id, self.date_order)
                cfdi_values['tipo_cambio'] = rate

        def on_failure(error, cfdi_filename=None, cfdi_str=None):
            if error == 'empty_cfdi':
                self._l10n_mx_edi_cfdi_invoice_document_empty()
            else:
                self._l10n_mx_edi_cfdi_invoice_document_sent_failed(error, cfdi_filename=cfdi_filename, cfdi_str=cfdi_str)

        def on_success(_cfdi_values, cfdi_filename, cfdi_str, populate_return=None):
            self._l10n_mx_edi_cfdi_invoice_document_sent(cfdi_filename, cfdi_str)

        qweb_template = self.env['l10n_mx_edi.document']._get_invoice_cfdi_template()
        cfdi_filename = "MX-Refund-4.0.xml".replace('/', '')
        self.env['l10n_mx_edi.document']._send_api(
            self.company_id,
            qweb_template,
            cfdi_filename,
            on_populate,
            on_failure,
            on_success,
        )

    def _l10n_mx_edi_cfdi_invoice_try_cancel(self, document, cancel_reason):
        """ Try to cancel the CFDI for the current refund.

        :param document:        The source invoice document to cancel.
        :param cancel_reason:   The reason for the cancellation.
        """
        self.ensure_one()

        # == Lock ==
        self.env['res.company']._with_locked_records(self)

        # == Cancel ==
        def on_failure(error):
            self._l10n_mx_edi_cfdi_invoice_document_cancel_failed(error, document, cancel_reason)

        def on_success():
            self._l10n_mx_edi_cfdi_invoice_document_cancel(document, cancel_reason)

        document._cancel_api(self.company_id, cancel_reason, on_failure, on_success)

    def _l10n_mx_edi_cfdi_refund_update_sat_state(self, document, sat_state, error=None):
        """ Update the SAT state of the document for the current pos order refund.

        :param document:    The CFDI document to be updated.
        :param sat_state:   The newly fetched state from the SAT
        :param error:       In case of error, the message returned by the SAT.
        """
        self.ensure_one()

        # The user manually cancelled the document in the SAT portal.
        if document.state == 'invoice_sent' and sat_state == 'cancelled':
            if document.sat_state not in ('valid', 'cancelled', 'skip'):
                document.sat_state = 'skip'

            document = self._l10n_mx_edi_cfdi_invoice_document_cancel(
                document,
                CANCELLATION_REASON_SELECTION[1][0],  # Force '02'.
            )

        document.sat_state = sat_state
        document.message = None
        if sat_state == 'error' and error:
            document.message = error

    def l10n_mx_edi_cfdi_try_sat(self):
        self.ensure_one()
        documents = self.l10n_mx_edi_document_ids
        for document in documents.filtered_domain(documents._get_update_sat_status_domain(from_cron=False)):
            document._update_sat_state()

    def _l10n_mx_edi_cfdi_global_invoice_try_send(self, periodicity='04', origin=None):
        """ Create a CFDI global invoice.

        :param periodicity: The value to fill the 'Periodicidad' value.
        :param origin:      The origin of the GI when cancelling an existing one.
        """
        Document = self.env['l10n_mx_edi.document']
        orders = self._l10n_mx_edi_check_orders_for_global_invoice(origin=origin)

        # == Check the config ==
        orders = self.filtered(lambda order: not order.refunded_order_id)
        orders |= self.env['pos.order.line'].search([('refunded_orderline_id.order_id', 'in', orders.ids)]).order_id
        errors = []
        for order in orders:
            errors += order._l10n_mx_edi_cfdi_check_order_config()
        if errors:
            orders._l10n_mx_edi_cfdi_global_invoice_document_sent_failed("\n".join(set(errors)))
            return

        # == Lock ==
        self.env['res.company']._with_locked_records(orders)

        # == Send ==
        def on_populate(cfdi_values):
            cfdi_lines = []
            for order in orders:
                # The refund are managed by the refunded order.
                if order.refunded_order_id:
                    continue

                # Dispatch the negative lines on the order itself.
                order_lines = order.lines._l10n_mx_edi_cfdi_lines()
                base_lines = order_lines._prepare_tax_base_line_values()
                Document._add_base_lines_tax_amounts(base_lines, cfdi_values['company'])
                lines_dispatching = Document._dispatch_cfdi_base_lines(base_lines)
                if lines_dispatching['orphan_negative_lines']:
                    cfdi_values['errors'] = [_("Failed to distribute some negative lines")]
                    return

                base_lines = lines_dispatching['result_lines']
                base_line_ids = {x['id'] for x in base_lines}
                for base_line in base_lines:
                    base_line['document_name'] = order.name

                # Find the refund lines targeting this order.
                all_refund_order_lines = self.env['pos.order.line']\
                    .search([('refunded_orderline_id', 'in', order_lines.ids)])\
                    ._l10n_mx_edi_cfdi_lines()

                # Manage the refunds.
                all_refund_base_lines = []
                for refund_order_lines in all_refund_order_lines.grouped('order_id').values():

                    # Dispatch the positive lines on the refund itself.
                    refund_base_lines = refund_order_lines._prepare_tax_base_line_values()
                    for refund_base_line in refund_base_lines:
                        refund_base_line['quantity'] *= -1
                    Document._add_base_lines_tax_amounts(refund_base_lines, cfdi_values['company'])
                    lines_dispatching = Document._dispatch_cfdi_base_lines(refund_base_lines)
                    if lines_dispatching['result_lines']:
                        cfdi_values['errors'] = [_("Failed to distribute some negative lines")]
                        return

                    # Dispatch the remaining negative lines from the refund on the invoice.
                    refund_base_lines = lines_dispatching['orphan_negative_lines']
                    lines_dispatching = Document._dispatch_cfdi_base_lines(base_lines + refund_base_lines)
                    if lines_dispatching['orphan_negative_lines']:
                        cfdi_values['errors'] = [_("Failed to distribute some negative lines")]
                        return

                    all_refund_base_lines += [x for x in lines_dispatching['result_lines'] if x['id'] not in base_line_ids]
                cfdi_lines += base_lines + all_refund_base_lines

            # Nothing left. Everything is refunded or empty.
            cfdi_lines = [x for x in cfdi_lines if not x['currency_id'].is_zero(x['tax_details']['raw_total_excluded_currency'])]
            if not cfdi_lines:
                cfdi_values['errors'] = ['empty_cfdi']
                return

            self.env['account.tax']._round_base_lines_tax_details(cfdi_lines, cfdi_values['company'])
            _biggest_amount_total, biggest_used_payment_method = max(
                [
                    (order.amount_total, order.l10n_mx_edi_payment_method_id)
                    for order in orders
                ],
                key=lambda x: x[0],
            )
            Document._add_payment_policy_cfdi_values(cfdi_values, payment_method=biggest_used_payment_method)
            Document._add_global_invoice_cfdi_values(
                cfdi_values,
                cfdi_lines,
                periodicity=periodicity,
                origin=origin,
            )

            self.env['res.company']._with_locked_records(cfdi_values['sequence'])
            return cfdi_values['sequence']

        def on_failure(error, cfdi_filename=None, cfdi_str=None):
            if error == 'empty_cfdi':
                orders._l10n_mx_edi_cfdi_global_invoice_document_empty()
            else:
                orders._l10n_mx_edi_cfdi_global_invoice_document_sent_failed(error, cfdi_filename=cfdi_filename, cfdi_str=cfdi_str)

        def on_success(cfdi_values, cfdi_filename, cfdi_str, populate_return=None):
            self.env['l10n_mx_edi.document']._consume_global_invoice_cfdi_sequence(populate_return, int(cfdi_values['folio']))
            orders._l10n_mx_edi_cfdi_global_invoice_document_sent(cfdi_filename, cfdi_str)

        qweb_template = self.env['l10n_mx_edi.document']._get_invoice_cfdi_template()
        cfdi_filename = "MX-Global-Invoice-4.0.xml".replace('/', '')
        self.env['l10n_mx_edi.document']._send_api(
            self.company_id,
            qweb_template,
            cfdi_filename,
            on_populate,
            on_failure,
            on_success,
        )

    def _l10n_mx_edi_cfdi_global_invoice_try_cancel(self, document, cancel_reason):
        """ Create a CFDI global invoice for multiple pos orders.

        :param document:        The Global invoice document to cancel.
        :param cancel_reason:   The reason for the cancellation.
        """
        # == Lock ==
        self.env['res.company']._with_locked_records(self)

        # == Cancel ==
        def on_failure(error):
            self._l10n_mx_edi_cfdi_global_invoice_document_cancel_failed(error, document, cancel_reason)

        def on_success():
            self._l10n_mx_edi_cfdi_global_invoice_document_cancel(document, cancel_reason)

        document._cancel_api(self.company_id, cancel_reason, on_failure, on_success)

    def _l10n_mx_edi_cfdi_global_invoice_update_document_sat_state(self, document, sat_state, error=None):
        """ Update the SAT state of the document for the current global invoice.

        :param document:    The CFDI document to be updated.
        :param sat_state:   The newly fetched state from the SAT
        :param error:       In case of error, the message returned by the SAT.
        """
        # The user manually cancelled the document in the SAT portal.
        if document.state == 'ginvoice_sent' and sat_state == 'cancelled':
            if document.sat_state not in ('valid', 'cancelled', 'skip'):
                document.sat_state = 'skip'

            document = self._l10n_mx_edi_cfdi_global_invoice_document_cancel(
                document,
                CANCELLATION_REASON_SELECTION[1][0],  # Force '02'.
            )

        document.sat_state = sat_state
        document.message = None
        if sat_state == 'error' and error:
            document.message = error

    def l10n_mx_edi_action_create_global_invoice(self):
        """ Action to open the wizard allowing to create a global invoice CFDI document for the
        selected pos orders.

        :return: An action to open the wizard.
        """
        return {
            'name': _("Create Global Invoice"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'l10n_mx_edi.global_invoice.create',
            'target': 'new',
            'context': {'default_pos_order_ids': [Command.set(self.ids)]},
        }

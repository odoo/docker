# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import datetime, timedelta

from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, ValidationError, UserError
from odoo.tools import SQL, format_date


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    sdd_required_collection_date = fields.Date(
        string='Required collection date',
        compute='_compute_sdd_required_collection_date', store=True,
        help="Date when the company expects to receive the payments of this batch. "
             "It can't be inferior to the sending day + the longest pre-notification period defined "
             "in the mandates linked to this batch.",
    )
    sdd_batch_booking = fields.Boolean(string="SDD Batch Booking", default=True, help="Request batch booking from the bank for the related bank statements.")
    sdd_scheme = fields.Selection(string="SDD Scheme", selection=[('CORE', 'CORE'), ('B2B', 'B2B')],
    help='The B2B scheme is an optional scheme,\noffered exclusively to business payers.\nSome banks/businesses might not accept B2B SDD.',
    compute='_compute_sdd_scheme', store=True, readonly=False)

    @api.depends('payment_ids')
    def _compute_sdd_required_collection_date(self):
        """
        The regulation requires that the payer's bank must receive the request for a first direct debit collection
        the latest 5 business days prior to the due date. For subsequent direct debit collections,
        the payer's bank must receive such a request the latest 2 business days prior to the due date
        """
        sepa_codes = set(self.env['account.payment.method']._get_sdd_payment_method_code())
        for batch in self.filtered(lambda batch: batch.payment_method_code in sepa_codes):
            if batch.sdd_required_collection_date:  # Do not override when there is a time
                batch.sdd_required_collection_date = batch.sdd_required_collection_date
                continue

            minimum_offset = 5
            mandates = self.payment_ids.sdd_mandate_id

            all_mandates_used = dict(self.env['account.payment']._read_group([
                ('sdd_mandate_id', 'in', mandates.ids),
                ('is_matched', '=', True),
                ],
                groupby=['sdd_mandate_id'],
                aggregates=['__count'],
            ))
            if all(all_mandates_used.get(mandate, 0) > 0 for mandate in mandates):
                # The minimum delay is 5 days in all cases, except when all the mandates involved were already used once before,
                # then it can be 2 days
                minimum_offset = 2

            offset = max((minimum_offset, *mandates.mapped('pre_notification_period')))
            batch.sdd_required_collection_date = fields.Date.context_today(batch) + timedelta(days=offset)

    @api.depends('payment_method_id')
    def _compute_sdd_scheme(self):
        sdd_payment_codes = self.payment_method_id._get_sdd_payment_method_code()
        for batch in self:
            if batch.payment_method_id.code not in sdd_payment_codes:
                batch.sdd_scheme = False
            else:
                if batch.sdd_scheme:
                    batch.sdd_scheme = batch.sdd_scheme
                else:
                    batch.sdd_scheme = batch.payment_ids and batch.payment_ids[0].sdd_mandate_scheme or 'CORE'

    def _get_methods_generating_files(self):
        rslt = super()._get_methods_generating_files()
        rslt += self.payment_method_id._get_sdd_payment_method_code()
        return rslt

    @api.constrains('sdd_required_collection_date', 'payment_method_id')
    def _check_minimal_collection_date(self):
        sepa_codes = self.env['account.payment.method']._get_sdd_payment_method_code()

        sepa_batch_payment = self.filtered(lambda p: p.payment_method_code in sepa_codes)
        if not sepa_batch_payment:
            return

        related_mandates = sepa_batch_payment.payment_ids.sdd_mandate_id
        self.env['account.payment'].flush_model(['is_matched', 'batch_payment_id'])
        self.env['sdd.mandate'].flush_model()

        if related_mandates:
            # Need to use SQL due to ORM limitations
            # We are trying to fetch all account_batch_payment that contain at least one payment using a mandate that was never used before
            self.env.cr.execute(SQL("""
                      WITH mandate_used AS (
                          SELECT DISTINCT mandate.id
                            FROM sdd_mandate mandate
                            JOIN account_payment payment ON payment.sdd_mandate_id = mandate.id
                           WHERE payment.is_matched AND mandate.id IN %(mandate_ids)s
                         )
                    SELECT DISTINCT payment.batch_payment_id
                      FROM account_payment payment
                      JOIN sdd_mandate mandate ON payment.sdd_mandate_id = mandate.id
                 LEFT JOIN mandate_used ON mandate.id = mandate_used.id
                     WHERE mandate_used.id IS NULL
                """,
                mandate_ids=tuple(related_mandates.ids),
            ))
            batch_with_new_mandate_ids = {row[0] for row in self.env.cr.fetchall()}
        else:
            batch_with_new_mandate_ids = set()

        for batch in sepa_batch_payment:
            minimum_offset = 5 if batch.id in batch_with_new_mandate_ids else 2
            minimum_date = fields.Date.context_today(batch) + timedelta(days=minimum_offset)
            if batch.payment_method_code in sepa_codes and batch.sdd_required_collection_date < minimum_date:
                raise ValidationError(_(
                    "The bank needs to be informed at least 5 days in advance for collections related to a new mandate "
                    "and 2 days in advance when the mandate is already known by them. "
                    "In this case, the minimum collection date must be the %(date)s",
                    date=format_date(self.env, minimum_date),
                ))

    @api.constrains('batch_type', 'journal_id', 'payment_ids', 'payment_method_id')
    def _check_payments_constrains(self):
        super(AccountBatchPayment, self)._check_payments_constrains()
        for record in self.filtered(lambda r: r.payment_method_code in r.payment_method_id._get_sdd_payment_method_code()):
            all_sdd_schemes = set(record.payment_ids.mapped('sdd_mandate_id.sdd_scheme'))
            if len(all_sdd_schemes) > 1:
                raise ValidationError(_("All the payments in the batch must have the same SDD scheme."))

    def validate_batch(self):
        self.ensure_one()
        if self.payment_method_code in self.payment_method_id._get_sdd_payment_method_code():
            today = fields.Date.context_today(self)
            company = self.journal_id.company_id

            if not company.sdd_creditor_identifier:
                action = self.env.ref('account.action_account_config')
                raise RedirectWarning(_(
                    "Your company must have a creditor identifier in order to issue SEPA Direct Debit payments requests. "
                    "It can be defined in accounting module's settings."
                    ),
                    action=action.id,
                    button_text=_("Go to settings"),
                )

            payments_without_mandate = self.payment_ids.filtered(lambda x: not x.sdd_mandate_id)
            if payments_without_mandate:
                raise RedirectWarning(
                    _("Some payments are not linked to any mandate."),
                    action={
                        'name': _("Payments without mandate"),
                        'type': 'ir.actions.act_window',
                        'res_model': 'account.payment',
                        'views': [(self.env.ref('account.view_account_payment_tree').id, 'list')],
                        'domain': [('id', 'in', payments_without_mandate.ids)]
                    },
                    button_text=_("Go to payments"),
                )

            invalid_mandates = self.payment_ids.sdd_mandate_id._update_and_partition_state_by_validity()['invalid']
            if invalid_mandates:
                raise RedirectWarning(
                    _("Some payments are linked to an inactive mandate."),
                    action={
                        'name': _("Problematic mandates"),
                        'type': 'ir.actions.act_window',
                        'res_model': 'sdd.mandate',
                        'views': [(self.env.ref('account_sepa_direct_debit.account_sepa_direct_debit_mandate_tree').id, 'list')],
                        'domain': [('id', 'in', invalid_mandates.ids)],
                    },
                    button_text=_("Go to mandates"),
                )

            # Check that the pre-notification delay is good
            collection_date = self.sdd_required_collection_date
            pre_notification_period = max(self.payment_ids.sdd_mandate_id.mapped('pre_notification_period'))  # Empty batch already checked
            min_collection_date = today + timedelta(days=pre_notification_period)
            if collection_date < min_collection_date:
                raise UserError(_(
                    "You cannot generate a SEPA Direct Debit file with a required collection date inferior to the sending day"
                    " + the longest pre-notification period defined in the mandates linked to this batch.\n"
                    "According to these payments mandates, the minimum required date should be the %(minimum_date)s",
                    minimum_date=format_date(self.env, min_collection_date),
                ))

            if self.journal_id.bank_account_id.acc_type != 'iban':
                raise RedirectWarning(_(
                        "Only IBAN account numbers can receive SEPA Direct Debit payments. "
                        "Please select a journal associated to one or add an IBAN bank account to the current journal"
                    ),
                    action={
                        'name': self.journal_id.name,
                        'type': 'ir.actions.act_window',
                        'res_model': 'account.journal',
                        'res_id': self.journal_id.id,
                        'views': [(self.env.ref('account.view_account_journal_form').id, 'form')],
                    },
                    button_text=_("Go to journal"),
                )

        return super().validate_batch()

    def _check_and_post_draft_payments(self, draft_payments):
        rslt = []
        if self.payment_method_code in self.payment_method_id._get_sdd_payment_method_code():

            drafts_without_mandate = draft_payments.filtered(lambda x: not x.get_usable_mandate())
            if drafts_without_mandate:
                rslt = [{'title': _("Some draft payments could not be posted because of the lack of any active mandate."),
                         'records': drafts_without_mandate,
                         'help': _("To solve that, you should create a mandate for each of the involved customers, valid at the moment of the payment date.")
                }]
                draft_payments -= drafts_without_mandate

        return rslt + super()._check_and_post_draft_payments(draft_payments)

    def _generate_export_file(self):
        if self.payment_method_code in self.payment_method_id._get_sdd_payment_method_code():
            # Constrains on models ensure all the payments can generate SDD data before
            # calling this method, so we make no further check of their content here
            company = self.env.company
            return {
                'filename': 'PAIN008' + datetime.now().strftime('%Y%m%d%H%M%S') + '.xml',
                'file': base64.encodebytes(self.payment_ids.generate_xml(company, self.sdd_required_collection_date, self.sdd_batch_booking)),
            }

        return super()._generate_export_file()

    def _send_after_validation(self):
        """ Notify the customer that a debit has been made from his account.

        This is required as per the SEPA Direct Debit rulebook.
        The notice must include:
            - the last 4 digits of the debtor's bank account
            - the mandate reference
            - the amount to be debited
            - your SEPA creditor identifier
            - your contact information
        Notifications should be sent at least 14 calendar days before the payment is created unless
        specified otherwise (We changed that default in Odoo by always specifying the period and defaulting it to 2).

        :param recordset token: The token linked to the mandate from which the debit has been made,
                                as a `payment.token` record
        :return: None
        """
        res = super()._send_after_validation()
        template = self.env.ref('account_sepa_direct_debit.email_template_sdd_pre_notification')
        sdd_codes = set(self.env['account.payment.method']._get_sdd_payment_method_code())
        for payment in self.payment_ids.filtered(lambda payment: payment.payment_method_code in sdd_codes and payment.sdd_mandate_id):
            mandate = payment.sdd_mandate_id
            ctx = {
                'iban_last_4': mandate.partner_bank_id.sanitized_acc_number[-4:],
                'mandate_ref': mandate.name,
                'collection_date': payment.batch_payment_id.sdd_required_collection_date,
                'amount': payment.amount,
                'creditor_iban': payment.journal_id.bank_acc_number,
            }
            payment.with_context(ctx).message_post_with_source(source_ref=template, subtype_xmlid='mail.mt_note')
        return res

    def check_payments_for_errors(self):
        rslt = super().check_payments_for_errors()

        if self.payment_method_code not in self.payment_method_id._get_sdd_payment_method_code():
            return rslt

        if len(self.payment_ids):
            sdd_scheme = self.payment_ids[0].sdd_mandate_id.sdd_scheme
            dif_scheme_payements = self.payment_ids.filtered(lambda x: x.sdd_mandate_id.sdd_scheme != sdd_scheme)
            if dif_scheme_payements:
                rslt.append({
                    'title': _("All the payments in the batch must have the same SDD scheme."),
                    'records': dif_scheme_payements,
                    'help': _("SDD scheme is set on the customer mandate.")
                })

        return rslt

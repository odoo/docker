# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.exceptions import ValidationError

@tagged('post_install', '-at_install')
class TestAccountBatchPayment(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.other_currency = cls.setup_other_currency('EUR')

        cls.payment_debit_account_id = cls.copy_account(cls.inbound_payment_method_line.payment_account_id)
        cls.payment_credit_account_id = cls.copy_account(cls.outbound_payment_method_line.payment_account_id)

        cls.partner_bank_account = cls.env['res.partner.bank'].create({
            'acc_number': 'BE32707171912447',
            'partner_id': cls.partner_a.id,
            'acc_type': 'bank',
        })

        cls.partner_a.write({
            'bank_ids': [(6, 0, cls.partner_bank_account.ids)],
        })

    def test_create_batch_payment_from_payment(self):
        payments = self.env['account.payment']
        for dummy in range(2):
            payments += self.env['account.payment'].create({
                'amount': 100.0,
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'partner_id': self.partner_a.id,
                'destination_account_id': self.partner_a.property_account_payable_id.id,
                'currency_id': self.other_currency.id,
                'partner_bank_id': self.partner_bank_account.id,
            })

        payments.action_post()
        batch_payment_action = payments.create_batch_payment()
        batch_payment_id = self.env['account.batch.payment'].browse(batch_payment_action.get('res_id'))
        self.assertEqual(len(batch_payment_id.payment_ids), 2)

    def test_change_payment_state(self):
        """
        Check if the amount is well computed when we change a payment state
        """
        payments = self.env['account.payment']
        for _ in range(2):
            payments += self.env['account.payment'].create({
                'amount': 100.0,
                'payment_type': 'inbound',
                'partner_type': 'supplier',
                'partner_id': self.partner_a.id,
                'destination_account_id': self.partner_a.property_account_payable_id.id,
                'partner_bank_id': self.partner_bank_account.id,
            })
        payments.action_post()

        batch_payment = self.env['account.batch.payment'].create(
            {
                'journal_id': payments.journal_id.id,
                'payment_method_id': payments.payment_method_id.id,
                'payment_ids': [
                    (6, 0, payments.ids)
                ],
            }
        )

        self.assertEqual(batch_payment.amount, 200)

        payments[0].move_id.button_draft()

        # Check that we still keep it
        self.assertEqual(batch_payment.amount, 200)

    def test_validate_batch(self):
        """
        Check that we can only validate a batch if all the payments are posted
        """
        payments = self.env['account.payment']
        for _ in range(2):
            payments += self.env['account.payment'].create({
                'amount': 100.0,
                'payment_type': 'inbound',
                'partner_type': 'supplier',
                'partner_id': self.partner_a.id,
                'destination_account_id': self.partner_a.property_account_payable_id.id,
                'partner_bank_id': self.partner_bank_account.id,
            })
        payments.action_post()

        batch_payment = self.env['account.batch.payment'].create(
            {
                'journal_id': payments.journal_id.id,
                'payment_method_id': payments.payment_method_id.id,
                'payment_ids': [Command.set(payments.ids)]
            }
        )

        payments[0].move_id.button_draft()
        payments[0].action_cancel()
        payments[0].action_draft()

        with self.assertRaisesRegex(ValidationError, "All payments must be posted to validate the batch"):
            batch_payment.validate_batch()

        payments[0].action_post()
        batch_payment.validate_batch()

    def test_batch_payment_sub_company(self):
        """Test the creation of a batch payment from a sub company"""
        self.company_data['company'].write({'child_ids': [Command.create({'name': 'Good Company'})]})
        child_comp = self.company_data['company'].child_ids[0]

        # needed for computation of payment.destination_account_id
        field_record = self.env['ir.model.fields']._get('res.partner', 'property_account_receivable_id')
        self.env['ir.default'].search(
            [('field_id', '=', field_record.id), ('company_id', '=', self.company_data['company'].id)], limit=1
        ).copy({'company_id': child_comp.id})

        self.env.user.write({
            'company_ids': [Command.set((self.company_data['company'] + child_comp).ids)],
            'company_id': child_comp.id,
        })

        payment = self.env['account.payment'].with_company(child_comp).create({
            'amount': 100.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
        })
        payment.action_post()

        context = {
            **self.env.context,
            'allowed_company_ids': self.env.company.ids,
            'active_ids': payment.ids,
            'active_model': 'account.payment',
        }

        batch = self.env['account.batch.payment'].with_context(context).create({
            'journal_id': payment.journal_id.id,
        })
        self.assertTrue(batch)

    def test_batch_payment_foreign_currency(self):
        """
        Make sure that payments in foreign currency are converted for the total amount to be displayed
            currency rate = 1$:10€
            amount_company_currency = 100$
            amount_foreign_currency = 100€ -> 10$
            => batch.amount = 110$
        """
        payments = self.env['account.payment']
        company_currency = self.env.company.currency_id
        foreign_currency = self.other_currency

        self.env['res.currency.rate'].create({
            'name': '2024-05-14',
            'rate': 10,
            'currency_id': foreign_currency.id,
            'company_id': self.env.company.id,
        })

        for currency in (company_currency, foreign_currency):
            payments += self.env['account.payment'].create({
                'amount': 100.0,
                'payment_type': 'inbound',
                'partner_type': 'supplier',
                'partner_id': self.partner_a.id,
                'currency_id': currency.id,
                'date': '2024-05-14',
            })

        payments.action_post()
        batch_payment_action = payments.create_batch_payment()
        batch_payment = self.env['account.batch.payment'].browse(batch_payment_action.get('res_id'))
        self.assertEqual(batch_payment.amount, 110)

    def test_batch_payment_journal_foreign_currency(self):
        """
        Test that, if a bank journal is set in a foreign currency, the batch payment will be correctly converted
        currency rate = 1$:10€
        payment of 100€ -> 100☺
        payment of 100$ -> 1000☺
        Total -> 1100
        """
        payments = self.env['account.payment']
        company_currency = self.env.company.currency_id
        foreign_currency = self.other_currency

        self.env['res.currency.rate'].create({
            'name': '2024-05-14',
            'rate': 10,
            'currency_id': foreign_currency.id,
            'company_id': self.env.company.id,
        })
        bank_journal_foreign = self.env['account.journal'].create({
            'name': 'Bank2',
            'type': 'bank',
            'code': 'BNK2',
            'currency_id': foreign_currency.id,
        })

        for currency in (company_currency, foreign_currency):
            payments += self.env['account.payment'].create({
                'amount': 100.0,
                'payment_type': 'inbound',
                'partner_type': 'supplier',
                'partner_id': self.partner_a.id,
                'currency_id': currency.id,
                'date': '2024-05-14',
                'journal_id': bank_journal_foreign.id
            })

        payments.action_post()
        batch_payment_action = payments.create_batch_payment()
        batch_payment = self.env['account.batch.payment'].browse(batch_payment_action.get('res_id'))
        self.assertEqual(batch_payment.amount, 1100)

    def test_create_batch_from_payment_already_in_batch(self):
        payment = self.env['account.payment'].create({
            'amount': 100.0,
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': self.partner_a.id,
            'destination_account_id': self.partner_a.property_account_payable_id.id,
            'currency_id': self.other_currency.id,
            'partner_bank_id': self.partner_bank_account.id,
        })
        payment.action_post()
        batch_payment_action = payment.create_batch_payment()
        batch_payment_id = self.env['account.batch.payment'].browse(batch_payment_action.get('res_id'))
        batch_payment_id.validate_batch()
        with self.assertRaises(ValidationError):
            payment.create_batch_payment()

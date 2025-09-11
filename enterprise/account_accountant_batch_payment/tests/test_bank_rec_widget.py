# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo import Command
from odoo.addons.account_accountant.tests.test_bank_rec_widget_common import TestBankRecWidgetCommon
from odoo.tests import tagged, TransactionCase


class CommonAccountingInstalled(TransactionCase):
    module = 'accounting'
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.classPatch(cls.env.registry['account.move'], '_get_invoice_in_payment_state', lambda self: 'in_payment')
        cls.payment_method_line = cls.company_data['default_journal_bank'].inbound_payment_method_line_ids\
            .filtered(lambda l: l.code == 'batch_payment')

    def _register_payment(self, invoice, **kwargs):
        return self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'payment_method_line_id': self.payment_method_line.id,
            **kwargs,
        })._create_payments()


class CommonInvoicingOnly(TransactionCase):
    module = 'invoicing_only'
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.classPatch(cls.env.registry['account.move'], '_get_invoice_in_payment_state', lambda self: 'paid')
        # When accounting is not installed, outstanding accounts are created and referenced only by xmlid
        xml_id = f"account.{cls.env.company.id}_account_journal_payment_debit_account_id"
        if not cls.env.ref(xml_id, raise_if_not_found=False):
            cls.env['account.account']._load_records([
                {
                    'xml_id': xml_id,
                    'values': {
                        'name': "Outstanding Receipts",
                        'prefix': '123456',
                        'code_digits': 6,
                        'account_type': 'asset_current',
                        'reconcile': True,
                    },
                    'noupdate': True,
                }
            ])


@tagged('post_install', '-at_install')
class TestBankRecWidgetWithoutEntry(CommonAccountingInstalled, TestBankRecWidgetCommon):
    def test_state_changes(self):
        invoice = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[1000.0], post=True)
        invoice_payment = self.env['account.payment.register'].create({
            'payment_date': '2019-01-01',
            'payment_method_line_id': self.payment_method_line.id,
            'line_ids': [Command.set(invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term').ids)],
        })._create_payments()
        from_scratch_payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'amount': 1000,
        })
        from_scratch_payment.action_post()
        for payment, expect_reconcile in [(invoice_payment, True), (from_scratch_payment, self.module == 'invoicing_only')]:
            self.assertFalse(payment.move_id and self.module == 'accounting')
            batch = self.env['account.batch.payment'].create({
                'journal_id': self.company_data['default_journal_bank'].id,
                'payment_ids': [Command.set(payment.ids)],
                'payment_method_id': self.payment_method_line.payment_method_id.id,
            })
            batch.validate_batch()
            self.assertIn(payment.state, self.env['account.batch.payment']._valid_payment_states())
            self.assertEqual(payment.is_sent, True)
            self.assertRecordValues(batch, [{'state': 'sent'}])

            st_line = self._create_st_line(1000.0, payment_ref=batch.name, partner_id=self.partner_a.id)
            wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
            wizard._action_add_new_batch_payments(batch)
            self.assertRecordValues(wizard.line_ids, [
                # pylint: disable=C0326
                {'flag': 'liquidity',       'balance':  1000.0},
                {'flag': 'new_batch',       'balance': -1000.0},
            ])
            wizard._action_validate()

            if self.module == 'accounting':
                counterpart_account = self.partner_a.property_account_receivable_id
            else:
                counterpart_account = self.env['account.payment']._get_outstanding_account('inbound')
            self.assertRecordValues(st_line.move_id.line_ids.sorted('balance'), [
                {'account_id': counterpart_account.id,                   'balance': -1000.0, 'reconciled': expect_reconcile},
                {'account_id': st_line.journal_id.default_account_id.id, 'balance':  1000.0, 'reconciled': False},
            ])
            self.assertRecordValues(payment, [{
                'state': 'paid',
                'is_sent': True,
            }])
            self.assertRecordValues(batch, [{'state': 'reconciled'}])

    def test_writeoff(self):
        invoice = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[1000.0], post=True)
        payment = self.env['account.payment.register'].create({
            'payment_date': '2019-01-01',
            'payment_method_line_id': self.payment_method_line.id,
            'line_ids': [Command.set(invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term').ids)],
        })._create_payments()
        batch = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payment.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })
        batch.validate_batch()

        st_line = self._create_st_line(900.0, payment_ref=batch.name, partner_id=self.partner_a.id)
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_batch_payments(batch)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance':   900.0},
            {'flag': 'new_batch',       'balance': -1000.0},
            {'flag': 'auto_balance',    'balance':   100.0},
        ])
        line = wizard.line_ids.filtered(lambda l: l.flag == 'auto_balance')
        wizard._js_action_mount_line_in_edit(line.index)
        wizard._js_action_line_set_partner_receivable_account(line.index)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance':   900.0},
            {'flag': 'new_batch',       'balance': -1000.0},
            {'flag': 'manual',          'balance':   100.0},
        ])
        wizard._action_validate()

        if self.module == 'accounting':
            counterpart_account = self.partner_a.property_account_receivable_id
        else:
            counterpart_account = self.env['account.payment']._get_outstanding_account('inbound')

        self.assertRecordValues(st_line.move_id.line_ids.sorted('balance'), [
            {'account_id': counterpart_account.id,                           'balance': -1000.0, 'reconciled': True},
            {'account_id': self.partner_a.property_account_receivable_id.id, 'balance':   100.0, 'reconciled': False},
            {'account_id': st_line.journal_id.default_account_id.id,         'balance':   900.0, 'reconciled': False},
        ])

    def test_multiple_exchange_diffs_in_batch(self):
        if self.module == 'invoicing_only':
            self.skipTest('Already tested in TestBankRecWidgetWithEntry')
        # Create a statement line when the currency rate is 1 USD == 2 EUR == 4 CAD
        st_line = self._create_st_line(
            1000.0,
            partner_id=self.partner_a.id,
            date='2017-01-01'
        )
        inv_line = self._create_invoice_line(
            'out_invoice',
            partner_id=self.partner_a.id,
            invoice_line_ids=[{'price_unit': 5000.0, 'tax_ids': []}],
        )
        # Payment when 1 USD == 1 EUR
        payment_eur_gain_diff = self.env['account.payment'].create({
            'date': '2015-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'currency_id': self.other_currency.id,
            'amount': 100.0,
        })
        # Payment when 1 USD == 1 EUR
        payment_eur_gain_diff_2 = self.env['account.payment'].create({
            'date': '2015-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'currency_id': self.other_currency.id,
            'amount': 200.0,
        })
        # Payment when 1 USD == 3 EUR
        payment_eur_loss_diff = self.env['account.payment'].create({
            'date': '2016-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'currency_id': self.other_currency.id,
            'amount': 240.0,
        })
        # Payment when 1 USD == 6 CAD
        payment_cad_loss_diff = self.env['account.payment'].create({
            'date': '2016-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'currency_id': self.other_currency_2.id,
            'amount': 300.0,
        })
        payments = payment_eur_gain_diff + payment_eur_gain_diff_2 + payment_eur_loss_diff + payment_cad_loss_diff
        payments.action_post()

        batch = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payments.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_amls(inv_line)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance': 1000.0},
            {'flag': 'new_aml',         'balance': -1000.0},
        ])

        wizard._action_add_new_batch_payments(batch)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1000.0,     'balance': 1000.0},
            {'flag': 'new_aml',         'amount_currency': -655.0,     'balance': -655.0},
            {'flag': 'new_batch',       'amount_currency': -840.0,     'balance': -430.0},
            {'flag': 'exchange_diff',   'amount_currency':    0.0,     'balance':  150.0},
            {'flag': 'exchange_diff',   'amount_currency':    0.0,     'balance':  -40.0},
            {'flag': 'exchange_diff',   'amount_currency':    0.0,     'balance':  -25.0},
        ])

        wizard._js_action_validate()
        self.assertRecordValues(st_line.move_id.line_ids, [
            {'balance':    -50.0, 'amount_currency':   -100.0, 'amount_residual':    -50.0},
            {'balance':   -100.0, 'amount_currency':   -200.0, 'amount_residual':   -100.0},
            {'balance':   -120.0, 'amount_currency':   -240.0, 'amount_residual':   -120.0},
            {'balance':    -75.0, 'amount_currency':   -300.0, 'amount_residual':    -75.0},
            {'balance':   1000.0, 'amount_currency':   1000.0, 'amount_residual':   1000.0},
            {'balance':   -655.0, 'amount_currency':   -655.0, 'amount_residual':      0.0},
        ])

        reconciled = st_line.move_id.line_ids.matched_debit_ids.debit_move_id | st_line.move_id.line_ids.matched_credit_ids.credit_move_id
        self.assertRecordValues(reconciled, [
            {'balance':   5000.0, 'amount_currency':   5000.0, 'amount_residual':   4345.0},
        ])

    def test_invoice_partial_batch_payment(self):
        invoice = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[1000.0], post=True)
        payment = self.env['account.payment.register'].create({
            'payment_date': '2019-01-01',
            'payment_method_line_id': self.payment_method_line.id,
            'line_ids': [Command.set(invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term').ids)],
            'amount': 500.0,
        })._create_payments()
        batch = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payment.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })
        batch.validate_batch()

        st_line = self._create_st_line(500.0, payment_ref=batch.name, partner_id=self.partner_a.id)
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_batch_payments(batch)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity', 'balance':  500.0},
            {'flag': 'new_batch', 'balance': -500.0},
        ])
        wizard._action_validate()

        if self.module == 'accounting':
            counterpart_account = self.partner_a.property_account_receivable_id
        else:
            counterpart_account = self.env['account.payment']._get_outstanding_account('inbound')

        self.assertRecordValues(st_line.move_id.line_ids.sorted('balance'), [
            {'account_id': counterpart_account.id,                   'balance': -500.0, 'reconciled': True},
            {'account_id': st_line.journal_id.default_account_id.id, 'balance':  500.0, 'reconciled': False},
        ])
        self.assertEqual(invoice.amount_residual, 500.0)
        self.assertEqual(batch.amount_residual, 0.0)

    def test_batch_with_cancelled_or_rejected_payments(self):
        payment_1 = self.env['account.payment'].create({
            'date': '2015-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'amount': 100.0,
        })
        payment_2 = self.env['account.payment'].create({
            'date': '2015-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'amount': 200.0,
        })
        payment_3 = self.env['account.payment'].create({
            'date': '2015-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'amount': 300.0,
        })
        payments = payment_1 + payment_2 + payment_3
        payments.action_post()
        batch = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payments.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })
        batch.validate_batch()
        self.assertEqual(batch.amount_residual, 600.0)
        # cancel first payment
        payment_1.action_cancel()
        # reject second payment
        payment_2.action_reject()
        self.assertEqual(batch.amount_residual, 300.0)

        st_line = self._create_st_line(300.0, payment_ref=batch.name, partner_id=self.partner_a.id)
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_batch_payments(batch)
        wizard._action_validate()
        self.assertEqual(batch.amount_residual, 0.0)
        self.assertEqual(batch.state, 'reconciled')
        self.assertEqual(payment_1.state, 'canceled')
        self.assertEqual(payment_2.state, 'rejected')
        self.assertEqual(payment_3.state, 'paid')

    def test_match_batch_partial_payments(self):
        """ Test reconcile a batch of partial payments with the corresponding statement """
        payments = self.env['account.payment']
        invoice1 = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[10.0], post=True)
        payments |= self._register_payment(invoice1, amount=2.0)
        payments |= self._register_payment(invoice1, amount=2.0)
        invoice2 = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[100.0], post=True)
        payments |= self._register_payment(invoice2, amount=20.0)
        invoice3 = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[1000.0], post=True)
        other_account = self.partner_a.property_account_receivable_id.copy()
        invoice3.line_ids.filtered(lambda l: l.display_type == 'payment_term').account_id = other_account
        payments |= self._register_payment(invoice3, amount=200.0)
        invoice4 = self.init_invoice('out_invoice', partner=self.partner_a, amounts=[10000.0], post=True)
        payments |= self._register_payment(invoice4, amount=20000.0)

        batch = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payments.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })
        batch.validate_batch()

        st_line = self._create_st_line(20224.0, payment_ref=batch.name, partner_id=self.partner_a.id)
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_batch_payments(batch)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance':   20224.0},
            {'flag': 'new_batch',       'balance':  -20224.0},
        ])
        wizard._action_validate()
        self.assertRecordValues(payments, [{'state': 'paid'}] * 5)
        self.assertRecordValues(invoice1 + invoice2 + invoice3 + invoice4, [
            {'amount_residual':   6.0},
            {'amount_residual':  80.0},
            {'amount_residual': 800.0},
            {'amount_residual':   0.0},
        ])

        bank_account = st_line.journal_id.default_account_id
        if self.module == 'accounting':
            receivable = self.partner_a.property_account_receivable_id
            self.assertRecordValues(st_line.move_id.line_ids.sorted('balance'), [
                {'account_id': receivable.id,    'balance': -20000.0, 'amount_residual': -10000.0},
                {'account_id': other_account.id, 'balance':   -200.0, 'amount_residual':      0.0},
                {'account_id': receivable.id,    'balance':    -20.0, 'amount_residual':      0.0},
                {'account_id': receivable.id,    'balance':     -2.0, 'amount_residual':      0.0},
                {'account_id': receivable.id,    'balance':     -2.0, 'amount_residual':      0.0},
                {'account_id': bank_account.id,  'balance':  20224.0, 'amount_residual':  20224.0},
            ])
        else:
            outstanding = self.env['account.payment']._get_outstanding_account('inbound')
            self.assertRecordValues(st_line.move_id.line_ids.sorted('balance'), [
                {'account_id': outstanding.id,   'balance': -20000.0, 'amount_residual':      0.0},
                {'account_id': outstanding.id,   'balance':   -200.0, 'amount_residual':      0.0},
                {'account_id': outstanding.id,   'balance':    -20.0, 'amount_residual':      0.0},
                {'account_id': outstanding.id,   'balance':     -2.0, 'amount_residual':      0.0},
                {'account_id': outstanding.id,   'balance':     -2.0, 'amount_residual':      0.0},
                {'account_id': bank_account.id,  'balance':  20224.0, 'amount_residual':  20224.0},
            ])


@tagged('post_install', '-at_install')
class TestBankRecWidgetWithoutEntryInvoicingOnly(CommonInvoicingOnly, TestBankRecWidgetWithoutEntry):
    allow_inherited_tests_method=True


@tagged('post_install', '-at_install')
class TestBankRecWidgetWithEntry(CommonAccountingInstalled, TestBankRecWidgetCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.payment_method_line.payment_account_id = cls.inbound_payment_method_line.payment_account_id

    def test_matching_batch_payment(self):
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'amount': 100.0,
        })
        payment.action_post()

        batch = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payment.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })
        self.assertRecordValues(batch, [{'state': 'draft'}])

        # Validate the batch and print it.
        batch.validate_batch()
        batch.print_batch_payment()
        self.assertRecordValues(batch, [{'state': 'sent'}])

        st_line = self._create_st_line(1000.0, payment_ref=f"turlututu {batch.name} tsointsoin", partner_id=self.partner_a.id)

        # Create a rule matching the batch payment.
        self.env['account.reconcile.model'].search([('company_id', '=', self.company_data['company'].id)]).unlink()
        rule = self._create_reconcile_model()

        # Ensure the rule matched the batch.
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_trigger_matching_rules()

        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance': 1000.0,  'reconcile_model_id': False},
            {'flag': 'new_aml',         'balance': -100.0,  'reconcile_model_id': rule.id},
            {'flag': 'auto_balance',    'balance': -900.0,  'reconcile_model_id': False},
        ])
        self.assertRecordValues(wizard, [{
            'state': 'valid',
        }])
        wizard._action_validate()

        self.assertRecordValues(batch, [{'state': 'reconciled'}])
        self.assertRecordValues(st_line.move_id.line_ids, [
            {'account_id': st_line.journal_id.default_account_id.id,         'balance': 1000.0, 'reconciled': False},
            {'account_id': payment.outstanding_account_id.id,                'balance': -100.0, 'reconciled': True},
            {'account_id': self.partner_a.property_account_receivable_id.id, 'balance': -900.0, 'reconciled': False},
        ])

    def test_single_payment_from_batch_on_bank_reco_widget(self):
        payments = self.env['account.payment'].create([
            {
                'date': '2018-01-01',
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': self.partner_a.id,
                'payment_method_line_id': self.payment_method_line.id,
                'amount': i * 100.0,
            }
            for i in range(1, 4)
        ])
        payments.action_post()

        # Add payments to a batch.
        batch_payment = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payments.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })

        st_line = self._create_st_line(100.0, partner_id=self.partner_a.id)
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        # Add payment1 from the aml tab
        aml = payments[0].move_id.line_ids.filtered(lambda x: x.account_id.account_type != 'asset_receivable')
        wizard._action_add_new_amls(aml)

        # Validate with one payment inside a batch should reconcile directly the statement line.
        wizard._js_action_validate()
        self.assertTrue(wizard.return_todo_command)
        self.assertTrue(wizard.return_todo_command.get('done'))

        self.assertEqual(batch_payment.amount_residual, sum(payments[1:].mapped('amount')), "The batch amount should change following payment reconciliation")

    def test_multiple_exchange_diffs_in_batch(self):
        # Create a statement line when the currency rate is 1 USD == 2 EUR == 4 CAD
        st_line = self._create_st_line(
            1000.0,
            partner_id=self.partner_a.id,
            date='2017-01-01'
        )
        inv_line = self._create_invoice_line(
            'out_invoice',
            partner_id=self.partner_a.id,
            invoice_line_ids=[{'price_unit': 5000.0, 'tax_ids': []}],
        )
        # Payment when 1 USD == 1 EUR
        payment_eur_gain_diff = self.env['account.payment'].create({
            'date': '2015-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'currency_id': self.other_currency.id,
            'amount': 100.0,
        })
        # Payment when 1 USD == 1 EUR
        payment_eur_gain_diff_2 = self.env['account.payment'].create({
            'date': '2015-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'currency_id': self.other_currency.id,
            'amount': 200.0,
        })
        # Payment when 1 USD == 3 EUR
        payment_eur_loss_diff = self.env['account.payment'].create({
            'date': '2016-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'currency_id': self.other_currency.id,
            'amount': 240.0,
        })
        # Payment when 1 USD == 6 CAD
        payment_cad_loss_diff = self.env['account.payment'].create({
            'date': '2016-01-01',
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'payment_method_line_id': self.payment_method_line.id,
            'currency_id': self.other_currency_2.id,
            'amount': 300.0,
        })
        payments = payment_eur_gain_diff + payment_eur_gain_diff_2 + payment_eur_loss_diff + payment_cad_loss_diff
        payments.action_post()

        self.assertRecordValues(payments.move_id.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_current'), [
            {'balance': 100.0, 'amount_currency': 100.0, 'amount_residual': 100.0},
            {'balance': 200.0, 'amount_currency': 200.0, 'amount_residual': 200.0},
            {'balance':  80.0, 'amount_currency': 240.0, 'amount_residual':  80.0},
            {'balance':  50.0, 'amount_currency': 300.0, 'amount_residual':  50.0},
        ])

        batch = self.env['account.batch.payment'].create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'payment_ids': [Command.set(payments.ids)],
            'payment_method_id': self.payment_method_line.payment_method_id.id,
        })

        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_add_new_amls(inv_line)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'balance': 1000.0},
            {'flag': 'new_aml',         'balance': -1000.0},
        ])

        wizard._action_add_new_batch_payments(batch)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1000.0,     'balance': 1000.0},
            {'flag': 'new_aml',         'amount_currency': -655.0,     'balance': -655.0},
            {'flag': 'new_batch',       'amount_currency': -840.0,     'balance': -430.0},
            {'flag': 'exchange_diff',   'amount_currency': 0.0,        'balance': 150.0},
            {'flag': 'exchange_diff',   'amount_currency': 0.0,        'balance': -40.0},
            {'flag': 'exchange_diff',   'amount_currency': 0.0,        'balance': -25.0},
        ])

        wizard._action_expand_batch_payments(batch)
        self.assertRecordValues(wizard.line_ids, [
            # pylint: disable=C0326
            {'flag': 'liquidity',       'amount_currency': 1000.0,     'balance': 1000.0},
            {'flag': 'new_aml',         'amount_currency': -655.0,     'balance': -655.0},
            {'flag': 'new_aml',         'amount_currency': -100.0,     'balance': -100.0},
            {'flag': 'exchange_diff',   'amount_currency': 0.0,        'balance': 50.0},
            {'flag': 'new_aml',         'amount_currency': -200.0,     'balance': -200.0},
            {'flag': 'exchange_diff',   'amount_currency': 0.0,        'balance': 100.0},
            {'flag': 'new_aml',         'amount_currency': -240.0,     'balance': -80.0},
            {'flag': 'exchange_diff',   'amount_currency': 0.0,        'balance': -40.0},
            {'flag': 'new_aml',         'amount_currency': -300.0,     'balance': -50.0},
            {'flag': 'exchange_diff',   'amount_currency': 0.0,        'balance': -25.0},
        ])

        wizard._js_action_validate()
        A, B, C, D, E, F = st_line.move_id.line_ids.mapped('matching_number')
        self.assertRecordValues(st_line.move_id.line_ids, [
            {'balance':   1000.0, 'amount_currency':   1000.0, 'amount_residual':   1000.0, 'matching_number': A},
            {'balance':   -655.0, 'amount_currency':   -655.0, 'amount_residual':      0.0, 'matching_number': B},
            {'balance':    -50.0, 'amount_currency':   -100.0, 'amount_residual':      0.0, 'matching_number': C},
            {'balance':   -100.0, 'amount_currency':   -200.0, 'amount_residual':      0.0, 'matching_number': D},
            {'balance':   -120.0, 'amount_currency':   -240.0, 'amount_residual':      0.0, 'matching_number': E},
            {'balance':    -75.0, 'amount_currency':   -300.0, 'amount_residual':      0.0, 'matching_number': F},
        ])

        reconciled = st_line.move_id.line_ids.matched_debit_ids.debit_move_id | st_line.move_id.line_ids.matched_credit_ids.credit_move_id
        self.assertRecordValues(reconciled, [
            {'balance':   5000.0, 'amount_currency':   5000.0, 'amount_residual':   4345.0, 'matching_number': B},
            {'balance':    100.0, 'amount_currency':    100.0, 'amount_residual':      0.0, 'matching_number': C},
            {'balance':    200.0, 'amount_currency':    200.0, 'amount_residual':      0.0, 'matching_number': D},
            {'balance':     40.0, 'amount_currency':      0.0, 'amount_residual':      0.0, 'matching_number': E},
            {'balance':     80.0, 'amount_currency':    240.0, 'amount_residual':      0.0, 'matching_number': E},
            {'balance':     25.0, 'amount_currency':      0.0, 'amount_residual':      0.0, 'matching_number': F},
            {'balance':     50.0, 'amount_currency':    300.0, 'amount_residual':      0.0, 'matching_number': F},
        ])
        self.assertRecordValues(payments.move_id.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_current'), [
            {'balance':    100.0, 'amount_currency':    100.0, 'amount_residual':      0.0},
            {'balance':    200.0, 'amount_currency':    200.0, 'amount_residual':      0.0},
            {'balance':     80.0, 'amount_currency':    240.0, 'amount_residual':      0.0},
            {'balance':     50.0, 'amount_currency':    300.0, 'amount_residual':      0.0},
        ])


@tagged('post_install', '-at_install')
class TestBankRecWidgetWithEntryInvoicingOnly(CommonInvoicingOnly, TestBankRecWidgetWithEntry):
    allow_inherited_tests_method=True

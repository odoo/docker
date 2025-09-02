from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestFrenchTaxClosing(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('fr')
    def setUpClass(cls):
        super().setUpClass()

        cls.tax_20_g_purchase = cls.env['account.tax'].search([('type_tax_use', '=', 'purchase'), ('name', '=', '20% G'), ('company_id', '=', cls.company.id)], limit=1)
        cls.tax_20_g_sale = cls.env['account.tax'].search([('type_tax_use', '=', 'sale'), ('name', '=', '20% G'), ('company_id', '=', cls.company.id)], limit=1)
        cls.tax_10_g_purchase = cls.env['account.tax'].search([('type_tax_use', '=', 'purchase'), ('name', '=', '10% G'), ('company_id', '=', cls.company.id)], limit=1)

        cls.tax_10_g_purchase.tax_group_id.tax_receivable_account_id = cls.tax_20_g_purchase.tax_group_id.tax_receivable_account_id.copy()
        cls.report = cls.env.ref('l10n_fr_account.tax_report')
        cls.report_handler = cls.env[cls.report.custom_handler_model_name]

        cls.partner = cls.env['res.partner'].create({
            'name': 'A partner',
        })

        cls.company_data['company'].write({
            'siret': '50056940503239',
            'street': 'Rue du Souleillou',
            'street2': '2',
            'zip': '46800',
            'city': 'Montcuq',
        })

        cls.bank = cls.env['res.bank'].create({
            'name': 'French Bank',
            'bic': 'SOGEFRPP',
        })
        cls.bank_partner = cls.env['res.partner.bank'].create({
            'partner_id': cls.env.company.partner_id.id,
            'acc_number': 'FR3410096000508334859773Z27',
            'bank_id': cls.bank.id,
        })

    @classmethod
    def _get_move_create_data(cls, move_data, line_data):
        return {
            'partner_id': cls.partner.id,
            'invoice_date': '2024-04-15',
            'journal_id': cls.company_data['default_journal_purchase'].id,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Test',
                    'quantity': 1,
                    **line_data,
                })
            ],
            **move_data,
        }

    def test_fr_tax_closing_with_different_tax_groups_and_different_accounts(self):
        """ The aim of this test is testing a case where 2 tax groups have
            different tax_receivable_account_id, and we generate the tax closing
            entries for 2 periods.
            In the first period, we have 2 vendors bills, one using the first
            tax group and the other using the second one.
            We generate the tax closing entry and go to the next period.
            In the next period, we only have one invoice with a tax group
            similar to the first vendor bills.
            The tax closing entry for this period should have a line for the
            customer invoice (a payable line) and one line for the vendors bills
            carried from the previous period, this line comes from the same
            tax group than the payable line.

        """
        self.env['account.move'].create([
            self._get_move_create_data(
                move_data={'move_type': 'in_invoice'},
                line_data={'price_unit': 2000, 'tax_ids': [Command.link(self.tax_20_g_purchase.id)]}
            ),
            self._get_move_create_data(
                move_data={'move_type': 'in_invoice'},
                line_data={'price_unit': 4000, 'tax_ids': [Command.link(self.tax_10_g_purchase.id)]}
            ),
        ])._post()

        options = self._generate_options(
            self.report,
            date_from='2024-04-01',
            date_to='2024-04-30',
        )
        with patch.object(self.env.registry['account.move'], '_get_vat_report_attachments', return_value=[]):
            april_closing_entry = self.report_handler._get_periodic_vat_entries(options)
            april_closing_entry._post()

        self.assertRecordValues(
            april_closing_entry.line_ids,
            [
                {
                    'account_id': self.tax_20_g_purchase.repartition_line_ids.account_id.id,
                    'balance': -400,
                },
                {
                    'account_id': self.tax_10_g_purchase.repartition_line_ids.account_id.id,
                    'balance': -400,
                },
                {
                    'account_id': self.tax_20_g_purchase.tax_group_id.tax_receivable_account_id.id,
                    'balance': 400,
                },
                {
                    'account_id': self.tax_10_g_purchase.tax_group_id.tax_receivable_account_id.id,
                    'balance': 400,
                },
            ]
        )

        self.env['account.move'].create([
            self._get_move_create_data(
                move_data={'move_type': 'out_invoice', 'invoice_date': '2024-05-15', 'journal_id': self.company_data['default_journal_sale'].id},
                line_data={'price_unit': 10000, 'tax_ids': [Command.link(self.tax_20_g_sale.id)]}
            ),
        ])._post()

        options = self._generate_options(
            self.report,
            date_from='2024-05-01',
            date_to='2024-05-31',
        )
        with patch.object(self.env.registry['account.move'], '_get_vat_report_attachments', return_value=[]):
            may_closing_entry = self.report_handler._get_periodic_vat_entries(options)
            may_closing_entry.refresh_tax_entry()
            may_closing_entry._post()

        self.assertRecordValues(
            may_closing_entry.line_ids,
            [
                {
                    'account_id': self.tax_20_g_sale.repartition_line_ids.account_id.id,
                    'balance': 2000,
                },
                {
                    'account_id': self.tax_20_g_purchase.tax_group_id.tax_receivable_account_id.id,
                    'balance': -400,
                },
                {
                    'account_id': self.tax_20_g_sale.tax_group_id.tax_payable_account_id.id,
                    'balance': -1600,
                },
            ]
        )

    def test_fr_send_edi_vat_values_vat_reimbursed_by_administration(self):
        """ The aim of this test is to verify edi VAT values
            once generated and when VAT should be reimbursed by
            the administration.
        """
        self.env['account.move'].create([
            self._get_move_create_data(
                move_data={'move_type': 'in_invoice', 'invoice_date': '2024-05-08', 'journal_id': self.company_data['default_journal_purchase'].id},
                line_data={'price_unit': 1000, 'tax_ids': [Command.link(self.tax_20_g_purchase.id)]}
            ),
            self._get_move_create_data(
                move_data={'move_type': 'in_invoice', 'invoice_date': '2024-05-09', 'journal_id': self.company_data['default_journal_purchase'].id},
                line_data={'price_unit': 667.5, 'tax_ids': [Command.link(self.tax_20_g_purchase.id)]}
            ),
            self._get_move_create_data(
                move_data={'move_type': 'in_invoice', 'invoice_date': '2024-05-12', 'journal_id': self.company_data['default_journal_purchase'].id},
                line_data={'price_unit': 3335, 'tax_ids': [Command.link(self.tax_10_g_purchase.id)]}
            ),
        ])._post()

        send_vat_wizard = self.env['l10n_fr_reports.send.vat.report'].create({
            'date_from': '2024-05-01',
            'date_to': '2024-05-31',
            'report_id': self.report.id,
            'test_interchange': True,
            'bank_account_line_ids': [
                Command.create({
                    'bank_partner_id': self.bank_partner.id,
                    'vat_amount': 667,
                }),
            ],
        })
        options = self._generate_options(
            self.report,
            date_from='2024-05-01',
            date_to='2024-05-31',
            default_options={
                'no_format': True,
                'unfold_all': True,
            }
        )
        lines = self.report._get_lines(options)
        edi_vals = send_vat_wizard._prepare_edi_vals(options, lines)

        values_to_check = [
            ('JA', '667,00'),  # VAT Credit
            ('HG', '667,00'),  # Total deductible
            ('JC', '667,00'),  # Total to carry forward
        ]

        for code, value in values_to_check:
            with self.subTest():
                self.assertIn(
                    {
                        'id': code,
                        'value': value,
                    },
                    edi_vals['declarations'][0]['form']['zones']
                )

        self.assertIn(
            {
                'id': 'GA',
                'iban': 'FR3410096000508334859773Z27',
                'bic': 'SOGEFRPP',
            },
            edi_vals['declarations'][0]['identif']['zones'],
        )
        self.assertIn(
            {
                'id': 'HA',
                'value': '667,00',
            },
            edi_vals['declarations'][0]['identif']['zones'],
        )
        self.assertIn(
            {
                'id': 'KA',
                'value': 'TVA1-20240501-20240531-3310CA3',
            },
            edi_vals['declarations'][0]['identif']['zones'],
        )

    def test_fr_send_edi_vat_values_vat_carry_over(self):
        """ The aim of this test is to verify edi VAT values
            once generated and when VAT is carry over for the
            next period.
        """
        self.env['account.move'].create([
            self._get_move_create_data(
                move_data={'move_type': 'in_invoice', 'invoice_date': '2024-05-08', 'journal_id': self.company_data['default_journal_purchase'].id},
                line_data={'price_unit': 1000, 'tax_ids': [Command.link(self.tax_20_g_purchase.id)]}
            ),
            self._get_move_create_data(
                move_data={'move_type': 'in_invoice', 'invoice_date': '2024-05-09', 'journal_id': self.company_data['default_journal_purchase'].id},
                line_data={'price_unit': 667.5, 'tax_ids': [Command.link(self.tax_20_g_purchase.id)]}
            ),
            self._get_move_create_data(
                move_data={'move_type': 'in_invoice', 'invoice_date': '2024-05-12', 'journal_id': self.company_data['default_journal_purchase'].id},
                line_data={'price_unit': 3335, 'tax_ids': [Command.link(self.tax_10_g_purchase.id)]}
            ),
        ])._post()

        send_vat_wizard = self.env['l10n_fr_reports.send.vat.report'].create({
            'date_from': '2024-05-01',
            'date_to': '2024-05-31',
            'report_id': self.report.id,
            'test_interchange': True,
        })
        options = self._generate_options(
            self.report,
            date_from='2024-05-01',
            date_to='2024-05-31',
            default_options={
                'no_format': True,
                'unfold_all': True,
            }
        )
        lines = self.report._get_lines(options)
        edi_vals = send_vat_wizard._prepare_edi_vals(options, lines)

        values_to_check = [
            ('JA', '667,00'),  # VAT Credit
            ('HG', '667,00'),  # Total deductible
            ('JC', '667,00'),  # Total to carry forward
        ]

        for code, value in values_to_check:
            with self.subTest():
                self.assertIn(
                    {
                        'id': code,
                        'value': value,
                    },
                    edi_vals['declarations'][0]['form']['zones']
                )

        self.assertNotIn(
            {
                'id': 'GA',
                'iban': 'FR3410096000508334859773Z27',
                'bic': 'SOGEFRPP',
            },
            edi_vals['declarations'][0]['identif']['zones'],
        )
        self.assertNotIn(
            {
                'id': 'HA',
                'value': '667,00',
            },
            edi_vals['declarations'][0]['identif']['zones'],
        )
        self.assertNotIn(
            {
                'id': 'KA',
                'value': 'TVA1-20240501-20240531-3310CA3',
            },
            edi_vals['declarations'][0]['identif']['zones'],
        )

    def test_fr_send_edi_vat_values_vat_due_to_administration(self):
        """ The aim of this test is to verify edi VAT values
            once generated and when VAT is due to the administration.
        """
        self.env['account.move'].create([
            self._get_move_create_data(
                move_data={'move_type': 'out_invoice', 'invoice_date': '2024-05-08', 'journal_id': self.company_data['default_journal_sale'].id},
                line_data={'price_unit': 1250, 'tax_ids': [Command.link(self.tax_20_g_sale.id)]}
            ),
            self._get_move_create_data(
                move_data={'move_type': 'out_invoice', 'invoice_date': '2024-05-09', 'journal_id': self.company_data['default_journal_sale'].id},
                line_data={'price_unit': 1250, 'tax_ids': [Command.link(self.tax_20_g_sale.id)]}
            ),
            self._get_move_create_data(
                move_data={'move_type': 'out_invoice', 'invoice_date': '2024-05-12', 'journal_id': self.company_data['default_journal_sale'].id},
                line_data={'price_unit': 1250, 'tax_ids': [Command.link(self.tax_20_g_sale.id)]}
            ),
            self._get_move_create_data(
                move_data={'move_type': 'out_invoice', 'invoice_date': '2024-05-13', 'journal_id': self.company_data['default_journal_sale'].id},
                line_data={'price_unit': 1250, 'tax_ids': [Command.link(self.tax_20_g_sale.id)]}
            ),
        ])._post()

        send_vat_wizard = self.env['l10n_fr_reports.send.vat.report'].create({
            'date_from': '2024-05-01',
            'date_to': '2024-05-31',
            'report_id': self.report.id,
            'test_interchange': True,
            'bank_account_line_ids': [
                Command.create({
                    'bank_partner_id': self.bank_partner.id,
                    'vat_amount': 1000.0,
                })
            ]
        })
        options = self._generate_options(
            self.report,
            date_from='2024-05-01',
            date_to='2024-05-31',
            default_options={
                'no_format': True,
                'unfold_all': True,
            }
        )
        lines = self.report._get_lines(options)
        edi_vals = send_vat_wizard._prepare_edi_vals(options, lines)

        values_to_check = [
            ('CA', '5000,00'),  # Taxable value
            ('FP', '5000,00'),  # Base 20%
            ('GP', '1000,00'),  # Tax 20%
            ('KA', '1000,00'),  # VAT Due
            ('GH', '1000,00'),  # Total gross VAT due
            ('ND', '1000,00'),  # Total net VAT due
            ('KE', '1000,00'),  # Total payable
        ]

        for code, value in values_to_check:
            with self.subTest():
                self.assertIn(
                    {
                        'id': code,
                        'value': value,
                    },
                    edi_vals['declarations'][0]['form']['zones']
                )

        self.assertIn(
            {
                'id': 'GA',
                'iban': 'FR3410096000508334859773Z27',
                'bic': 'SOGEFRPP',
            },
            edi_vals['declarations'][0]['identif']['zones'],
        )
        self.assertIn(
            {
                'id': 'HA',
                'value': '1000,00',
            },
            edi_vals['declarations'][0]['identif']['zones'],
        )
        self.assertIn(
            {
                'id': 'KA',
                'value': 'TVA1-20240501-20240531-3310CA3',
            },
            edi_vals['declarations'][0]['identif']['zones'],
        )

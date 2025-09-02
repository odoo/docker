from freezegun import freeze_time
from odoo import Command

from odoo.addons.l10n_cl_edi.tests.common import TestL10nClEdiCommon
from odoo.tools import misc
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiFactoring(TestL10nClEdiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].write({
            'l10n_cl_dte_service_provider': 'SIIDEMO',
            'l10n_cl_factoring_journal_id': cls.env['account.journal'].search([('type', '=', 'general')], limit=1).id,
            'l10n_cl_factoring_counterpart_account_id': cls.env['account.account'].search(
                [('account_type', '=', 'asset_current')], limit=1).id,
        })

    @freeze_time('2024-06-10T17:00:00', tz_offset=3)
    def test_factoring_with_aec(self):
        self.partner_factoring = self.env['res.partner'].create({
            'name': 'Partner Factoring S.A.',
            'is_company': 1,
            'city': 'Pudahuel',
            'country_id': self.env.ref('base.cl').id,
            'street': 'Puerto Test 105',
            'phone': '+562 0000 1111',
            'email': 'email@myfactoring.cl',
            'l10n_cl_dte_email': 'dte@myfactoring.cl',
            'l10n_latam_identification_type_id': self.env.ref('l10n_cl.it_RUT').id,
            'l10n_cl_sii_taxpayer_type': '1',
            'l10n_cl_activity_description': 'activity_test',
            'vat': '76086428-5',
            'l10n_cl_is_factoring': True,
        })
        self.tax_19 = self.env['account.tax'].search([
            ('name', '=', '19% VAT'),
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', self.company_data['company'].id)])
        self.account_receivable = self.env['account.account'].search(
            [('account_type', '=', 'asset_receivable')], limit=1)
        self.account_income = self.env['account.account'].search(
            [('account_type', '=', 'income')], limit=1)
        self.product_a = self.env['product.product'].create({
            'name': 'product test',
            'type': 'service',
            'list_price': 30000.0,
            'taxes_id': [Command.set(self.tax_19.ids)],
        })

        invoice = self.env['account.move'].create({
            'partner_id': self.partner_sii.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'quantity': 1.0,
                'name': 'product test',
                'price_unit': 30000.0,
                'tax_ids': [Command.set(self.tax_19.ids)],
                'account_id': self.account_income.id,
            })],
            'invoice_date': '2024-06-10',
            'invoice_date_due': '2024-06-11',
            'journal_id': self.env['account.journal'].search([('code', '=', 'INV2')], limit=1).id,
        })
        invoice.action_post()
        invoice.l10n_cl_send_dte_to_sii()

        # "Ensure that the invoice has been posted"
        self.assertEqual(invoice.state, 'posted', "The invoice has not been posted")
        self.assertEqual(invoice.l10n_cl_dte_status, 'accepted', "The invoice has not been marked as accepted by SII")

        # Inicialize the wizard
        aec_generator = self.env['l10n_cl.aec.generator'].create({
            'partner_id': self.partner_factoring.id,
        })
        generated_moves = aec_generator.with_context(active_ids=[invoice.id]).create_aec()
        with misc.file_open('l10n_cl_edi_factoring/tests/expected_aec/expected_aec.xml', 'rb') as f:
            expected_aec = f.read()

        self.maxDiff = None
        for move in generated_moves:
            self.assertXmlTreeEqual(
                self.get_xml_tree_from_attachment(move.l10n_cl_aec_attachment_id),
                self.get_xml_tree_from_string(expected_aec)
            )

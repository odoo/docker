from odoo import Command
from odoo.tests.common import tagged

from . import common


@tagged("-at_install", "post_install", "post_install_l10n", "manual")
class TestManual(common.TestUyEdi):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_uy.l10n_uy_edi_ucfe_env = "demo"

    def test_10_post_invoice(self):
        """ Post EDI UY invoice
        * default invoice is e-ticket,
        * default taxes auto applied on lines is 22% vat tax
        * name after post (should have * ID name)
        """
        invoice = self._create_move()
        self.assertEqual(invoice.company_id, self.company_uy, "created with wrong company")
        self.assertEqual(invoice.journal_id.l10n_uy_edi_type, "electronic", "Invoice is not created on EDI journal")
        self.assertEqual(invoice.amount_tax, 22, "invoice taxes are not properly set")
        self.assertEqual(invoice.amount_total, 122.0, "invoice taxes has not been applied to the total")
        invoice.action_post()
        self.assertEqual(invoice.state, "posted", "invoice has not been validate in Odoo")
        self.assertEqual(invoice.name, "* %s" % invoice.id, "Not expected name")

    def test_20_e_ticket_xml(self):
        """ Create/post/send an e-ticket and check that the pre-generated XML is the same as the one expected """
        invoice = self._create_move()
        self.assertEqual(invoice.l10n_latam_document_type_id.code, "101", "Not e-ticket")
        invoice.action_post()
        self._send_and_print(invoice)
        self._check_cfe(invoice, "e-TK", "20_e_ticket")

    def test_30_e_invoice_xml(self):
        """ Create e-Invoice, and check that the pre-generated xml is the same as the one expected """
        invoice = self._create_move(
            partner_id=self.partner_local.id,
            l10n_latam_document_type_id=self.env.ref("l10n_uy.dc_e_inv").id
        )
        self.assertEqual(invoice.l10n_latam_document_type_id.code, "111", "Not an e-invoice")
        invoice.action_post()
        self._send_and_print(invoice)
        self._check_cfe(invoice, "e-FC", "30_e_invoice")

    def test_40_e_expo_invoice(self):
        """ Create an Expo e-invoice, and check that the pre-generated xml is the same as the one expected """
        invoice = self._create_move(
            l10n_latam_document_type_id=self.env.ref("l10n_uy.dc_e_inv_exp").id,
            partner_id=self.foreign_partner.id,
            invoice_incoterm_id=self.env.ref("account.incoterm_FOB").id,
            l10n_uy_edi_cfe_sale_mode="1",
            l10n_uy_edi_cfe_transport_route="1",
            invoice_line_ids=[Command.create({"product_id": self.product_vat_22.id, "price_unit": 100.0})],
        )
        self.assertEqual(invoice.l10n_latam_document_type_id.code, "121", "Not Expo e-invoice")
        invoice.action_post()

        # IndFact lo cambié de 3 a 10
        self._send_and_print(invoice)
        self._check_cfe(invoice, "e-FCE", "40_e_expo_invoice")

    def test_50_e_ticket_multi_tax_xml(self):
        """ Create/post/send an e-ticket with multi tax and check that the pre-generated XML is the same as the one expected """
        invoice = self._create_move(
            invoice_line_ids=[
                Command.create({
                    "product_id": self.service_vat_22.id,
                    "price_unit": 100.0,
                }),
                Command.create({
                    "product_id": self.service_vat_10.id,
                    "quantity": 2,
                    "price_unit": 150,
                }),
            ]
        )
        self.assertEqual(invoice.l10n_latam_document_type_id.code, "101", "Not e-ticket")
        invoice.action_post()
        self._send_and_print(invoice)
        self._check_cfe(invoice, "e-TK", "50_e_ticket_multi_tax")

    def test_60_another_currency(self):
        """ create an invoice with different currency, also test that Incoterm/Transport is properly set for services """
        invoice = self._create_move(
            l10n_latam_document_type_id=self.env.ref("l10n_uy.dc_e_inv_exp").id,
            partner_id=self.foreign_partner.id,
            l10n_uy_edi_cfe_sale_mode="1",
            l10n_uy_edi_cfe_transport_route="1",
            currency_id=self.env.ref("base.USD").id,
        )
        self.assertEqual(invoice.l10n_latam_document_type_id.code, "121", "Not Expo e-invoice")
        invoice.action_post()
        self._send_and_print(invoice)
        self._check_cfe(invoice, "e-FCE", "60_e_invoice_another_currency")

    def test_70_tax_included(self):
        tax_22_included = self.tax_22.copy({"price_include_override": "tax_included", "name": "22% VAT (included)"})
        tax_10_included = self.tax_10.copy({"price_include_override": "tax_included", "name": "10% VAT (included)"})
        tax_0_included = self.tax_0.copy({"price_include_override": "tax_included", "name": "0% VAT (included)"})
        invoice = self._create_move(
            partner_id=self.partner_local.id,
            l10n_latam_document_type_id=self.env.ref("l10n_uy.dc_e_inv").id,
            invoice_line_ids=[
                Command.create({
                    "product_id": self.service_vat_22.id,
                    "price_unit": 1000,
                    "tax_ids": tax_22_included,
                }),
                Command.create({
                    "product_id": self.service_vat_22.id,
                    "quantity": 2,
                    "price_unit": 150,
                    "tax_ids": tax_10_included,
                }),
                Command.create({
                    "product_id": self.service_vat_22.id,
                    "quantity": 2,
                    "price_unit": 150,
                    "tax_ids": tax_0_included,
                }),
            ],
        )

        invoice.action_post()
        self.assertEqual(invoice.l10n_latam_document_type_id.code, "111", "Not e-invoice")
        self._send_and_print(invoice)
        self._check_cfe(invoice, "e-FC", "70_e_invoice_tax_included")

    def test_80_e_ticket_credit_note(self):
        """ Create a credit note, validate it, check that we do not get any error. """
        invoice = self._create_move()
        invoice.action_post()
        self._send_and_print(invoice)
        self._check_cfe(invoice, "e-TK", "20_e_ticket")

        refund = self._create_credit_note(invoice)
        refund.action_post()
        self.assertEqual(refund.l10n_latam_document_type_id.code, "102", "Not Credit not document type.")
        self._send_and_print(refund)
        self._check_cfe(refund, "e-NCTK", "80_e_ticket_credit_note")

    def test_90_e_ticket_debit_note(self):
        """ Create a credit note, validate it, check that we do not get any error. """
        invoice = self._create_move()
        invoice.action_post()
        self._send_and_print(invoice)
        self._check_cfe(invoice, "e-TK", "20_e_ticket")
        refund = self._create_debit_note(invoice)
        refund.action_post()
        self.assertEqual(refund.l10n_latam_document_type_id.code, "103", "Not Debit not document type.")
        self._send_and_print(refund)
        self._check_cfe(refund, "e-NDTK", "90_e_ticket_debit_note")

    def test_100_e_ticket_with_disclosures(self):
        """ Create/post/send an e-ticket with disclosures and check that the pre-generated XML is the same as the one
        expected """
        item_legend = self.env['l10n_uy_edi.addenda'].create({
            "type": 'item',
            "is_legend": True,
            "name": 'Leyenda Product/Service Detail',
            "content": 'Leyenda Product/Service Detail',
            "company_id": self.env.company.id
        })
        l10n_uy_edi_addenda_ids = self.env['l10n_uy_edi.addenda'].create({
            "type": 'cfe_doc',
            "is_legend": True,
            "name": 'CFE Legend',
            "content": 'CFE Legend',
            "company_id": self.env.company.id
        })
        invoice = self._create_move(
            l10n_uy_edi_addenda_ids=l10n_uy_edi_addenda_ids.ids,
            invoice_line_ids=[Command.create({
                "product_id": self.service_vat_22.id,
                "price_unit": 100.0,
                "l10n_uy_edi_addenda_ids": item_legend.ids,
            })],
        )
        self.assertEqual(invoice.l10n_latam_document_type_id.code, "101", "Not e-ticket")
        invoice.action_post()
        self._send_and_print(invoice)
        self._check_cfe(invoice, "e-TK", "100_e_ticket_disclosures")

    def test_120_e_ticket_final_consumer(self):
        """ Create/post/send an e-ticket and check that the pre-generated XML is the same as the one expected """
        invoice = self._create_move(partner_id=self.env.ref("l10n_uy.partner_cfu").id)
        self.assertEqual(invoice.l10n_latam_document_type_id.code, "101", "Not e-ticket")
        invoice.action_post()
        self._send_and_print(invoice)
        self._check_cfe(invoice, "e-TK", "120_e_ticket_final_consumer")

    def test_default_doc_type_by_id(self):
        dc_e_inv = self.env.ref('l10n_uy.dc_e_inv')
        move = self._create_move(partner_id=self.env.ref("l10n_uy.partner_cfu").id)
        self.assertEqual(move.l10n_latam_document_type_id, self.env.ref('l10n_uy.dc_e_ticket'), "The document type is not being set correctly.")
        move.partner_id = self.env.ref('l10n_uy.partner_dgi').id
        self.assertEqual(move.l10n_latam_document_type_id, dc_e_inv, "The expected document should be e-invoice")

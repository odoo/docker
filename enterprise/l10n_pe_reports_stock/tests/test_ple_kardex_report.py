import base64
from freezegun import freeze_time

from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo import Command
from odoo.tests import Form, tagged


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestPleKardexReport(TestSaleCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('pe')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data["company"].country_id = cls.env.ref("base.pe")
        cls.company_data["company"].vat = "20512528458"
        cls.partner_a.write({"country_id": cls.env.ref("base.pe").id, "vat": "20557912879", "l10n_latam_identification_type_id": cls.env.ref("l10n_pe.it_RUC").id})

    @freeze_time('2024-01-01')
    def test_kardex_report(self):
        """Ensure that kardex report is generated correctly with a sale order and a purchase order"""

        sale = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'name': p.name,
                    'product_id': p.id,
                    'product_uom_qty': 2,
                    'product_uom': p.uom_id.id,
                    'price_unit': p.list_price,
                    'tax_id': [Command.set(self.env.ref(f"account.{self.env.company.id}_sale_tax_igv_18").ids)],
                }) for p in (
                    self.company_data['product_order_no'],
                    self.company_data['product_service_delivery'],
                    self.company_data['product_service_order'],
                    self.company_data['product_delivery_no'],
                )],
            'pricelist_id': self.company_data['default_pricelist'].id,
            'picking_policy': 'direct',
        })

        # confirm our standard so, check the picking
        sale.action_confirm()
        self.assertTrue(sale.picking_ids, 'Sale Stock: no picking created for "invoice on delivery" storable products')

        # Process picking
        pick = sale.picking_ids
        pick.move_ids.write({'quantity': 2, 'picked': True})
        pick.button_validate()

        # invoice on order
        sale._create_invoices()
        sale.invoice_ids.action_post()

        # Purchase
        purchase = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'name': self.company_data['product_order_no'].name,
                    'product_id': self.company_data['product_order_no'].id,
                    'product_qty': 5.0,
                    'product_uom': self.company_data['product_order_no'].uom_po_id.id,
                    'price_unit': 500.0,
                })],
        })

        purchase.button_confirm()

        picking = purchase.picking_ids
        picking.move_line_ids.write({'quantity': 5.0, 'picked': True})
        picking.button_validate()

        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.partner_id = self.partner_a
        move_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-purchase.id)
        move_form.invoice_date = '2024-01-01'
        move_form.l10n_latam_document_type_id = self.env.ref("l10n_pe.document_type01")
        move_form.l10n_latam_document_number = "BILL/2024/01/0001"
        invoice = move_form.save()
        invoice.action_post()

        # ==== Report ====
        wizard = self.env['l10n_pe.stock.ple.wizard'].create({
            'date_from': '2024-01-01',
            'date_to': '2024-01-31',
        })
        wizard.get_ple_report_12_1()

        self.maxDiff = None
        self.assertSequenceEqual(
            base64.b64decode(wizard.report_data).decode().split('\n'),
            [
                '20240100|000000|M1|0000|1|99|FURN9999|1||01/01/2024|01|FFFI|00000001|01|product_order_no|NIU|0.00|-2.0|1|',
                '20240100|000001|M1|0000|1|99|FURN7777|1||01/01/2024|01|FFFI|00000001|01|product_delivery_no|NIU|0.00|-2.0|1|',
                '20240100|000002|M1|0000|1|99|FURN9999|1||01/01/2024|01|FBILL202401|0001|02|product_order_no|NIU|5.0|0.00|1|',
                '',
            ]
        )

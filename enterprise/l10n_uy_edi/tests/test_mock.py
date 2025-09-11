from odoo.tests.common import tagged

from odoo.exceptions import UserError

from . import common


@tagged("-at_install", "post_install", "post_install_l10n", "mock")
class TestMock(common.TestUyEdi):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_uy.write({
            "l10n_uy_edi_ucfe_env": "testing",
            "l10n_uy_edi_ucfe_password": "password_xxx",
            "l10n_uy_edi_ucfe_commerce_code": "commerce_xxx",
            "l10n_uy_edi_ucfe_terminal_code": "terminal_xxx",
        })

    def test_10_missing_credentials(self):
        self.company_uy.l10n_uy_edi_ucfe_commerce_code = False

        error_msg = self._mock_check_credentials(self.company_uy, "NO_RESPONSE")
        self.assertRegex(error_msg, "Incomplete Data to connect to Uruware.*Please complete the UCFE data to test the connection: Uruware Commerce code")

    def test_20_bad_credentials(self):
        self.company_uy.l10n_uy_edi_ucfe_commerce_code = "comerce_xxx1"

        error_msg = self._mock_check_credentials(self.company_uy, "mock_20_bad_credentials")
        self.assertRegex(error_msg, "Las credenciales no son v.*lidas")

    def test_30_invoice_bad_credentials(self):
        """ try to send and print and process a bad credentials error """
        self.company_uy.l10n_uy_edi_ucfe_password = "password_wrong"
        invoice = self._create_move()
        invoice.action_post()
        error_msg = "Fault Error - Las credenciales no son v.*lidas"
        with self.assertRaisesRegex(UserError, error_msg):
            self._mock_send_and_print(invoice, "mock_30_invoice_bad_credentials")

        self.assertEqual(invoice.name, "* %s" % invoice.id, "Name should remain * ID because is was not process")
        self.assertEqual(invoice.l10n_uy_edi_cfe_state, "error")
        self.assertRegex(invoice.l10n_uy_edi_error, error_msg)

    def test_35_invoice_bad_commerce(self):
        """ everything is ok but the commerce is wrong """
        self.company_uy.l10n_uy_edi_ucfe_commerce_code = "commerce_xxx1"
        invoice = self._create_move()
        invoice.action_post()
        error_msg = "- Response Error - Code: 500 Las credenciales no son v.*lidas"
        with self.assertRaisesRegex(UserError, error_msg):
            self._mock_send_and_print(invoice, "mock_20_bad_credentials")

    def test_40_invoice_connection_error(self):
        invoice = self._create_move()
        invoice.action_post()
        with self.assertRaisesRegex(UserError, "Timeout"):
            self._mock_send_and_print(invoice, exception="Timeout", expected_xml_file="NO_RESPONSE")

    def test_80_invoice_accepted_and_pdf(self):
        """ process an accepted invoice and generate the legal pdf """
        invoice = self._create_move()
        invoice.action_post()
        self._mock_send_and_print(invoice, "mock_80_invoice_accepted", get_pdf=True)

        self.assertEqual(invoice.l10n_uy_edi_cfe_state, "accepted")
        self.assertTrue(invoice.invoice_pdf_report_file, "The pdf file was not created.")

    def test_90_invoice_received_pdf_check_status(self):
        invoice = self._create_move()
        invoice.action_post()
        self._mock_send_and_print(invoice, "mock_90_invoice_received", get_pdf=True)

        self.assertEqual(invoice.l10n_uy_edi_cfe_state, "received")
        self.assertTrue(invoice.invoice_pdf_report_file, "The pdf file was not created.")

        self._mock_update_dgi_state(invoice, "mock_90_invoice_received")
        self.assertEqual(invoice.l10n_uy_edi_cfe_state, "accepted")

    def test_100_invoice_rejected(self):
        """ simulate we have a invoice in state received. then check status from uruware and receive
        rejected state """
        invoice = self._create_move()
        invoice.action_post()
        self._mock_send_and_print(invoice, "mock_90_invoice_received", get_pdf=True)

        self.assertEqual(invoice.l10n_uy_edi_cfe_state, "received")
        self.assertTrue(invoice.invoice_pdf_report_file, "The pdf file was not created.")

        self._mock_update_dgi_state(invoice, "mock_invoice_rejected")
        self.assertEqual(invoice.l10n_uy_edi_cfe_state, "rejected")

    def test_110_invoice_error(self):
        """ capture error return by DGI because the data we send in the XML is not valid """
        partner_local_with_error = self.env["res.partner"].create({
            "name": "IEB Internacional",
            "l10n_latam_identification_type_id": self.env.ref("l10n_uy.it_dni").id,
            "vat": "218435730016",
            "street": "Bach 0",
            "city": "Aeroparque",
            "state_id": self.env.ref("base.state_uy_02").id,
            "country_id": self.env.ref("base.uy").id,
            "email": "rut@example.com",
        })
        invoice = self._create_move(partner_id=partner_local_with_error.id)
        invoice.action_post()
        error_msg = ".*por lo que se espera país AR, BR, CL ó PY, pero se recibió UY.*"
        with self.assertRaisesRegex(UserError, error_msg):
            self._mock_send_and_print(invoice, "mock_110_invoice_error")

        self.assertFalse(invoice.invoice_pdf_report_file, "Since we have an error the pdf file must not exist.")
        self.assertEqual(invoice.l10n_uy_edi_cfe_state, "error")
        self.assertRegex(invoice.l10n_uy_edi_error, error_msg)

    def test_120_invoice_internal_validation_fail(self):
        """ capture error before sending to uruware, check that we capture and the invoice is not marked as error """
        export_invoice = self.env.ref("l10n_uy.dc_e_inv_exp")
        invoice = self._create_move(
            partner_id=self.foreign_partner.id,
            l10n_latam_document_type_id=export_invoice.id,
        )
        invoice.write({
            "invoice_incoterm_id": self.env.ref("account.incoterm_FOB"),
            "l10n_uy_edi_cfe_sale_mode": "1",
            "l10n_uy_edi_cfe_transport_route": "1",
        })
        self.assertEqual(invoice.l10n_latam_document_type_id.code, "121", "Not Expo e-invoice")
        invoice.invoice_line_ids.tax_ids = self.tax_22
        invoice.action_post()
        with self.assertRaisesRegex(UserError, "Export CFE can only have 0% vat taxes"):
            self._mock_send_and_print(invoice, expected_xml_file="NO_RESPONSE")

        # Since is an internal pre send to dgi validation the state and error in the invoice should be unset
        self.assertFalse(invoice.l10n_uy_edi_cfe_state)
        self.assertFalse(invoice.l10n_uy_edi_error)

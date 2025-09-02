# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import tagged
from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontend
from odoo import Command, http
from odoo.addons.point_of_sale.controllers.main import PosController


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestFiskalyPoS(TestFrontend):
    def install_fiskalyhook(self):
        def auth_hook(self):
            return {}

        def vat_definition_hook(self):
            return http.Response(
            '{"data": [{"percentage": 19, "vat_definition_export_id": 1}, {"percentage": 7, "vat_definition_export_id": 2}, {"percentage": 10.7, "vat_definition_export_id": 3}, {"percentage": 5.5, "vat_definition_export_id": 4}, {"percentage": 0, "vat_definition_export_id": 5}]}',
            content_type="application/json",
        )

        def tss_hook(self, tx_id, tss_id, **kwargs):
            return http.Response(
                '{"time_end": 20000, "time_start": 10000, "tss_serial_number": "12345-abcdes", "log": {"timestamp_format": "format"}, "signature": {"value": 12345, "algorithm": "fake_algo", "public_key": "fake_key", "client_serial_number": "fake_csn"}}',
                content_type="application/json",
            )

        self.env.registry.clear_cache('routing')
        PosController.auth_hook_v0 = http.route("/fake_fiskaly/api/v0/auth", type="json", methods=["POST"], csrf=False)(auth_hook)
        PosController.auth_hook_v1 = http.route("/fake_fiskaly/api/v1/auth", type="json", methods=["POST"], csrf=False)(auth_hook)
        PosController.tss_hook = http.route(["/fake_fiskaly/api/v1/tss/<int:tss_id>/tx/<string:tx_id>"], methods=["PUT"], type="http", csrf=False)(tss_hook)
        PosController.vat_definition_hook = http.route(["/fake_fiskaly/api/v0/vat_definitions"], type="http")(vat_definition_hook)

        @self.addCleanup
        def _cleanup():
            del PosController.auth_hook_v0
            del PosController.auth_hook_v1
            del PosController.tss_hook
            del PosController.vat_definition_hook
            self.env.registry.clear_cache('routing')

    def test_fiskaly_basic_order(self):
        self.install_fiskalyhook()
        self.env['ir.config_parameter'].sudo().set_param('l10n_de_fiskaly_kassensichv_url', 'http://127.0.0.1:8069/fake_fiskaly')
        self.env['ir.config_parameter'].sudo().set_param('l10n_de_fiskaly_dsfinvk_url', 'http://127.0.0.1:8069/fake_fiskaly')

        self.company.write({
            "country_id": self.env.ref('base.de'),
            "l10n_de_fiskaly_organization_id": "12345679",
            "l10n_de_fiskaly_api_secret": "123456789",
            "l10n_de_fiskaly_api_key": "123456789",
        })
        self.main_pos_config.write({
            "l10n_de_fiskaly_tss_id": "123456798",
            "l10n_de_fiskaly_client_id": "123456798",
        })
        self.env['res.partner'].create({
            "name": "AA Test Partner",
        })
        self.env['pos.printer'].search([]).write({
            "product_categories_ids": [Command.clear()],
        })
        self.env['pos_preparation_display.display'].create({
            'name': 'Preparation Display',
        })
        # Create a valid tax for fiskaly
        normal_tax = self.env['account.tax'].create({
            "name": "NORMAL",
            "amount": 19,
        })
        desk = self.env['product.product'].search([('name', '=', 'Coca-Cola')])
        desk.taxes_id = normal_tax
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'FiskalyTour', login="pos_user")

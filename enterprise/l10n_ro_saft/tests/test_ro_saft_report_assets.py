# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.addons.l10n_ro_saft.tests.test_ro_saft_report_monthly import TestRoSaftReport
from odoo.tests import Form, tagged
from odoo import Command, fields


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestRoSaftReportAssets(TestRoSaftReport):
    """ Test the generation of the SAF-T Asset Declaration export for Romania."""

    @classmethod
    @TestAccountReportsCommon.setup_country('ro')
    def setUpClass(cls):
        """
        Tests the SAF-T Asset Declaration export
        The following use cases are tested in a single export, each one applied on a different asset for simplicity:
        - purchase of asset
        - increase in value of asset
        - decrease in value of asset
        - selling of asset
        - disposal of asset
        - depreciation of asset
        """

        def copy_and_validate_asset(asset, name):
            new_truck = asset.copy()
            new_truck.name = name
            new_truck.validate()
            return new_truck

        super().setUpClass()

        asset_account_id = cls.company_data['default_account_assets'].id
        loss_account_id = cls.company_data['default_account_expense'].id
        counterpart_account_id = cls.company_data['default_account_expense'].copy().id

        cls.bill = cls.env['account.move'].create([
            {
                'move_type': 'in_invoice',
                'invoice_date': '2023-01-01',
                'date': '2023-01-01',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [Command.create({
                    'name': 'Truck',
                    'account_id': asset_account_id,
                    'quantity': 1.0,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(cls.company_data['default_tax_sale'].ids)],
                })],
            },
        ])
        cls.bill.action_post()

        # Purchase
        asset_line = cls.bill.line_ids.filtered(lambda x: x.account_id.id == asset_account_id)
        asset_form = Form(cls.env['account.asset'].with_context(default_original_move_line_ids=asset_line.ids))
        asset_form.account_depreciation_expense_id = cls.company_data['default_account_expense']
        asset_form.l10n_ro_saft_account_asset_category_id = cls.env.ref('l10n_ro_saft.l10n_ro_saft_1_1_2_1')
        cls.truck = asset_form.save()
        cls.truck.validate()

        cls.truck_to_increase = copy_and_validate_asset(cls.truck, 'Truck to increase')
        cls.truck_to_decrease = copy_and_validate_asset(cls.truck, 'Truck to decrease')
        cls.truck_to_sell = copy_and_validate_asset(cls.truck, 'Truck to sell')
        cls.truck_to_dispose = copy_and_validate_asset(cls.truck, 'Truck to dispose')

        # Positive revaluation
        cls.env['asset.modify'].create({
            'name': 'New beautiful sticker :D',
            'asset_id': cls.truck_to_increase.id,
            'value_residual': cls.truck_to_increase._get_residual_value_at_date(fields.Date.to_date('2023-06-30')) + 80,
            'salvage_value': 0,
            'date': '2023-06-30',
            "account_asset_counterpart_id": counterpart_account_id,
        }).modify()

        # Negative revaluation
        cls.env['asset.modify'].create({
            'name': 'Little scratch :(',
            'asset_id': cls.truck_to_decrease.id,
            'value_residual': cls.truck_to_decrease._get_residual_value_at_date(fields.Date.to_date('2023-06-30')) - 50,
            'salvage_value': 0,
            'date': '2023-06-30',
            "account_asset_counterpart_id": counterpart_account_id,
        }).modify()

        # Dispose
        disposal_action_view = cls.env['asset.modify'].create({
            'asset_id': cls.truck_to_dispose.id,
            'modify_action': 'dispose',
            'loss_account_id': loss_account_id,
            'date': '2023-06-30',
        }).sell_dispose()

        cls.env['account.move'].browse(disposal_action_view['res_id']).action_post()

        # Sell
        closing_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_line_ids': [Command.create({'price_unit': 900})]  # amount at 2023-06-30 - perfect sale
        })
        cls.env['asset.modify'].create({
            'asset_id': cls.truck_to_sell.id,
            'modify_action': 'sell',
            'invoice_line_ids': closing_invoice.invoice_line_ids,
            'date': '2023-06-30',
        }).sell_dispose()
        selling_move = cls.truck_to_sell.depreciation_move_ids.filtered(lambda l: l.state == 'draft')
        selling_move.action_post()

    @freeze_time('2024-01-01')
    def test_l10n_ro_saft_report_assets(self):
        self._report_compare_with_test_file(
            self.report_handler.l10n_ro_export_saft_to_xml_assets(self._generate_options(
                date_from='2023-01-01',
                date_to='2023-12-31',
            )),
            'saft_report_assets.xml'
        )

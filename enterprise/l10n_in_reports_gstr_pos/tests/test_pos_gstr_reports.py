# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo

from datetime import date
from freezegun import freeze_time

from .common import TestInGstrPosBase
from .gstr_test_json import expected_gstr1_pos_response

TEST_DATE = date(2023, 5, 20)


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestInGstrPosGSTR(TestInGstrPosBase):
    """
    Test class for GSTR-related POS functionality.
    """

    @freeze_time('2023-05-20')
    def test_gstr1_json_generation_with_pos_refund_order(self):
        """Test case for partial refund and GSTR1 JSON generation."""
        with self.with_pos_session() as session:
            # Step 1: Create an order with two products
            order = self._create_order({
                'pos_order_lines_ui_args': [
                    (self.product_a, 2.0),  # Buying 2 units of product_a
                    (self.product_b, 2.0),  # Buying 2 units of product_b
                ],
                'payments': [(self.bank_pm1, 630.0)],  # Payment of 630
            })

            # Step 2: Create a refund for one product line
            self._create_order({
                'pos_order_lines_ui_args': [
                    {
                        'product': self.product_b,
                        'quantity': -1.0,  # Refund 1 unit of product_b
                        'refunded_orderline_id': order.lines[1].id,
                    },
                ],
                'payments': [(self.bank_pm1, -210.0)],  # Refund of 210
            })

            # Step 3: Close POS session and generate GSTR1 report
            session.action_pos_session_closing_control()

            # Step 4: Create GSTR1 report and compare JSON output
            gstr1_report = self.env['l10n_in.gst.return.period'].create({
                'company_id': self.company_data["company"].id,
                'periodicity': 'monthly',
                'year': TEST_DATE.strftime('%Y'),
                'month': TEST_DATE.strftime('%m'),
            })
            gstr1_json = gstr1_report._get_gstr1_json()

            # Assert GSTR1 JSON matches the expected data
            self.assertDictEqual(gstr1_json, expected_gstr1_pos_response)

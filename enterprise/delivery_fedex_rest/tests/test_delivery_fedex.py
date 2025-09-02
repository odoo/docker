# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from contextlib import contextmanager
from unittest.mock import patch

import requests

from odoo.tests import Form, TransactionCase, tagged


@contextmanager
def _mock_request_call():
    def _mock_request(*args, **kwargs):
        url = kwargs.get('url', args[2])
        responses = {
            'token': {'access_token': 'mock_token'},
            'rate': {'output': {
                "alerts": [{"code": "string", "message": "string"}],
                'rateReplyDetails': [{
                    'ratedShipmentDetails': [{'currency': 'USD', 'totalNetChargeWithDutiesAndTaxes': 5.5}]
                }],
            }},
            'cancel': {'output': {'cancelledShipment': True}},
            'ship': {
                'output': {
                    'transactionShipments': [{
                        'completedShipmentDetail': {
                            'shipmentRating': {
                                'actualRateType': 'TEST',
                                'shipmentRateDetails': [{
                                    'rateType': 'TEST',
                                    "totalNetChargeWithDutiesAndTaxes": 5.5
                                }]
                            },
                            'completedPackageDetails': [{'trackingIds': [{'trackingNumber': 'TEST'}]}]
                        },
                        'pieceResponses': [{
                            'trackingNumber': '123',
                            'packageDocuments': [{'contentType': 'LABEL', 'encodedLabel': 'TEST'}]
                        }]
                    }]
                }
            },
        }

        for endpoint, content in responses.items():
            if endpoint in url:
                response = requests.Response()
                response.request = requests.Request(kwargs.get('method'), url, kwargs.get('headers'))
                response.request.body = str(kwargs.get('json')).encode('utf-8')
                response._content = json.dumps(content).encode()
                response.status_code = 200
                return response

        raise Exception('unhandled request url %s' % url)

    with patch.object(requests.Session, 'request', _mock_request):
        yield


@tagged('post_install', '-at_install')
class TestDeliveryFedex(TransactionCase):

    def setUp(self):
        super().setUp()

        self.iPadMini = self.env['product.product'].create({
            'name': 'Ipad Mini',
            'weight': 0.01,
        })
        self.large_desk = self.env['product.product'].create({
            'name': 'Large Desk',
            'weight': 0.01,
        })
        self.uom_unit = self.env.ref('uom.product_uom_unit')

        self.your_company = self.env.ref('base.main_partner')
        self.your_company.write({'country_id': self.env.ref('base.us').id,
                                 'state_id': self.env.ref('base.state_us_5').id,
                                 'city': 'San Francisco',
                                 'street': '51 Federal Street',
                                 'zip': '94107',
                                 'phone': 9874582356})

        self.agrolait = self.env['res.partner'].create({
            'name': 'Agrolait',
            'phone': '(603)-996-3829',
            'street': "rue des Bourlottes, 9",
            'street2': "",
            'city': "Ramillies",
            'zip': 1367,
            'state_id': False,
            'country_id': self.env.ref('base.be').id,
        })
        self.delta_pc = self.env['res.partner'].create({
            'name': 'Delta PC',
            'phone': '(803)-873-6126',
            'street': "1515 Main Street",
            'street2': "",
            'city': "Columbia",
            'zip': 29201,
            'state_id': self.env.ref('base.state_us_41').id,
            'country_id': self.env.ref('base.us').id,
        })
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.customer_location = self.env.ref('stock.stock_location_customers')

    def wiz_put_in_pack(self, picking):
        """ Helper to use the 'choose.delivery.package' wizard
        in order to call the 'action_put_in_pack' method.
        """
        wiz_action = picking.action_put_in_pack()
        self.assertEqual(wiz_action['res_model'], 'choose.delivery.package', 'Wrong wizard returned')
        wiz = Form(self.env[wiz_action['res_model']].with_context(wiz_action['context']).create({
            'delivery_package_type_id': picking.carrier_id.fedex_rest_default_package_type_id.id
        }))
        choose_delivery_carrier = wiz.save()
        choose_delivery_carrier.action_put_in_pack()

    def test_01_fedex_basic_us_domestic_flow(self):
        SaleOrder = self.env['sale.order']

        sol_vals = {'product_id': self.iPadMini.id,
                    'name': "[A1232] iPad Mini",
                    'product_uom': self.uom_unit.id,
                    'product_uom_qty': 1.0,
                    'price_unit': self.iPadMini.lst_price}

        so_vals = {'partner_id': self.delta_pc.id,
                   'order_line': [(0, None, sol_vals)]}

        sale_order = SaleOrder.create(so_vals)
        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order.id,
            'default_carrier_id': self.env.ref('delivery_fedex_rest.delivery_carrier_fedex_us').id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        with _mock_request_call():
            choose_delivery_carrier.update_price()
            self.assertGreater(choose_delivery_carrier.delivery_price, 0.0, "FedEx delivery cost for this SO has not been correctly estimated.")
            choose_delivery_carrier.button_confirm()

            sale_order.action_confirm()
            self.assertEqual(len(sale_order.picking_ids), 1, "The Sales Order did not generate a picking.")

            picking = sale_order.picking_ids[0]
            self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

            picking.move_line_ids[0].quantity = 1.0
            self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")

            picking._action_done()
            self.assertIsNot(picking.carrier_tracking_ref, False, "FedEx did not return any tracking number")
            self.assertGreater(picking.carrier_price, 0.0, "FedEx carrying price is probably incorrect")

            picking.cancel_shipment()
            self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
            self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

    def test_02_fedex_basic_international_flow(self):
        SaleOrder = self.env['sale.order']

        sol_vals = {'product_id': self.iPadMini.id,
                    'name': "[A1232] Large Cabinet",
                    'product_uom': self.uom_unit.id,
                    'product_uom_qty': 1.0,
                    'price_unit': self.iPadMini.lst_price}

        so_vals = {'partner_id': self.agrolait.id,
                   'order_line': [(0, None, sol_vals)]}

        sale_order = SaleOrder.create(so_vals)
        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order.id,
            'default_carrier_id': self.env.ref('delivery_fedex_rest.delivery_carrier_fedex_inter').id,
        }))
        choose_delivery_carrier = delivery_wizard.save()
        with _mock_request_call():
            choose_delivery_carrier.update_price()
            self.assertGreater(choose_delivery_carrier.delivery_price, 0.0, "FedEx delivery cost for this SO has not been correctly estimated.")
            choose_delivery_carrier.button_confirm()

            sale_order.action_confirm()
            self.assertEqual(len(sale_order.picking_ids), 1, "The Sales Order did not generate a picking.")

            picking = sale_order.picking_ids[0]
            self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

            picking.move_line_ids[0].quantity = 1.0
            self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")

            picking._action_done()
            self.assertIsNot(picking.carrier_tracking_ref, False, "FedEx did not return any tracking number")
            self.assertGreater(picking.carrier_price, 0.0, "FedEx carrying price is probably incorrect")

            picking.cancel_shipment()
            self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
            self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

    def test_03_fedex_multipackage_international_flow(self):
        SaleOrder = self.env['sale.order']

        sol_1_vals = {'product_id': self.iPadMini.id,
                      'name': "[A1232] iPad Mini",
                      'product_uom': self.uom_unit.id,
                      'product_uom_qty': 1.0,
                      'price_unit': self.iPadMini.lst_price}
        sol_2_vals = {'product_id': self.large_desk.id,
                      'name': "[A1090] Large Desk",
                      'product_uom': self.uom_unit.id,
                      'product_uom_qty': 1.0,
                      'price_unit': self.large_desk.lst_price}

        so_vals = {'partner_id': self.agrolait.id,
                   'order_line': [(0, None, sol_1_vals), (0, None, sol_2_vals)]}

        sale_order = SaleOrder.create(so_vals)
        # I add delivery cost in Sales order
        delivery_wizard = Form(self.env['choose.delivery.carrier'].with_context({
            'default_order_id': sale_order.id,
            'default_carrier_id': self.env.ref('delivery_fedex_rest.delivery_carrier_fedex_inter').id
        }))
        choose_delivery_carrier = delivery_wizard.save()
        with _mock_request_call():
            choose_delivery_carrier.update_price()
            self.assertGreater(choose_delivery_carrier.delivery_price, 0.0, "FedEx delivery cost for this SO has not been correctly estimated.")
            choose_delivery_carrier.button_confirm()

            sale_order.action_confirm()
            self.assertEqual(len(sale_order.picking_ids), 1, "The Sales Order did not generate a picking.")

            picking = sale_order.picking_ids[0]
            self.assertEqual(picking.carrier_id.id, sale_order.carrier_id.id, "Carrier is not the same on Picking and on SO.")

            move0 = picking.move_line_ids[0]
            move0.quantity = 1.0
            move0.picked = True
            self.wiz_put_in_pack(picking)
            move1 = picking.move_line_ids[1]
            move1.quantity = 1.0
            move1.picked = True
            self.wiz_put_in_pack(picking)
            self.assertEqual(len(picking.move_line_ids.mapped('result_package_id')), 2, "2 Packages should have been created at this point")
            self.assertGreater(picking.shipping_weight, 0.0, "Picking weight should be positive.")

            picking._action_done()
            self.assertIsNot(picking.carrier_tracking_ref, False, "FedEx did not return any tracking number")
            self.assertGreater(picking.carrier_price, 0.0, "FedEx carrying price is probably incorrect")

            picking.cancel_shipment()
            self.assertFalse(picking.carrier_tracking_ref, "Carrier Tracking code has not been properly deleted")
            self.assertEqual(picking.carrier_price, 0.0, "Carrier price has not been properly deleted")

    def test_04_fedex_international_delivery_from_delivery_order(self):
        StockPicking = self.env['stock.picking']

        order1_vals = {
                    'product_id': self.iPadMini.id,
                    'name': "[A1232] iPad Mini",
                    'product_uom': self.uom_unit.id,
                    'product_uom_qty': 1.0,
                    'location_id': self.stock_location.id,
                    'location_dest_id': self.customer_location.id}

        do_vals = {'partner_id': self.agrolait.id,
                    'carrier_id': self.env.ref('delivery_fedex_rest.delivery_carrier_fedex_inter').id,
                    'location_id': self.stock_location.id,
                    'location_dest_id': self.customer_location.id,
                    'picking_type_id': self.env.ref('stock.picking_type_out').id,
                    'state': 'draft',
                    'move_ids_without_package': [(0, None, order1_vals)]}

        delivery_order = StockPicking.create(do_vals)
        self.assertEqual(delivery_order.state, 'draft', 'Shipment state should be draft.')

        delivery_order.action_confirm()
        self.assertEqual(delivery_order.state, 'assigned', 'Shipment state should be ready(assigned).')
        delivery_order.move_ids_without_package.quantity = 1.0
        with _mock_request_call():
            delivery_order.button_validate()
            self.assertEqual(delivery_order.state, 'done', 'Shipment state should be done.')

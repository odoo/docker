from base64 import b64decode
from datetime import datetime
from freezegun import freeze_time
from lxml import etree
import pytz
from unittest import mock

from odoo.tests import tagged
from .common import TestECDeliveryGuideCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestECDeliveryGuide(TestECDeliveryGuideCommon):

    def test_send_delivery_guide_flow(self):
        ''' Test the delivery guide submission + cancellation flow. '''
        mocked_responses = iter([
            # First call: send the delivery guide
            {
                'estado': 'RECIBIDA',
                'comprobantes': None
            },
            # Second call: retrieve the status
            {
                'numeroComprobantes': '1',
                'autorizaciones': {
                    'autorizacion': [{
                        'estado': 'AUTORIZADO',
                        'numeroAutorizacion': '1912202406010364761600110010010001912253121521419',
                        'fechaAutorizacion': datetime(2024, 12, 19, 12, 5, 29, tzinfo=pytz.FixedOffset(-5 * 60)),
                        'ambiente': 'PRUEBAS',
                        'comprobante': 'dummy',
                        'mensajes': None,
                    }],
                },
            },
            # Third call: retrieve the status
            {
                'numeroComprobantes': '1',
                'autorizaciones': {
                    'autorizacion': [{
                        'estado': 'CANCELADO',
                        'mensajes': None,
                    }],
                },
            },
        ])

        def mocked_l10n_ec_get_client_service_response_new(self, company_id, mode, **kwargs):
            return next(mocked_responses), [], []

        def mocked_l10n_ec_generate_signed_xml(self, company_id, xml_node_or_string):
            return ''

        with (
            mock.patch.object(
                self.env['account.edi.format'].__class__,
                '_l10n_ec_get_client_service_response_new',
                new=mocked_l10n_ec_get_client_service_response_new,
            ),
            mock.patch.object(
                self.env['account.edi.format'].__class__,
                '_l10n_ec_generate_signed_xml',
                new=mocked_l10n_ec_generate_signed_xml,
            ),
        ):
            # Set this to True in order to mock sending invoices to SRI
            self.env.company.l10n_ec_production_env = True

            # Send the delivery guide
            stock_picking = self.get_stock_picking()
            self.prepare_delivery_guide(stock_picking)

            self.assertRecordValues(stock_picking, [{
                'l10n_ec_edi_status': 'sent',
                'l10n_ec_delivery_guide_error': False,
                'l10n_ec_authorization_date': datetime(2024, 12, 19, 12, 5, 29),
            }])

            # Cancel the delivery guide
            stock_picking.button_action_cancel_delivery_guide()
            stock_picking.l10n_ec_send_delivery_guide_to_cancel()
            self.assertRecordValues(stock_picking, [{
                'l10n_ec_edi_status': 'cancelled',
                'l10n_ec_delivery_guide_error': False,
                'l10n_ec_authorization_date': False,
            }])

        # Check that all calls to `_l10n_ec_get_client_service_response` were made.
        self.assertEqual(next(mocked_responses, None), None, 'Fewer calls than expected were made to _l10n_ec_get_client_service_response!')

    def test_xml_tree_delivery_guide_basic(self):
        '''
        Validates the XML content of a delivery guide
        '''
        with freeze_time(self.frozen_today):
            stock_picking = self.get_stock_picking()
            self.prepare_delivery_guide(stock_picking)
            attachment_id = self.env['ir.attachment'].search([
                ('res_model', '=', 'stock.picking'),
                ('res_id', '=', stock_picking.id),
            ])
            decoded_content = b64decode(attachment_id.datas).decode('utf-8')
            self.assertXmlTreeEqual(
                etree.fromstring(decoded_content),
                etree.fromstring(L10N_EC_EDI_XML_DELIVERY_GUIDE),
            )


L10N_EC_EDI_XML_DELIVERY_GUIDE = """<autorizacion>
    <estado>AUTORIZADO</estado>
    <numeroAutorizacion>2501202206179236683600110010010000000013121521412</numeroAutorizacion>
    <fechaAutorizacion>2022-01-24 00:00:00</fechaAutorizacion>
    <ambiente>PRUEBAS</ambiente>
    <comprobante>
        <guiaRemision id="comprobante" version="1.1.0">
            <infoTributaria>
                <ambiente>1</ambiente>
                <tipoEmision>1</tipoEmision>
                <razonSocial>EC Test Company (official)</razonSocial>
                <nombreComercial>EC Test Company</nombreComercial>
                <ruc>1792366836001</ruc>
                <claveAcceso>2501202206179236683600110010010000000013121521412</claveAcceso>
                <codDoc>06</codDoc>
                <estab>001</estab>
                <ptoEmi>001</ptoEmi>
                <secuencial>000000001</secuencial>
                <dirMatriz>Avenida Machala 42</dirMatriz>
            </infoTributaria>
            <infoGuiaRemision>
                <dirEstablecimiento>Avenida Machala 42</dirEstablecimiento>
                <dirPartida>Avenida Machala 42</dirPartida>
                <razonSocialTransportista>Delivery guide Carrier EC</razonSocialTransportista>
                <tipoIdentificacionTransportista>05</tipoIdentificacionTransportista>
                <rucTransportista>0750032310</rucTransportista>
                <obligadoContabilidad>SI</obligadoContabilidad>
                <fechaIniTransporte>25/01/2022</fechaIniTransporte>
                <fechaFinTransporte>09/02/2022</fechaFinTransporte>
                <placa>OBA1413</placa>
            </infoGuiaRemision>
            <destinatarios>
                <destinatario>
                    <identificacionDestinatario>0453661050152</identificacionDestinatario>
                    <razonSocialDestinatario>EC Test Partner AàÁ³$£€èêÈÊöÔÇç¡⅛&amp;@™</razonSocialDestinatario>
                    <dirDestinatario>Av. Libertador Simón Bolívar 1155 -  - Quito - Ecuador</dirDestinatario>
                    <motivoTraslado>Goods Dispatch</motivoTraslado>
                    <detalles>
                        <detalle>
                            <descripcion>Computadora</descripcion>
                            <cantidad>1.0</cantidad>
                        </detalle>
                    </detalles>
                </destinatario>
            </destinatarios>
        </guiaRemision>
    </comprobante>
</autorizacion>
""".encode()

from freezegun import freeze_time

import random
import requests
from base64 import b64encode
from contextlib import contextmanager
from datetime import datetime, date
from unittest.mock import Mock, patch
import uuid

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools import file_open
from odoo.addons.l10n_co_edi.models.res_partner import FINAL_CONSUMER_VAT


class TestCoDianCommon(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('co')
    def setUpClass(cls):
        super().setUpClass()

        cls.frozen_today = datetime(year=2024, month=1, day=30)
        cls.document_path = 'odoo.addons.l10n_co_dian.models.l10n_co_dian_document.L10nCoDianDocument'
        cls.utils_path = 'odoo.addons.l10n_co_dian.xml_utils'

        with freeze_time(cls.frozen_today):
            cls.key_demo = cls.env["certificate.key"].create({
                "name": "Test DIAN Key",
                "content": b64encode(cls._read_file('l10n_co_dian/demo/demo_key.pem', 'rb')),
                "company_id": cls.company_data['company'].id,
            })
            cls.certificate_demo = cls.env["certificate.certificate"].create({
                "name": "Test DIAN certificate",
                "content": b64encode(cls._read_file('l10n_co_dian/demo/demo_cert.crt', 'rb')),
                "private_key_id": cls.key_demo.id,
                "company_id": cls.company_data['company'].id,
            })

        city_bogota = cls.env.ref('l10n_co_edi.city_co_150')
        cls.company_data['company'].write({
            'name': "CO Company Test",
            'vat': "1018419008-5",
            'zip': "110110",
            'street': "CL 12A",
            'city': city_bogota.name,
            'state_id': city_bogota.state_id.id,
            'l10n_co_edi_header_actividad_economica': '0114',
            'l10n_co_dian_operation_mode_ids': [
                Command.create({
                    'dian_software_operation_mode': 'invoice',
                    'dian_software_id': 'Odoo',
                    'dian_software_security_code': '12345',
                    'dian_testing_id': 'test_id',
                    'company_id': cls.company_data['company'].id,
                }),
                Command.create({
                    'dian_software_operation_mode': 'bill',
                    'dian_software_id': 'Odoo',
                    'dian_software_security_code': '12345',
                    'dian_testing_id': 'test_id',
                    'company_id': cls.company_data['company'].id,
                }),
            ],
            'l10n_co_dian_certificate_ids': [Command.set(cls.certificate_demo.ids)],
            'l10n_co_dian_test_environment': True,
            'l10n_co_dian_provider': 'dian',
        })
        cls.company_data['company'].partner_id.write({
            'city_id': city_bogota.id,
            'l10n_co_edi_obligation_type_ids': [Command.set(cls.env.ref('l10n_co_edi.obligation_type_1').ids)],
            'l10n_latam_identification_type_id': cls.env.ref('l10n_co.rut').id,
        })

        # Journals
        dian_vals = {
            'l10n_co_edi_dian_authorization_number': "18760000001",
            'l10n_co_edi_dian_authorization_date': date(2020, 1, 19),
            'l10n_co_edi_dian_authorization_end_date': date(2030, 1, 19),
            'l10n_co_edi_min_range_number': "990000000",
            'l10n_co_edi_max_range_number': "995000000",
            'l10n_co_dian_technical_key': "dummy_journal_technical_key",
        }
        cls.company_data['default_journal_sale'].write({
            'code': 'SETP',
            **dian_vals,
        })
        cls.debit_note_journal = cls.env['account.journal'].create({
            'name': "DIAN Debit Note",
            'l10n_co_edi_debit_note': True,
            'code': "DN",
            'type': "sale",
            **dian_vals,
        })
        cls.support_document_journal = cls.env['account.journal'].create({
            'name': "DIAN Support Document",
            'l10n_co_edi_is_support_document': True,
            'code': "DS",
            'type': "purchase",
            **dian_vals,
        })

        # Partners
        cls.partner_co = cls.env['res.partner'].create({
            'name': "ADQUIRIENTE DE EJEMPLO",
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
            'street': "CARRERA 8 No 20-14/40",
            'city': city_bogota.name,
            'city_id': city_bogota.id,
            'state_id': city_bogota.state_id.id,
            'zip': "110110",
            'country_id': cls.env.ref('base.co').id,
            'vat': "900108281",
            'bank_ids': [Command.create({'acc_number': "0123456789"})],
            'l10n_co_edi_obligation_type_ids': cls.env.ref('l10n_co_edi.obligation_type_1'),
            'l10n_latam_identification_type_id': cls.env.ref('l10n_co.rut').id,
        })
        cls.final_consumer = cls.env['res.partner'].create({
            'name': "consumidor o usuario final",
            'country_id': cls.env.ref('base.co').id,
            'l10n_latam_identification_type_id': cls.env.ref('l10n_co.national_citizen_id').id,
            'vat': FINAL_CONSUMER_VAT,
            'l10n_co_edi_obligation_type_ids': cls.env.ref('l10n_co_edi.obligation_type_5'),
            'l10n_co_edi_fiscal_regimen': '49',
        })

        # Taxes
        cls.tax_iva_5 = cls.env["account.chart.template"].ref('l10n_co_tax_0')
        cls.tax_iva_19 = cls.env["account.chart.template"].ref('l10n_co_tax_8')
        cls.tax_ret_ica_1_104 = cls.env["account.chart.template"].ref('l10n_co_tax_45')
        cls.tax_ret_ica_0414 = cls.env["account.chart.template"].ref('l10n_co_tax_57')
        cls.tax_ret_iva_2_85 = cls.env["account.chart.template"].ref('l10n_co_tax_12')

        # Other
        cls.product_a.barcode = "562438192"
        cls.product_b.default_code = "prod_b"
        cls.env.ref('uom.product_uom_dozen').l10n_co_edi_ubl = "DPC"

    @classmethod
    def _create_move(cls, **kwargs):
        with freeze_time(cls.frozen_today):
            invoice = cls.env['account.move'].create({
                'partner_id': cls.partner_co.id,
                'move_type': 'out_invoice',
                'journal_id': cls.company_data['default_journal_sale'].id,
                'invoice_line_ids': [
                    Command.create({'product_id': cls.product_a.id, 'tax_ids': [Command.set(cls.tax_iva_5.ids)]}),
                ],
                **kwargs,
            })
            invoice.action_post()
            return invoice

    @classmethod
    def _create_product(cls, **kwargs):
        return cls.env['product.product'].create({
            'name': 'Product',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            **kwargs,
        })

    def _assert_document_dian(self, xml, file):
        expected_dian = self._read_file(file, 'rb')
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(xml),
            self.get_xml_tree_from_string(expected_dian),
        )

    @classmethod
    def _read_file(cls, path, *args):
        with file_open(path, *args) as f:
            content = f.read()
        return content

    @contextmanager
    def _mock_uuid_generation(self):
        rnd = random.Random(42)
        with patch(f'{self.utils_path}._uuid1', lambda: uuid.UUID(int=rnd.getrandbits(128))):
            yield

    def _mocked_request(self, response_file, status_code):
        mock_response = Mock(spec=requests.Response)
        mock_response.status_code = status_code
        mock_response.text = self._read_file(f'l10n_co_dian/tests/responses/{response_file}')
        return mock_response

    def _mocked_response(self, response_file, status_code):
        return {
            'response': self._read_file(f'l10n_co_dian/tests/responses/{response_file}'),
            'status_code': status_code,
        }

    def _mock_get_status(self):
        return patch(f'{self.document_path}._get_status', return_value=self._mocked_response('GetStatus_invoice.xml', 200))

    def _mock_send_and_print(self, move, response_file, response_code=200):
        with (
            self._mock_get_status(),
            patch(f'{self.utils_path}._build_and_send_request', return_value=self._mocked_response(response_file, response_code)),
        ):
            self.env['account.move.send.wizard'] \
                .with_context(active_model=move._name, active_ids=move.ids) \
                .create({}) \
                .action_send_and_print()

    def _mock_get_status_zip(self, move, response_file, response_code=200):
        with patch.object(requests, 'post', return_value=self._mocked_request(response_file, response_code)):
            move.l10n_co_dian_document_ids._get_status_zip()

    def _mock_button_l10n_co_dian_fetch_numbering_range(self, journal, response_file, response_code=200):
        with patch.object(requests, 'post', return_value=self._mocked_request(response_file, response_code)):
            return journal.button_l10n_co_dian_fetch_numbering_range()

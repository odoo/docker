from lxml import etree
from pytz import timezone

from collections import defaultdict
from datetime import timedelta
import re
from hashlib import sha384

from odoo import models, fields, _
from odoo.addons.l10n_co_dian import xml_utils
from odoo.tools import cleanup_xml_node, float_repr
from odoo.addons.l10n_co_edi.models.res_partner import FINAL_CONSUMER_VAT
from odoo.addons.l10n_co_edi.models.account_invoice import L10N_CO_EDI_TYPE

COUNTRIES_ES = {
    "AF": "Afganistán",
    "AX": "Åland",
    "AL": "Albania",
    "DE": "Alemania",
    "AD": "Andorra",
    "AO": "Angola",
    "AI": "Anguila",
    "AQ": "Antártida",
    "AG": "Antigua y Barbuda",
    "SA": "Arabia Saudita",
    "DZ": "Argelia",
    "AR": "Argentina",
    "AM": "Armenia",
    "AW": "Aruba",
    "AU": "Australia",
    "AT": "Austria",
    "AZ": "Azerbaiyán",
    "BS": "Bahamas",
    "BD": "Bangladés",
    "BB": "Barbados",
    "BH": "Baréin",
    "BE": "Bélgica",
    "BZ": "Belice",
    "BJ": "Benín",
    "BM": "Bermudas",
    "BY": "Bielorrusia",
    "BO": "Bolivia",
    "BQ": "Bonaire, San Eustaquio y Saba",
    "BA": "Bosnia y Herzegovina",
    "BW": "Botsuana",
    "BR": "Brasil",
    "BN": "Brunéi",
    "BG": "Bulgaria",
    "BF": "Burkina Faso",
    "BI": "Burundi",
    "BT": "Bután",
    "CV": "Cabo Verde",
    "KH": "Camboya",
    "CM": "Camerún",
    "CA": "Canadá",
    "QA": "Catar",
    "TD": "Chad",
    "CL": "Chile",
    "CN": "China",
    "CY": "Chipre",
    "CO": "Colombia",
    "KM": "Comoras",
    "KP": "Corea del Norte",
    "KR": "Corea del Sur",
    "CI": "Costa de Marfil",
    "CR": "Costa Rica",
    "HR": "Croacia",
    "CU": "Cuba",
    "CW": "Curazao",
    "DK": "Dinamarca",
    "DM": "Dominica",
    "EC": "Ecuador",
    "EG": "Egipto",
    "SV": "El Salvador",
    "AE": "Emiratos Árabes Unidos",
    "ER": "Eritrea",
    "SK": "Eslovaquia",
    "SI": "Eslovenia",
    "ES": "España",
    "US": "Estados Unidos",
    "EE": "Estonia",
    "ET": "Etiopía",
    "PH": "Filipinas",
    "FI": "Finlandia",
    "FJ": "Fiyi",
    "FR": "Francia",
    "GA": "Gabón",
    "GM": "Gambia",
    "GE": "Georgia",
    "GH": "Ghana",
    "GI": "Gibraltar",
    "GD": "Granada",
    "GR": "Grecia",
    "GL": "Groenlandia",
    "GP": "Guadalupe",
    "GU": "Guam",
    "GT": "Guatemala",
    "GF": "Guayana Francesa",
    "GG": "Guernsey",
    "GN": "Guinea",
    "GW": "Guinea-Bisáu",
    "GQ": "Guinea Ecuatorial",
    "GY": "Guyana",
    "HT": "Haití",
    "HN": "Honduras",
    "HK": "Hong Kong",
    "HU": "Hungría",
    "IN": "India",
    "ID": "Indonesia",
    "IQ": "Irak",
    "IR": "Irán",
    "IE": "Irlanda",
    "BV": "Isla Bouvet",
    "IM": "Isla de Man",
    "CX": "Isla de Navidad",
    "IS": "Islandia",
    "KY": "Islas Caimán",
    "CC": "Islas Cocos",
    "CK": "Islas Cook",
    "FO": "Islas Feroe",
    "GS": "Islas Georgias del Sur y Sandwich del Sur",
    "HM": "Islas Heard y McDonald",
    "FK": "Islas Malvinas",
    "MP": "Islas Marianas del Norte",
    "MH": "Islas Marshall",
    "PN": "Islas Pitcairn",
    "SB": "Islas Salomón",
    "TC": "Islas Turcas y Caicos",
    "UM": "Islas ultramarinas de Estados Unidos",
    "VG": "Islas Vírgenes Británicas",
    "VI": "Islas Vírgenes de los Estados Unidos",
    "IL": "Israel",
    "IT": "Italia",
    "JM": "Jamaica",
    "JP": "Japón",
    "JE": "Jersey",
    "JO": "Jordania",
    "KZ": "Kazajistán",
    "KE": "Kenia",
    "KG": "Kirguistán",
    "KI": "Kiribati",
    "XK": "Kosovo",
    "KW": "Kuwait",
    "LA": "Laos",
    "LS": "Lesoto",
    "LV": "Letonia",
    "LB": "Líbano",
    "LR": "Liberia",
    "LY": "Libia",
    "LI": "Liechtenstein",
    "LT": "Lituania",
    "LU": "Luxemburgo",
    "MO": "Macao",
    "MK": "Macedonia",
    "MG": "Madagascar",
    "MY": "Malasia",
    "MW": "Malaui",
    "MV": "Maldivas",
    "ML": "Malí",
    "MT": "Malta",
    "MA": "Marruecos",
    "MQ": "Martinica",
    "MU": "Mauricio",
    "MR": "Mauritania",
    "YT": "Mayotte",
    "MX": "México",
    "FM": "Micronesia",
    "MD": "Moldavia",
    "MC": "Mónaco",
    "MN": "Mongolia",
    "ME": "Montenegro",
    "MS": "Montserrat",
    "MZ": "Mozambique",
    "MM": "Myanmar",
    "NA": "Namibia",
    "NR": "Nauru",
    "NP": "Nepal",
    "NI": "Nicaragua",
    "NE": "Níger",
    "NG": "Nigeria",
    "NU": "Niue",
    "NF": "Norfolk",
    "NO": "Noruega",
    "NC": "Nueva Caledonia",
    "NZ": "Nueva Zelanda",
    "OM": "Omán",
    "NL": "Países Bajos",
    "PK": "Pakistán",
    "PW": "Palaos",
    "PS": "Palestina",
    "PA": "Panamá",
    "PG": "Papúa Nueva Guinea",
    "PY": "Paraguay",
    "PE": "Perú",
    "PF": "Polinesia Francesa",
    "PL": "Polonia",
    "PT": "Portugal",
    "PR": "Puerto Rico",
    "GB": "Reino Unido",
    "EH": "República Árabe Saharaui Democrática",
    "CF": "República Centroafricana",
    "CZ": "República Checa",
    "CG": "República del Congo",
    "CD": "República Democrática del Congo",
    "DO": "República Dominicana",
    "RE": "Reunión",
    "RW": "Ruanda",
    "RO": "Rumania",
    "RU": "Rusia",
    "WS": "Samoa",
    "AS": "Samoa Americana",
    "BL": "San Bartolomé",
    "KN": "San Cristóbal y Nieves",
    "SM": "San Marino",
    "MF": "San Martín",
    "PM": "San Pedro y Miquelón",
    "VC": "San Vicente y las Granadinas",
    "SH": "Santa Elena, Ascensión y Tristán de Acuña",
    "LC": "Santa Lucía",
    "ST": "Santo Tomé y Príncipe",
    "SN": "Senegal",
    "RS": "Serbia",
    "SC": "Seychelles",
    "SL": "Sierra Leona",
    "SG": "Singapur",
    "SX": "Sint Maarten",
    "SY": "Siria",
    "SO": "Somalia",
    "LK": "Sri Lanka",
    "SZ": "Suazilandia",
    "ZA": "Sudáfrica",
    "SD": "Sudán",
    "SS": "Sudán del Sur",
    "SE": "Suecia",
    "CH": "Suiza",
    "SR": "Surinam",
    "SJ": "Svalbard y Jan Mayen",
    "TH": "Tailandia",
    "TW": "Taiwán (República de China)",
    "TZ": "Tanzania",
    "TJ": "Tayikistán",
    "IO": "Territorio Británico del Océano Índico",
    "TF": "Tierras Australes y Antárticas Francesas",
    "TL": "Timor Oriental",
    "TG": "Togo",
    "TK": "Tokelau",
    "TO": "Tonga",
    "TT": "Trinidad y Tobago",
    "TN": "Túnez",
    "TM": "Turkmenistán",
    "TR": "Turquía",
    "TV": "Tuvalu",
    "UA": "Ucrania",
    "UG": "Uganda",
    "UY": "Uruguay",
    "UZ": "Uzbekistán",
    "VU": "Vanuatu",
    "VA": "Vaticano, Ciudad del",
    "VE": "Venezuela",
    "VN": "Vietnam",
    "WF": "Wallis y Futuna",
    "YE": "Yemen",
    "DJ": "Yibuti",
    "ZM": "Zambia",
    "ZW": "Zimbabue",
}


class AccountEdiXmlUBLDian(models.AbstractModel):
    """ The technical documentation is available on the dian.gov.co website. Latest version is 1.9:
    https://www.dian.gov.co/impuestos/factura-electronica/Documents/Anexo-Tecnico-Factura-Electronica-de-Venta-vr-1-9.pdf
    """
    _name = 'account.edi.xml.ubl_dian'
    _inherit = 'account.edi.xml.ubl_21'
    _description = "UBL DIAN"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        # OVERRIDE account.edi.xml.ubl_21
        return 'dian_%s.xml' % (re.sub(r'[\W_]', '', invoice.name))

    def _get_partner_address_vals(self, partner):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_partner_address_vals(partner)
        vals.pop('street_name', None)
        vals.update({
            'id': str(partner.city_id.l10n_co_edi_code).zfill(5),  # Codigo Municipio
            'address_lines': [partner._l10n_co_edi_get_company_address()],
            'country_subentity_code': str(partner.state_id.l10n_co_edi_code).zfill(2),
        })
        vals['country_vals']['name_attrs'] = {
            'languageID': 'es' if partner.country_code == 'CO' else 'en',
        }
        return vals

    def _get_partner_party_tax_scheme_vals_list(self, partner, role):
        # EXTENDS account.edi.xml.ubl_20
        vals_list = super()._get_partner_party_tax_scheme_vals_list(partner, role)
        for vals in vals_list:
            vals['company_id'] = partner._get_vat_without_verification_code()
            scheme_name = partner._l10n_co_edi_get_carvajal_code_for_identification_type()
            vals['company_id_attrs'] = {
                'schemeName': scheme_name,
                'schemeAgencyName': "CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)",
                'schemeAgencyID': "195",
                'schemeID': partner._get_vat_verification_code() if scheme_name == '31' else False,
            }
            vals['tax_level_code'] = ';'.join(partner.l10n_co_edi_obligation_type_ids.mapped('name'))
            name = partner._l10n_co_edi_get_fiscal_regimen_name()
            vals['tax_scheme_vals'].update({
                'id': partner._l10n_co_edi_get_fiscal_regimen_code(),
                'name': 'No aplica' if name == 'No Aplica' else name,
            })
            vals['registration_address_vals']['id'] = str(partner.city_id.l10n_co_edi_code).zfill(5)
            if partner.vat == FINAL_CONSUMER_VAT:
                # 'Consumidor Final' is used in B2C, hence no address should be filled
                vals.pop('registration_address_vals')
        return vals_list

    def _get_partner_party_identification_vals_list(self, partner):
        # EXTENDS account.edi.xml.ubl_20
        vals = super()._get_partner_party_identification_vals_list(partner)
        if not partner.is_company:
            partner_code = partner._l10n_co_edi_get_carvajal_code_for_identification_type()
            vals.append({
                'id_attrs': {
                    'schemeName': partner_code,
                    # every Colombian NIT (code='rut') comprises a validation digit, it is mandatory to add it here
                    'schemeID': partner._get_vat_verification_code() if partner_code == '31' else False,
                },
                'id': partner._get_vat_without_verification_code(),
            })
        return vals

    def _get_partner_contact_vals(self, partner):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._get_partner_contact_vals(partner)
        vals.pop('id')
        return vals

    def _get_partner_party_vals(self, partner, role):
        # EXTENDS account.edi.xml.ubl_20
        vals = super()._get_partner_party_vals(partner, role)
        vals['physical_location_vals'] = {'address_vals': vals.pop('postal_address_vals')}
        vals['physical_location_vals']['address_vals']['country_vals']['name'] = COUNTRIES_ES.get(partner.country_code)
        if partner.vat == FINAL_CONSUMER_VAT:
            vals.pop('physical_location_vals')
            vals.pop('party_legal_entity_vals')
            vals.pop('contact_vals')
        return vals

    def _get_partner_party_legal_entity_vals_list(self, partner):
        # EXTENDS account.edi.xml.ubl_20
        vals_list = super()._get_partner_party_legal_entity_vals_list(partner)
        for vals in vals_list:
            vals['company_id'] = partner._get_vat_without_verification_code()
            vals['company_id_attrs'] = {
                'schemeName': partner._l10n_co_edi_get_carvajal_code_for_identification_type(),
                'schemeAgencyName': "CO, DIAN (Dirección de Impuestos y Aduanas Nacionales)",
                'schemeAgencyID': "195",
                'schemeID': partner._get_vat_verification_code(),
            }
            vals.pop('registration_address_vals')
        return vals_list

    def _get_invoice_monetary_total_vals(self, invoice, taxes_vals, line_extension_amount, allowance_total_amount, charge_total_amount):
        """ The validator will check that:
        * LineExtensionAmount = sum(InvoiceLine/LineExtensionAmount)
        * TaxExclusiveAmount = sum(InvoiceLine/TaxTotal/TaxSubtotal/TaxableAmount)
        * TaxInclusiveAmount = LineExtensionAmount + sum(Invoice/TaxTotal/TaxAmount)
        * ChargeTotalAmount = sum(Invoice/AllowanceCharge[ChargeIndicator='true'] [1]
        * AllowanceTotalAmount = sum(Invoice/AllowanceCharge[ChargeIndicator='false'] [1]
        * PrepaidAmount = sum(Invoice/PrepaidPayment/PaidAmount)
        * PayableAmount = TaxInclusiveAmount - AllowanceTotalAmount + ChargeTotalAmount [2]

        [1]: Will always be 0
        [2]: PrepaidAmount is not used in the PayableAmount
        [3]: Withholdings have no impact in any of these subtotals, they are optionals
        """
        # EXTENDS account.edi.xml.ubl_20
        vals = super()._get_invoice_monetary_total_vals(
            invoice,
            taxes_vals,
            line_extension_amount,
            allowance_total_amount,
            charge_total_amount,
        )
        sign = -invoice.direction_sign
        withholding_amount = sum(
            details['tax_amount']
            for key, details in taxes_vals['tax_details'].items()
            if key['tax_co_ret']
        )
        prepayments = invoice._l10n_co_dian_get_invoice_prepayments()
        prepaid_amount = sum(p['amount'] for p in prepayments)
        vals.update({
            'currency': invoice.company_id.currency_id,
            'currency_dp': self._get_currency_decimal_places(invoice.company_id.currency_id),
            'tax_exclusive_amount': taxes_vals['base_amount'],
            'tax_inclusive_amount': sign * invoice.amount_total_signed - withholding_amount,
            'prepaid_amount': prepaid_amount or None,
            'payable_amount': sign * invoice.amount_total_signed - withholding_amount,
        })
        return vals

    def _get_tax_category_list(self, customer, supplier, taxes):
        # OVERRIDE account.edi.xml.ubl_20
        res = []
        for tax in taxes:
            res.append({
                'percent': float_repr(tax.amount, 3),
                'tax_scheme_vals': {
                    'id': tax.l10n_co_edi_type.code,
                    'name': 'No aplica' if tax.l10n_co_edi_type.name == 'No Aplica' else tax.l10n_co_edi_type.name,
                },
            })
        return res

    def _get_tax_grouping_key(self, base_line, tax_data):
        """ Group the taxes by colombian type using the (tax.amount, tax.amount_type, tax.l10n_co_edi_type) """
        # OVERRIDE account.edi.xml.ubl_20
        customer = base_line['record'].move_id.commercial_partner_id
        supplier = base_line['record'].move_id.company_id.partner_id.commercial_partner_id
        tax = tax_data['tax']
        code_to_filter = ['07', 'ZZ'] if base_line['record'].move_id.move_type in ('in_invoice', 'in_refund') else ['ZZ']
        return {
            'tax_co_type': tax.l10n_co_edi_type.code,
            'tax_co_ret': tax.l10n_co_edi_type.retention or tax.l10n_co_edi_type.code in code_to_filter,
            'tax_amount_type': tax.amount_type,
            '_tax_category_vals_': self._get_tax_category_list(customer, supplier, tax)[0],  # used to render the TaxCategory nodes
        }

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        # OVERRIDE account.edi.xml.ubl_21
        return self._dian_tax_totals(invoice, taxes_vals, withholding=False)

    def _get_invoice_line_item_vals(self, line, taxes_vals):
        # EXTENDS account.edi.xml.ubl_20
        vals = super()._get_invoice_line_item_vals(line, taxes_vals)
        value, scheme_id, scheme_name = line._l10n_co_edi_get_product_code()
        vals['standard_item_identification_vals'] = {
            'id': value,
            'id_attrs': {'schemeID': scheme_id, 'schemeName': scheme_name or False},
        }
        if line.move_id.l10n_co_edi_is_support_document:
            vals['sellers_item_identification_vals'] = {
                'id': value,
                'extended_id': value,
            }
        vals['classified_tax_category_vals'] = []
        if line.move_id.l10n_co_edi_type == L10N_CO_EDI_TYPE['Export Invoice']:
            vals.update({
                'brand_name': line.product_id.l10n_co_edi_brand,
                'model_name': line.product_id.l10n_co_edi_customs_code,
            })
        return vals

    def _get_invoice_line_allowance_vals_list(self, line, tax_values_list):
        # OVERRIDE account.edi.xml.ubl_20
        currency = line.company_id.currency_id
        if line.discount:
            gross_price_subtotal = line._l10n_co_dian_gross_price_subtotal()
            return [{
                'currency_name': currency.name,
                'currency_dp': self._get_currency_decimal_places(currency),
                'charge_indicator': 'false',
                'allowance_charge_reason_code': '00',  # unconditional discount
                'amount': gross_price_subtotal - line._l10n_co_dian_net_price_subtotal(),
                'base_amount': gross_price_subtotal,
                'multiplier_factor': line.discount,
            }]
        return []

    def _get_invoice_line_price_vals(self, line):
        # EXTENDS account.edi.xml.ubl_20
        invoice_line_vals = super()._get_invoice_line_price_vals(line)
        currency = line.company_id.currency_id
        invoice_line_vals.update({
            'currency': currency,
            'currency_dp': self._get_currency_decimal_places(currency),
            'price_amount': line._l10n_co_dian_gross_price_subtotal() / line.quantity if line.quantity else 0.0,
            'base_quantity': line.quantity,
        })
        invoice_line_vals['base_quantity_attrs']['unitCode'] = self._dian_uom_code(line)
        return invoice_line_vals

    def _get_invoice_line_vals(self, line, line_id, taxes_vals):
        # EXTENDS account.edi.xml.ubl_20
        vals = super()._get_invoice_line_vals(line, line_id, taxes_vals)
        uom_code = self._dian_uom_code(line)
        currency = line.company_id.currency_id
        vals.update({
            'currency': currency,
            'currency_dp': self._get_currency_decimal_places(currency),
            'line_extension_amount': line._l10n_co_dian_net_price_subtotal(),
            'withholding_tax_total_vals_list': self._dian_tax_totals(line.move_id, taxes_vals, withholding=True),
            'line_quantity_attrs': {'unitCode': uom_code},
        })
        if line.move_id.l10n_co_edi_is_support_document:
            vals['invoice_period_vals_list'] = [{
                'start_date': line.move_id.invoice_date,
                'description_code': "1",
                'description': "Por operación",
            }]
        vals['price_vals']['base_quantity_attrs']['unitCode'] = uom_code
        return vals

    def _get_delivery_vals_list(self, invoice):
        # OVERRIDE account.edi.xml.ubl_20
        return []

    def _get_invoice_payment_exchange_rate_vals(self, invoice):
        if invoice.currency_id.name != "COP":
            rate = invoice.amount_total_signed / (invoice.amount_total or 1)
            return {
                'source_currency_code': "COP",
                'source_currency_base_rate': self.format_float(rate, 6),  # 6 decimals are allowed
                'target_currency_code': invoice.currency_id.name,
                'target_currency_base_rate': "1.00",
                'calculation_rate': self.format_float(rate, 6),  # 6 decimals are allowed
                'date': invoice.invoice_date,
            }
        return {}

    def _get_invoice_payment_means_vals_list(self, invoice):
        # OVERRIDE account.edi.xml.ubl_20
        return [{
            'id': '1' if invoice.l10n_co_edi_is_direct_payment else '2',
            'payment_means_code': invoice.l10n_co_edi_payment_option_id.code,
            'payment_due_date': invoice.invoice_date_due,
            'payment_id_vals': [invoice.payment_reference or invoice.name],
        }]

    def _get_invoice_period_vals_list(self, invoice):
        # EXTENDS account.edi.xml.ubl_20
        vals_list = super()._get_invoice_period_vals_list(invoice)
        if invoice.l10n_co_edi_operation_type in ['22', '32']:  # 22: Nota Crédito sin referencia a facturas, 32: Nota Débito sin referencia a facturas
            vals_list.append({
                'start_date': invoice.invoice_date,
                'end_date': invoice.invoice_date,
            })
        return vals_list

    def _get_sts_namespace(self, invoice):
        if invoice.l10n_co_edi_debit_note or invoice.move_type == 'out_refund':
            return "http://www.dian.gov.co/contratos/facturaelectronica/v1/Structures"
        else:
            return "dian:gov:co:facturaelectronica:Structures-2-1"

    def _export_invoice_vals(self, invoice):
        # EXTENDS account.edi.xml.ubl_21
        vals = super()._export_invoice_vals(invoice)

        vals['vals']['accounting_supplier_party_vals']['party_vals']['industry_classification_code'] = \
            invoice.company_id.l10n_co_edi_header_actividad_economica
        if invoice.l10n_co_dian_identifier_type == 'cude':
            algorithm = "CUDE-SHA384"
        elif invoice.l10n_co_dian_identifier_type == 'cuds':
            algorithm = "CUDS-SHA384"
            # Switch the party roles
            vals['supplier'], vals['customer'] = vals['customer'], vals['supplier']
            vals['vals'].update({
                'accounting_supplier_party_vals': {
                    'party_vals': self._get_partner_party_vals(vals['supplier'], role='supplier'),
                },
                'accounting_customer_party_vals': {
                    'party_vals': self._get_partner_party_vals(vals['customer'], role='customer'),
                },
            })
        else:
            algorithm = "CUFE-SHA384"

        vals['sts_namespace'] = self._get_sts_namespace(invoice)
        vals['vals'].update({
            'customization_id': self._dian_get_customization_id(invoice),
            'ubl_version_id': 'UBL 2.1',
            'profile_execution_id': '2' if invoice.company_id.l10n_co_dian_test_environment else '1',
            'profile_id': invoice._l10n_co_edi_get_electronic_invoice_type_info(),
            'id': invoice.name,
            'uuid_attrs': {
                'schemeID': '2' if invoice.company_id.l10n_co_dian_test_environment else '1',
                'schemeName': algorithm,
            },
            'issue_date': invoice.l10n_co_dian_post_time.date().isoformat(),
            'issue_time': invoice.l10n_co_dian_post_time.strftime("%H:%M:%S-05:00"),
            'document_type_code': self._dian_get_document_type_code(invoice),
            'document_currency_code': "COP",
            'document_currency_code_attrs': {
                'listAgencyID': "6",
                'listAgencyName': "United Nations Economic Commission for Europe",
                'listID': "ISO 4217 Alpha"
            },
            'line_count_numeric': len(vals['vals']['line_vals']),
            'sales_order_id': False,
            'payment_exchange_rate_vals': self._get_invoice_payment_exchange_rate_vals(invoice),
            'withholding_tax_total_vals_list': self._dian_tax_totals(invoice, vals['taxes_vals'], withholding=True),
        })

        if invoice.l10n_co_edi_operation_type == '20' or invoice.move_type == 'in_refund':
            # Credit note or Credit note Support Document with a referenced invoice
            reversed_move = invoice.reversed_entry_id
            vals['vals']['discrepancy_response_vals'] = [{
                'reference_id': reversed_move.name,
                'response_code': invoice.l10n_co_edi_description_code_credit,
                'description': dict(invoice._fields['l10n_co_edi_description_code_credit'].selection).get(invoice.l10n_co_edi_description_code_credit),
            }]
            vals['vals']['billing_reference_vals'] = {
                'id': reversed_move.name,
                'uuid': reversed_move.l10n_co_edi_cufe_cude_ref,
                'uuid_attrs': {"schemeName": ("CUDS" if invoice.move_type == 'in_refund' else "CUFE") + "-SHA384"},
                'issue_date': reversed_move.invoice_date.isoformat(),
            }

        if invoice.l10n_co_edi_operation_type == '30':
            # Debit note with a referenced invoice
            original_invoice = invoice.debit_origin_id
            vals['vals']['discrepancy_response_vals'] = [{
                'reference_id': original_invoice.name,
                'response_code': invoice.l10n_co_edi_description_code_debit,
                'description': dict(invoice._fields['l10n_co_edi_description_code_debit'].selection).get(invoice.l10n_co_edi_description_code_debit),
            }]
            vals['vals']['billing_reference_vals'] = {
                'id': original_invoice.name,
                'uuid': original_invoice.l10n_co_edi_cufe_cude_ref,
                'uuid_attrs': {"schemeName": "CUFE-SHA384"},
                'issue_date': original_invoice.invoice_date.isoformat(),
            }

        vals['vals']['prepaid_payments'] = [
            {
                'id': p['name'],
                'paid_amount': p['amount'],
                'received_date': p['date'],
                'paid_amount_attrs': {'currencyID': invoice.company_currency_id.name},
                'currency_dp': self._get_currency_decimal_places(invoice.company_currency_id),
            }
            for p in invoice._l10n_co_dian_get_invoice_prepayments()
        ]

        vals['vals']['accounting_supplier_party_vals']['additional_account_id'] = vals['supplier']._l10n_co_edi_get_partner_type()
        vals['vals']['accounting_customer_party_vals']['additional_account_id'] = vals['customer'].commercial_partner_id._l10n_co_edi_get_partner_type()

        if invoice.l10n_co_edi_debit_note:
            vals['main_template'] = 'l10n_co_dian.ubl_20_DebitNote_dian'
        elif invoice.move_type in ('out_refund', 'in_refund'):
            vals['main_template'] = 'l10n_co_dian.ubl_20_CreditNote_dian'
        else:
            vals['main_template'] = 'l10n_co_dian.ubl_20_Invoice_dian'

        cufe_cude_cuds_vals = "".join(str(res) for res in self._dian_get_identifier_vals(invoice, vals).values())
        vals['vals']['uuid'] = sha384(cufe_cude_cuds_vals.encode()).hexdigest()  # as stated in the "Anexo Tecnico" file, SHA384 must be used
        vals['vals']['note_vals'].append({'note': cufe_cude_cuds_vals})
        return vals

    def _export_invoice(self, invoice):
        # EXTENDS account.edi.xml.ubl_20
        xml, errors = super()._export_invoice(invoice, convert_fixed_taxes=False)
        if errors:
            return xml, errors
        xml = self._dian_insert_corporate_registration_scheme_node(invoice, xml)
        return self._dian_sign_xml(xml, invoice)

    def _export_invoice_constraints(self, move, vals):
        # EXTENDS account.edi.xml.ubl_20
        constraints = super()._export_invoice_constraints(move, vals)
        now = fields.Datetime.now()
        oldest_date = now - timedelta(days=5)
        newest_date = now + timedelta(days=10)
        if not (oldest_date <= fields.Datetime.to_datetime(move.invoice_date) <= newest_date):
            constraints['dian_date'] = _("The issue date can not be older than 5 days or more than 5 days in the future.")
        # required fields on invoice
        if not move.l10n_co_dian_post_time:
            constraints['l10n_co_dian_post_time'] = _("A posted time is required to compute the CUFE/CUDE/CUDS.")
        # required fields on company
        operation_mode = self._dian_get_operation_mode(move)
        if not operation_mode:
            constraints["dian_operation_modes"] = _("No DIAN Operation Mode Matches")
        else:
            mandatory_fields = ['dian_software_id', 'dian_software_operation_mode', 'dian_software_security_code']
            if move.company_id.l10n_co_dian_test_environment:
                mandatory_fields.append('dian_testing_id')
            for field in mandatory_fields:
                constraints[field] = self._check_required_fields(operation_mode, field)
            if move.l10n_co_dian_identifier_type in ('cude', 'cuds') and not operation_mode.dian_software_security_code:
                constraints['l10n_co_dian_identifier_type'] = _("The software PIN is required to compute the CUDE/CUDS.")
        # required fields on journal
        if move.move_type == 'out_invoice' and not move.journal_id.l10n_co_dian_technical_key:
            constraints['l10n_co_dian_technical_key'] = _("A technical key on the journal is required to compute the CUFE.")
        for field in ('l10n_co_edi_dian_authorization_number', 'l10n_co_edi_dian_authorization_date',
                      'l10n_co_edi_dian_authorization_end_date', 'l10n_co_edi_min_range_number',
                      'l10n_co_edi_max_range_number', 'l10n_co_dian_technical_key'):
            constraints[f"dian_{field}"] = self._check_required_fields(move.journal_id, field)
        # fields on partners
        for role in ('customer', 'supplier'):
            commercial_partner = vals[role].commercial_partner_id
            constraints.update({
                f"dian_vat_{role}": self._check_required_fields(commercial_partner, 'vat'),
                f"dian_identification_type_{role}": self._check_required_fields(commercial_partner, 'l10n_latam_identification_type_id'),
                f"dian_obligation_type_{role}": self._check_required_fields(commercial_partner, 'l10n_co_edi_obligation_type_ids'),
            })
            if commercial_partner.l10n_latam_identification_type_id.l10n_co_document_code != 'rut' and commercial_partner.vat and '-' in commercial_partner.vat:
                constraints[f"dian_NIT_{role}"] = _("The identification number of %s contains '-' but is not a NIT.", commercial_partner.name)
            if vals[role].country_code == 'CO' and commercial_partner.vat != FINAL_CONSUMER_VAT:
                constraints[f'dian_country_subentity_{role}'] = self._check_required_fields(vals[role], 'state_id')
                constraints[f"dian_city_{role}"] = self._check_required_fields(vals[role], 'city_id')
        # fields on lines
        for line in move.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note')):
            product = line.product_id
            constraints[f"product_{product.id}"] = self._check_required_fields(
                product, ['default_code', 'barcode', 'unspsc_code_id'])
            if move.l10n_co_edi_type == L10N_CO_EDI_TYPE['Export Invoice'] and product:
                if not product.l10n_co_edi_customs_code:
                    constraints['dian_export_product_code'] = _("Every exportation product must have a customs code.")
                if not product.l10n_co_edi_brand:
                    constraints['dian_export_product_brand'] = _("Every exportation product must have a brand.")
            if "IBUA" in line.tax_ids.l10n_co_edi_type.mapped('name') and product.l10n_co_edi_ref_nominal_tax == 0:
                constraints['dian_sugar'] = _(
                    "'Volume in milliliters' should be set on product: %s when using IBUA taxes.", line.product_id.name)
            if not self._dian_uom_code(line):
                constraints['dian_uom'] = _("There is no Colombian code on the unit of measure: %s", line.product_uom_id.name)
            if move.l10n_co_edi_is_support_document and move.currency_id.is_zero(line.price_unit):
                constraints['dian_zero_lines'] = _("Every lines should have non zero price units.")

        if move.l10n_co_edi_operation_type == '20':
            # Credit note with a referenced invoice
            if not move.l10n_co_edi_description_code_credit:
                constraints['dian_credit_note_missing_reason'] = _("Please set a credit note reason as it is required for this type of transaction.")
            if not move.reversed_entry_id:
                constraints['dian_credit_note'] = _("There is no invoice linked to this credit note but the operation type is '20'.")
            elif not move.reversed_entry_id.l10n_co_edi_cufe_cude_ref:
                constraints['dian_credit_note_cufe'] = _("The invoice linked to this credit note has no CUFE.")

        if move.move_type == 'in_refund':
            # Support Document Credit Note
            if not move.reversed_entry_id:
                constraints['dian_credit_note'] = _("There is no support document linked to this credit note.")
            if not move.reversed_entry_id.l10n_co_edi_cufe_cude_ref:
                constraints['dian_credit_note_cufe'] = _("The support document linked to this credit note has no CUDS.")

        if move.l10n_co_edi_operation_type == '30':
            # Debit note with a referenced invoice
            if not move.debit_origin_id:
                constraints['dian_debit_note'] = _("There is no original debited invoice but the operation type is '30'.")
            elif not move.debit_origin_id.l10n_co_edi_cufe_cude_ref:
                constraints['dian_debit_note_cufe'] = _("The original debited invoice has no CUFE.")

        if move.l10n_co_edi_operation_type in ('20', '22'):
            constraints['dian_concepto_credit_note'] = self._check_required_fields(move, 'l10n_co_edi_description_code_credit')
        if move.l10n_co_edi_debit_note:
            constraints['dian_concepto_debit_note'] = self._check_required_fields(move, 'l10n_co_edi_description_code_debit')

        return constraints

    # -------------------------------------------------------------------------
    # Utils
    # -------------------------------------------------------------------------

    def _dian_tax_amount_repr(self, tax_amount):
        """ Returns a string representation of a float amount to fill the 'TaxSubtotal/TaxCategory/Percent' node.

        DIAN accepts up to 3 decimals for this node. But it also checks that the type of tax is consistent with the
        tax amount reported.
        For instance: '19.00' for an 'IVA' tax is allowed, but '19.000' is not (it raises: "FAS01b, Rechazo: Tributo
        IVA (01), INC (04) informado no coincide, revisar Porcentaje, Nombre y ID.").
        The majority of taxes have only 2 decimals, but some have 3 (and they should be reported with all their
        decimals), hence this weird function.
        """
        str_tax_amount = self.format_float(abs(tax_amount), 3)  # withholding taxes are reported as positives
        return str_tax_amount[:-1] if str_tax_amount.endswith('0') else str_tax_amount

    def _dian_uom_code(self, line):
        """ Colombia follows a standard that very much resembles the UNSPSC """
        if line.product_uom_id != self.env.ref('uom.product_uom_unit'):
            code = line.product_uom_id.l10n_co_edi_ubl
        else:
            code = '94'
        return code

    def _dian_tax_totals(self, move, taxes_vals, withholding):
        """
        Colombian particularity: there should be one `TaxTotal` per colombian tax type, comprising 1 or more
        `TaxSubtotal` (1 per tax amount). The same applies for `WithholdingTaxTotal`.

        :returns: [
            {
                'tax_amount': float,
                'currency': res.currency,
                'currency_dp': int,
                'tax_subtotal_vals': [{
                    'tax_amount': float,
                    'taxable_amount': float,
                    'currency': res.currency,
                    'currency_dp': int,
                    'tax_category_vals': {},
                }]
            },
        ]
        """
        def filter_tax_details(key):
            if move.l10n_co_edi_is_support_document:
                # For support document, only the taxes IVA (01), ReteICA (05), ReteRenta (06) should be included
                return key['tax_co_ret'] == withholding and key['tax_co_type'] in ('01', '05', '06')
            return key['tax_co_ret'] == withholding

        currency = move.company_id.currency_id
        tax_total_dict = defaultdict(lambda: {
            'currency': currency,
            'currency_dp': self._get_currency_decimal_places(currency),
            'tax_amount': 0,
            'per_unit_amount': 0,
            'tax_subtotal_vals': [],
        })
        filtered_tax_details = {k: v for k, v in taxes_vals['tax_details'].items() if filter_tax_details(k)}
        for grouping_key, vals in filtered_tax_details.items():
            tax_co_type = grouping_key['tax_co_type']
            tax_total_dict[tax_co_type]['tax_co_type'] = tax_co_type  # not used in the xml, used to build the CUFE
            tax_subtotal = {
                'currency': currency,
                'currency_dp': self._get_currency_decimal_places(currency),
                'taxable_amount': vals['base_amount'],
                'tax_amount': abs(vals['tax_amount']),   # abs for withholding taxes
                'tax_category_vals': {
                    'percent': self._dian_tax_amount_repr(float(vals['_tax_category_vals_']['percent'])),
                    'tax_scheme_vals': vals['_tax_category_vals_']['tax_scheme_vals'],
                },
            }
            if tax_co_type == '34':
                # IBUA (tax on sugar beverages) is a tax based on the quantity of sugar per 100mL
                # e.g. if the quantity of sugar per 100mL is > 10gr -> tax of 35$ per 100mL
                # In Odoo, we use fixed taxes and a field for the volume of the product: l10n_co_edi_ref_nominal_tax
                # Hence, we can infer the rate per 100mL of the tax
                tax_subtotal.pop('taxable_amount')
                tax_subtotal['base_unit_measure_attrs'] = {'unitCode': "ML"}
                if 'percent' in tax_subtotal['tax_category_vals']:
                    tax_subtotal['tax_category_vals'].pop('percent')
                # Total Volume in mL
                if 'tax_details_per_record' in taxes_vals:
                    tax_subtotal['base_unit_measure'] = sum(
                        base_line['product_id'].l10n_co_edi_ref_nominal_tax * base_line['quantity']
                        for base_line, _taxes_data in vals['base_line_x_taxes_data']
                    )
                else:
                    base_line = taxes_vals['base_line']
                    tax_subtotal['base_unit_measure'] = base_line['product_id'].l10n_co_edi_ref_nominal_tax * base_line['quantity']
                # Infer the rate per 100mL
                rate = vals['tax_amount'] * 100 / tax_subtotal['base_unit_measure']
                tax_subtotal['per_unit_amount'] = self.format_float(rate, 2)
            tax_total_dict[tax_co_type]['tax_amount'] += tax_subtotal['tax_amount']  # abs for withholding taxes
            tax_total_dict[tax_co_type]['tax_subtotal_vals'].append(tax_subtotal)

        if '05' in tax_total_dict and move.l10n_co_edi_is_support_document and withholding:
            # Taxes with type '05' are retention taxes (15 %) that apply on the *tax amount* of a regular VAT tax
            # Hence, the tax "15% RteVAT 19%" is encoded as a -2.85% tax in Odoo
            if 'tax_details_per_record' in taxes_vals:
                # On document level, backtrack the taxable amount based on the tax amount
                for subtotal in tax_total_dict['05']['tax_subtotal_vals']:
                    subtotal['tax_category_vals']['percent'] = '15.00'
                    subtotal['taxable_amount'] = subtotal['tax_amount'] / 0.15
            else:
                # On invoice line, look at the sibling tax total node '01' and extract its exact tax amount
                # DSAY05: the Taxable Amount for the taxes with type '05' should be equal to the Tax Amount
                # on which the taxes with type '01' were applied
                sibling_tax_totals = self._dian_tax_totals(move, taxes_vals, withholding=False)
                tax_amount_01 = next((tot for tot in sibling_tax_totals if tot['tax_co_type'] == '01'), {'tax_amount': 0})['tax_amount']
                for subtotal in tax_total_dict['05']['tax_subtotal_vals']:
                    subtotal['tax_category_vals']['percent'] = '15.00'
                    subtotal['taxable_amount'] = tax_amount_01
        return [v for k, v in tax_total_dict.items()]

    def _dian_get_identifier_vals(self, invoice, invoice_vals):
        """ Returns the values used to compute the CUFE/CUDE/CUDS """
        operation_mode = self._dian_get_operation_mode(invoice)

        def format_float(amount, precision_digits=invoice_vals['vals']['currency_dp']):
            return invoice_vals['format_float'](amount, precision_digits)

        def get_filtered_tax_amount(co_tax_code):
            """ Get the tax amount associated to a given colombian tax type code. """
            return sum(ttvals['tax_amount'] for ttvals in invoice_vals['vals']['tax_total_vals'] if ttvals['tax_co_type'] == co_tax_code)

        if invoice.l10n_co_dian_identifier_type in ('cude', 'cuds'):
            key = operation_mode.dian_software_security_code
        else:
            key = invoice.journal_id.l10n_co_dian_technical_key

        vals = {
            'invoice_id': invoice_vals['vals']['id'],
            'issue_date': invoice_vals['vals']['issue_date'],
            'issue_time': invoice_vals['vals']['issue_time'],  # invoice time (including tz)
            'line_extension_amount': format_float(invoice_vals['vals']['monetary_total_vals']['line_extension_amount']),
            'tax_code_01': '01',
            'ValImp1': format_float(get_filtered_tax_amount('01')),
            'tax_code_04': '04',
            'ValImp2': format_float(get_filtered_tax_amount('04')),
            'tax_code_03': '03',
            'ValImp3': format_float(get_filtered_tax_amount('03')),
            'ValTotFac': format_float(invoice_vals['vals']['monetary_total_vals']['payable_amount']),
            'supplier_company_id': invoice_vals['vals']['accounting_supplier_party_vals']['party_vals']['party_tax_scheme_vals'][0]['company_id'],
            'customer_company_id': invoice_vals['vals']['accounting_customer_party_vals']['party_vals']['party_tax_scheme_vals'][0]['company_id'],
            'key': key or 'missing_key',
            'profile_execution_id': invoice_vals['vals']['profile_execution_id'],
        }
        if invoice.l10n_co_edi_is_support_document:
            [vals.pop(k) for k in ('tax_code_04', 'ValImp2', 'tax_code_03', 'ValImp3')]
        return vals

    def _dian_insert_corporate_registration_scheme_node(self, invoice, xml):
        # Create a CorporateRegistrationScheme node
        root = etree.fromstring(xml)
        nsmap = root.nsmap
        corporate_node = etree.Element("{%s}CorporateRegistrationScheme" % nsmap.get('cac'), nsmap=nsmap)
        id_node = etree.SubElement(corporate_node, "{%s}ID" % nsmap.get('cbc'), nsmap=nsmap)
        id_node.text = invoice.journal_id.code
        name_node = etree.SubElement(corporate_node, "{%s}Name" % nsmap.get('cbc'), nsmap=nsmap)
        name_node.text = invoice.company_id.partner_id._get_vat_without_verification_code()
        # Insert
        legal_entity_node = root.find('.//{*}AccountingSupplierParty//{*}PartyLegalEntity')
        if legal_entity_node is not None:
            legal_entity_node.insert(2, corporate_node)
        return etree.tostring(cleanup_xml_node(root))

    def _dian_get_qr_code_url(self, invoice, identifier):
        """ Returns the value used to fill the sts:DianExtensions/sts:QRCode node """
        if invoice.company_id.l10n_co_dian_test_environment:
            url = 'https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentkey='
        else:
            url = 'https://catalogo-vpfe.dian.gov.co/document/searchqr?documentkey='
        return url + identifier

    def _dian_get_security_code(self, invoice, operation_mode):
        """ Returns the value for the 'SoftwareSecurityCode' node """
        return sha384((
            operation_mode.dian_software_id
            + operation_mode.dian_software_security_code
            + invoice.name
        ).encode()).hexdigest()

    def _dian_get_document_type_code(self, invoice):
        """ Returns the document type, used for the 'InvoiceTypeCode'/'CreditNoteTypeCode' node """
        if not invoice.l10n_co_edi_is_support_document:
            return invoice.l10n_co_edi_type.rjust(2, '0')
        elif invoice.move_type == 'in_refund':
            return '95'  # Nota de ajuste al documento soporte
        else:
            return '05'  # Documento soporte

    def _dian_get_customization_id(self, invoice):
        """ Returns the value used for the 'CustomizationID' node """
        if not invoice.l10n_co_edi_is_support_document:
            return invoice.l10n_co_edi_operation_type
        return '10' if invoice.partner_id.country_code == 'CO' else '11'

    def _dian_get_operation_mode(self, invoice):
        """Looks for the desired operation mode record based on the mode type"""
        mode = 'invoice' if invoice.is_sale_document() else 'bill'
        return invoice.company_id.l10n_co_dian_operation_mode_ids.filtered(
            lambda operation_mode: operation_mode.dian_software_operation_mode == mode
        )

    def _dian_sign_xml(self, xml, invoice):
        errors = []
        certificates_sudo = invoice.company_id.sudo().l10n_co_dian_certificate_ids
        operation_mode = self._dian_get_operation_mode(invoice)
        x509_certificates = []
        for cert_sudo in certificates_sudo:
            x509_certificates.append({
                'x509_issuer_description': cert_sudo._get_issuer_string(),
                'x509_serial_number': int(cert_sudo.serial_number),
            })
        root = etree.fromstring(xml)
        signature_vals = {
            'record': invoice,
            'sts_namespace': self._get_sts_namespace(invoice),
            'provider_check_digit': invoice.company_id.partner_id._get_vat_verification_code(),
            'provider_id': invoice.company_id.partner_id._get_vat_without_verification_code(),
            'software_id': operation_mode.dian_software_id,
            'software_security_code': self._dian_get_security_code(invoice, operation_mode),
            'qr_code_val': self._dian_get_qr_code_url(invoice, root.findtext('./cbc:UUID', namespaces=root.nsmap)),
            'document_id': "xmldsig-" + str(xml_utils._uuid1()),
            'key_info_id': "xmldsig-" + str(xml_utils._uuid1()) + "-keyinfo",
            'x509_certificate': cert_sudo._get_der_certificate_bytes().decode(),
            'x509_certificates': x509_certificates,
            'signature_value': 'to be filled later',
            # Colombia time (UTC-5): p.556 "Anexo-Tecnico-Resolucion[...].pdf"
            'signing_time': fields.datetime.now(tz=timezone('America/Bogota')).isoformat(timespec='milliseconds'),
            'sigcertif_digest': cert_sudo._get_fingerprint_bytes(formatting='base64').decode(),
            'claimed_role': "supplier",
        }
        extensions = self.env['ir.qweb']._render('l10n_co_dian.ubl_extension_dian', signature_vals)
        extensions = cleanup_xml_node(extensions, remove_blank_nodes=False)
        root.insert(0, extensions)
        xml_utils._remove_tail_and_text_in_hierarchy(root)
        # Hash and sign
        xml_utils._reference_digests(extensions.find(".//ds:SignedInfo", {'ds': 'http://www.w3.org/2000/09/xmldsig#'}))
        xml_utils._fill_signature(extensions.find(".//ds:Signature", {'ds': 'http://www.w3.org/2000/09/xmldsig#'}), cert_sudo)
        return etree.tostring(root, encoding='UTF-8'), errors

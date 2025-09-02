import logging
import uuid

from odoo import http, Command
from odoo.http import request
from odoo.tools import consteq
from odoo.tools.json import scriptsafe as json
from odoo.addons.pos_urban_piper import const
from .data_validator import object_of, list_of

from werkzeug import exceptions

_logger = logging.getLogger(__name__)

order_data_schema = object_of({
    'order': object_of({
        'items': list_of(object_of({
            'title': True,
            'price': True,
            'merchant_id': True,
            'quantity': True,
        })),
        'details': object_of({
            'order_subtotal': True,
            'total_taxes': True,
            'order_state': True,
            'channel': True,
            'id': True,
        }),
        'payment': True,
        'store': object_of({
            'merchant_ref_id': True,
        }),
    }),
    'customer': object_of({
        'name': True,
        'email': True,
        'phone': True,
        'address': True,
    }),
})

order_status_update_schema = object_of({
    'order_id': True,
    'new_state': True,
    'store_id': True,
})

rider_status_update_schema = object_of({
    'delivery_info': object_of({
        'current_state': True,
        'delivery_person_details': object_of({
            'name': True,
            'phone': True,
        }),
    }),
    'order_id': True,
    'store': object_of({
        'ref_id': True,
    }),
})


class PosUrbanPiperController(http.Controller):

    @http.route('/urbanpiper/webhook/<string:event_type>', type='json', methods=['POST'], auth='public')
    def webhook(self, event_type):
        if not consteq(request.httprequest.headers.get('X-Urbanpiper-Uuid'), request.env['ir.config_parameter'].sudo().get_param('pos_urban_piper.uuid')):
            # Ignore request if it's not from the same database
            return
        data = request.get_json_data()
        if event_type == 'order_placed':
            self._handle_data(data, order_data_schema, self._create_order, event_type)
        elif event_type == 'order_status_update':
            self._handle_data(data, order_status_update_schema, self._order_status_update, event_type)
        elif event_type == 'rider_status_update':
            self._handle_data(data, rider_status_update_schema, self._rider_status_update, event_type)

    def _handle_data(self, data, schema, handler, event_type):
        is_valid, error = schema(data)
        pos_config = request.env['pos.config']
        if is_valid:
            if event_type == 'order_placed':
                pos_config_sudo = request.env['pos.config'].sudo().search([
                    ('urbanpiper_store_identifier', '=', data['order']['store']['merchant_ref_id'])
                ])
                if not pos_config_sudo:
                    _logger.warning("UrbanPiper: Store not found for order %r", data['order'].get('id'))
                    pos_config.log_xml("UrbanPiper: - %s" % (data), 'urbanpiper_webhook_store_not_found')
                    return exceptions.BadRequest()
                if not pos_config_sudo.current_session_id:
                    _logger.warning("UrbanPiper: Session is not open for %r", pos_config_sudo.name)
                    pos_config.log_xml("UrbanPiper: - %s" % (data), 'urbanpiper_webhook_session_not_open%s')
                    return exceptions.BadRequest()
            handler(data)
        else:
            pos_config.log_xml("Payload - %s. Error - %s" % (data, error), 'urbanpiper_webhook_%s' % (event_type))
            _logger.warning("UrbanPiper: %r", error)

    def _create_order(self, data):
        order = data['order']
        customer = data['customer']
        customer_address = customer['address']
        details = order['details']
        pos_config_sudo = request.env['pos.config'].sudo().search([
            ('urbanpiper_store_identifier', '=', order['store']['merchant_ref_id'])
        ])
        customer_sudo = request.env['res.partner'].sudo().search(
            ['|', ('phone', '=', customer['phone']), ('mobile', '=', customer['phone'])]
        )
        if not customer_sudo:
            customer_sudo = request.env['res.partner'].sudo().create({
                'name': customer['name'],
                'phone': customer['phone'],
                'email': customer['email'],
                'mobile': customer['phone'],
                'street': customer_address.get('line_1'),
                'street2': customer_address.get('line_2'),
                'city': customer_address.get('city'),
                'zip': customer_address.get('pin'),
            })
        else:
            if customer_sudo.zip != customer_address.get('zip'):
                customer_sudo.write({
                    'street': customer_address.get('line_1'),
                    'street2': customer_address.get('line_2'),
                    'zip': customer_address.get('pin'),
                    'city': customer_address.get('city'),
                })
        order_reference = request.env['pos.order']._generate_unique_reference(
            pos_config_sudo.current_session_id.id,
            pos_config_sudo.id,
            pos_config_sudo.current_session_id.sequence_number,
            order['details']['channel'].capitalize()
        )

        def get_prep_time(details):
            data = details.get('prep_time')
            if data:
                return data.get('estimated') or data.get('max')

        pos_delivery_provider = request.env['pos.delivery.provider'].sudo().search([('technical_name', '=', details['channel'])], limit=1)
        if not pos_delivery_provider:
            _logger.warning("UrbanPiper: Delivery provider not found for %r", details['channel'])
            pos_config_sudo.log_xml("UrbanPiper: - %s" % (data), 'urbanpiper_webhook_delivery_provider_not_found')
            return exceptions.BadRequest()

        lines = [self._create_order_line(line, pos_config_sudo) for line in order['items']]
        for charge in details.get('charges', []):
            charge_title = charge.get('title', '').lower()
            charge_product = request.env.ref('pos_urban_piper.product_other_charges', False)
            if 'delivery' in charge_title:
                charge_product = request.env.ref('pos_urban_piper.product_delivery_charges', False)
            elif 'packaging' in charge_title:
                charge_product = request.env.ref('pos_urban_piper.product_packaging_charges', False)
            if not charge_product:
                _logger.warning("UrbanPiper: Charge product not found for %r", charge_title)
                pos_config_sudo.log_xml("UrbanPiper: - %s" % (data), 'urbanpiper_charge_product_not_found')
                continue
            total_tax = request.env["account.tax"].browse(
                [
                    tax_record.id
                    for tax_payload in charge.get("taxes", [])
                    if tax_payload.get("value")
                    and (
                        tax_record := request.env["account.tax"]
                        .sudo()
                        .search(
                            self._get_tax_domain(
                                pos_config_sudo,
                                int((100 * tax_payload["value"]) / charge.get("value")),
                            ),
                            limit=1,
                        )
                    )
                ]
            )
            tax_ids_after_fiscal_position = pos_config_sudo.urbanpiper_fiscal_position_id.map_tax(total_tax)
            taxes = tax_ids_after_fiscal_position.compute_all(charge.get('value'), pos_config_sudo.company_id.currency_id, 1, product=charge_product)
            lines.append(Command.create({
                'product_id': charge_product.sudo().id,
                'full_product_name': charge.get('title', charge_product.sudo().name),
                'qty': 1,
                'price_unit': charge.get('value'),
                'tax_ids': [Command.set(total_tax.ids)],
                'price_subtotal': taxes['total_excluded'],
                'price_subtotal_incl': taxes['total_included'],
                'note': charge.get('title'),
                'uuid': str(uuid.uuid4())
            }))
        discounts = details.get('ext_platforms', [{}])[0].get('discounts', [])
        discount_amt = sum(discount['value'] for discount in discounts if discount['is_merchant_discount'])
        general_note = "\n".join([
            f"{pos_delivery_provider.name} Discount: {pos_config_sudo.company_id.currency_id.symbol} {discount.get('value')}"
            for discount in discounts if not discount.get('is_merchant_discount')
        ])
        for discount in discounts:
            if discount.get('is_merchant_discount'):
                discount_product = request.env['product.product'].sudo().search([
                    ('name', '=', 'Merchant Discount'),
                    ('default_code', '=', 'MRDT')
                ], limit=1)
                if not discount_product:
                    discount_product = request.env['product.product'].sudo().create({
                        'name': 'Merchant Discount',
                        'type': 'service',
                        'list_price': 0,
                        'available_in_pos': True,
                        'taxes_id': [(5, 0, 0)],
                        'default_code': 'MRDT'
                    })
                lines.append(Command.create({
                    'product_id': discount_product.sudo().id,
                    'qty': 1,
                    'price_unit': -discount.get('value'),
                    'price_subtotal': -discount.get('value'),
                    'price_subtotal_incl': -discount.get('value'),
                    'note': discount.get('code'),
                    'uuid': str(uuid.uuid4()),
                }))
        number = str((pos_config_sudo.current_session_id.id % 10) * 100 + pos_config_sudo.current_session_id.sequence_number % 100).zfill(3)
        delivery_order = request.env["pos.order"].sudo().create({
            'name': order_reference,
            'partner_id': customer_sudo.id,
            'pos_reference': order_reference,
            'sequence_number': number,
            'tracking_number': number,
            'config_id': pos_config_sudo.id,
            'session_id': pos_config_sudo.current_session_id.id,
            'company_id': pos_config_sudo.company_id.id,
            'fiscal_position_id': pos_config_sudo.urbanpiper_fiscal_position_id.id,
            'lines': lines,
            'amount_paid': 0.0, #calculation is done below
            'amount_total': 0.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'delivery_identifier': details['id'],
            'delivery_status': details['order_state'].lower(),
            'general_note': "\n".join(
                x for x in [details.get('instructions'), general_note] if x and x.strip()
            ),
            'delivery_provider_id': pos_delivery_provider.id,
            'prep_time': get_prep_time(details),
            'delivery_json': json.dumps(data),
            'user_id':  pos_config_sudo.current_session_id.user_id.id,
            'uuid': str(uuid.uuid4()),
        })
        delivery_order._compute_prices()
        pos_config_sudo.current_session_id.sequence_number += 1
        self.after_delivery_order_create(delivery_order, details, pos_config_sudo)
        pos_config_sudo._send_delivery_order_count(delivery_order.id)

    def after_delivery_order_create(self, delivery_order, details, pos_config_sudo):
        pass

    def _get_tax_value(self, taxes_data, pos_config):
        """
        Override in delivery provider modules.
        """
        taxes = request.env['account.tax']
        for tax_line in taxes_data:
            taxes |= request.env['account.tax'].sudo().search([
                ('tax_group_id.name', '=', tax_line.get('title')),
                ('amount', '=', tax_line.get('rate'))
            ], limit=1)
        return taxes

    def _get_tax_domain(self, pos_config, tax_percentage):
        return [('company_id', '=', pos_config.company_id.id), ('amount', '=', tax_percentage)]

    def _create_order_line(self, line_data, pos_config_sudo):
        value_ids_lst = []
        note = ''
        if line_data.get('options_to_add'):
            note = '\n'.join([f"{option.get('title')} X {option.get('quantity')}" for option in line_data['options_to_add']])
            merchant_value_lst = [option.get('merchant_id') for option in line_data['options_to_add']]
            value_ids_lst = [int(vid.split('-')[1]) for vid in merchant_value_lst]
        price_extra = sum(option.get('total_price', 0) for option in line_data.get('options_to_add', []))
        attribute_value_ids = []
        values_to_remove = []
        if value_ids_lst:
            for value in value_ids_lst:
                value_id = request.env['product.attribute.value'].sudo().browse(value)
                if value_id.attribute_id.create_variant == 'no_variant' or value_id.attribute_id.display_type == 'multi':
                    product_option = request.env['product.template.attribute.value'].sudo().search([
                        ('product_tmpl_id', '=', int(line_data['merchant_id'].split('-')[0])),
                        ('product_attribute_value_id', '=', value)
                    ])
                    if product_option:
                        attribute_value_ids.append(product_option.id)
                    values_to_remove.append(value)
        variant_value_lst = [value for value in value_ids_lst if value not in values_to_remove]
        line_taxes = self._get_tax_value(line_data.get('taxes', []), pos_config_sudo)
        main_product = self._product_template_to_product_variant(int(line_data['merchant_id'].split('-')[0]), variant_value_lst)
        price_unit = float(line_data['price'] + price_extra)
        tax_ids_after_fiscal_position = pos_config_sudo.urbanpiper_fiscal_position_id.map_tax(line_taxes)
        taxes = tax_ids_after_fiscal_position.compute_all(price_unit, pos_config_sudo.company_id.currency_id, int(line_data['quantity']), product=main_product)
        lines = Command.create({
            'product_id': main_product.id,
            'full_product_name': line_data['title'],
            'qty': int(line_data['quantity']),
            'attribute_value_ids': attribute_value_ids,
            'price_extra': price_extra,
            'price_unit': price_unit,
            'price_subtotal': taxes['total_excluded'],
            'price_subtotal_incl': taxes['total_included'],
            'tax_ids': [Command.set(line_taxes.ids)] if line_taxes else None,
            'note': "\n".join(
                x for x in [line_data.get('instructions'), note] if x and x.strip()
            ),
            'uuid': str(uuid.uuid4()),
        })
        return lines

    def _product_template_to_product_variant(self, tmpl_id, value_ids):
        products = request.env['product.product'].sudo().search([('product_tmpl_id', '=', tmpl_id)])
        if products:
            if not value_ids:
                return products[0]
            if len(products) == 1:
                return products[0]
            product = products.filtered(
                lambda l: sorted(l.product_template_variant_value_ids.product_attribute_value_id.ids) == sorted(value_ids)
            )
            return product

    def _order_status_update(self, data):
        def _get_status_seq(status):
            return const.ORDER_STATUS_MAPPING[status][0]
        current_order_id = request.env['pos.order'].sudo().search([('delivery_identifier', '=', str(data['order_id']))])
        if not current_order_id:
            _logger.warning("UrbanPiper: Order %r not found for update the status.", data['order_id'])
            return
        if _get_status_seq(current_order_id.delivery_status.replace('_', ' ').title()) < _get_status_seq(data['new_state']):
            current_order_id.delivery_status = const.ORDER_STATUS_MAPPING[data['new_state']][1]
            pos_config_sudo = request.env['pos.config'].sudo().search([
                ('urbanpiper_store_identifier', '=', data['store_id'])
            ])
            if current_order_id.delivery_status == 'food_ready':
                pos_config_sudo._make_order_payment(current_order_id)
            pos_config_sudo._send_delivery_order_count(current_order_id.id)

    def _rider_status_update(self, data):
        current_order_id = request.env['pos.order'].sudo().search([('delivery_identifier', '=', str(data['order_id']))])
        if not current_order_id:
            _logger.warning("UrbanPiper: Order %r not found for update the rider status.", data['order_id'])
            return
        current_order_id.delivery_rider_json = json.dumps(data['delivery_info'])
        pos_config_sudo = request.env['pos.config'].sudo().search([
            ('urbanpiper_store_identifier', '=', data['store']['ref_id'])
        ])
        pos_config_sudo._send_delivery_order_count()

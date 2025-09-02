# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Fedex Shipping",
    'description': "Send your shippings through Fedex and track them online",
    'category': 'Inventory/Delivery',
    'version': '1.0',
    'application': True,
    'depends': ['stock_delivery', 'mail'],
    'data': [
        'data/delivery_fedex.xml',
        'views/delivery_fedex.xml',
    ],
    'license': 'OEEL-1',
}

from odoo.tests import tagged, Form, HttpCase


@tagged('post_install', '-at_install')
class TestVariantProductCreation(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mock_barcodelookup_data = {
            "products": [
                {
                    "barcode_number": "710535977349",
                    "barcode_formats": "UPC-A 710535977349, EAN-13 0710535977349",
                    "model": "v16",
                    "title": "Odoo Scale up",
                    "category": "Business & Industrial",
                    "manufacturer": "Odoo S.a",
                    "brand": "Odoo",
                    "color": "purple",
                    "size": "13cm * 19cm *3cm",
                    "length": "19 cm",
                    "width": "13 cm",
                    "height": "3 cm",
                    "weight": "0.5 kg",
                    "description": "Did you ever dream of starting your own business? Or wondered what you needed to know? With Odoo Scale-Up! you will learn all of that through 7 different business cases. You'll start by setting up the processes of a simple retail business. Then grow by deploying a manufacturing line, tracking services, launching an eCommerce and more!",
                    "features": [
                        "Start a new business",
                        "Manage project",
                        "Set up a MRP process"
                    ],
                }
            ]
        }

    def test_product_update_with_attr_while_disabled_variant(self):
        self.env = self.env(user=self.env.ref('base.user_admin'))

        def _create_product_lookup(name):
            product_form = Form(self.env['product.template'])
            product_form.name = name
            product = product_form.save()
            product._update_product_by_barcodelookup(product, self.mock_barcodelookup_data)
            return product

        if self.env.user.has_group('product.group_product_variant'):
            product = _create_product_lookup('Product with Variant')
            self.assertTrue(product.attribute_line_ids)

            # check after removing group
            group_product = self.env.ref('product.group_product_variant', False)
            group_product.write({'users': [(3, self.env.user.id)]})

        product = _create_product_lookup('Product without Variant')
        self.assertFalse(product.attribute_line_ids)

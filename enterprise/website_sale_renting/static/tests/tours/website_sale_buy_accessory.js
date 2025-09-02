/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as tourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add('shop_buy_accessory_rental_product', {
    url: '/shop',
    steps: () => [
        ...tourUtils.addToCart({productName: "Parent product"}),
        tourUtils.goToCart({quantity: 1}),
        {
            content: "Verify there are 1 quantity of Parent product",
            trigger: '#cart_products div div.css_quantity input[value="1"]',
        },
        {
            content: "Add Accessory product to cart via the quick add button",
            trigger: 'a:contains("Add to cart")',
            run: "click",
        },
        {
            content: "Check product added to the cart",
            trigger: ".my_cart_quantity:contains(2)",
        }
    ]
});

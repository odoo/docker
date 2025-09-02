/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as tourUtils from '@website_sale/js/tours/tour_utils';

registry.category("web_tour.tours").add("rental_cart_update_duration", {
    url: "/shop",
    steps: () => [
        {
            content: "Search computer write text",
            trigger: 'form input[name="search"]',
            run: "edit computer",
        },
        {
            content: "Search computer click",
            trigger: 'form:has(input[name="search"]) .oe_search_button',
            run: "click",
        },
        {
            content: "Select computer",
            trigger: '.oe_product_cart:first a:contains("Computer")',
            run: "click",
        },
        {
            content: "Open daterangepicker",
            trigger: "input[name=renting_start_date]",
            run: "click",
        },
        {
            content: "Pick start time",
            trigger: ".o_time_picker_select:eq(0)",
            run: "select 6",
        },
        {
            content: "Pick start time",
            trigger: ".o_time_picker_select:eq(1)",
            run: "select 0",
        },
        {
            content: "Pick end time",
            trigger: ".o_time_picker_select:eq(2)",
            run: "select 12",
        },
        {
            content: "Pick end time",
            trigger: ".o_time_picker_select:eq(3)",
            run: "select 0",
        },
        {
            content: "Apply change",
            trigger: ".o_datetime_buttons button.o_apply",
            run: "click",
        },
        {
            content: "click on add to cart",
            trigger:
                '#product_detail form[action^="/shop/cart/update"] #add_to_cart',
            run: "click",
        },
        tourUtils.goToCart(),
        {
            content: "Verify Rental Product is in the cart",
            trigger: '#cart_products div div.css_quantity input[value="1"]',
        },
        {
            content: "Open daterangepicker",
            trigger: "input[name=renting_start_date]",
            run: "click",
        },
        {
            content: "Pick start time",
            trigger: ".o_time_picker_select:eq(0)",
            run: "select 8",
        },
        {
            content: "Apply change",
            trigger: ".o_datetime_buttons button.o_apply",
            run: "click",
        },
        {
            content: "Verify order line rental period start time",
            trigger: 'div.text-muted.small span:contains("08:00")',
        },
        {
            content: "Verify order line rental period return time",
            trigger: 'div.text-muted.small span:contains("12:00")',
        },
    ],
});

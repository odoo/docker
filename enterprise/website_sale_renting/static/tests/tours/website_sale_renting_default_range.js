/** @odoo-module **/

import { registry } from "@web/core/registry";

registry
    .category("web_tour.tours")
    .add("website_sale_renting_default_duration_from_default_range", {
        url: "/shop?start_date=2023-12-17+23%3A00%3A00&end_date=2023-12-22+22%3A59%3A59",
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
                content: "Check that the duration is correct",
                trigger: '.o_renting_duration:contains("120")',
            },
            {
                content: "Check that the unit is correct",
                trigger: '.o_renting_unit:contains("Hours")',
            },
        ],
    });

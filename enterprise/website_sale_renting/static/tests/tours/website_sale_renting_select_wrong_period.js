const { DateTime } = luxon;

import { registry } from '@web/core/registry';

function getValidNextStartDatetime() {
    return DateTime
            .now()
            .plus({ weeks: 1 })
            .set({ weekday: 1 })
            .toFormat('D TT'); // next monday
}

function getValidNextEndDatetime() {
    return DateTime
            .now()
            .plus({ weeks: 1 })
            .set({ weekday: 3 })
            .toFormat('D TT'); // next wednesday
}

/**
 * Tests that css_not_available class is applied (removed) when picking an invalid (valid) rental
 * period.
 */
registry
    .category('web_tour.tours')
    .add('website_sale_renting_select_wrong_period', {
        url: '/shop?search=Computer',
        steps: () => [
            {
                content: 'Select Computer',
                trigger: '.oe_product_cart:first a:contains("Computer")',
                run: 'click',
            },
            {
                content: 'Pick an invalid start date',
                trigger: 'input[name=renting_start_date]',
                run: 'edit 01/01/2000 00:00:00',
            },
            {
                content: 'Apply change',
                trigger: '.o_datetime_buttons button.o_apply',
                run: 'click',
            },
            {
                content: 'Check that css_not_available has been added to the product form',
                trigger: 'form[action="/shop/cart/update"].css_not_available'
            },
            {
                content: 'Pick a valid end date first (otherwise start date after end date)',
                trigger: 'input[name=renting_end_date]',
                run: `edit ${getValidNextEndDatetime()}`,
            },
            {
                content: 'Apply change',
                trigger: '.o_datetime_buttons button.o_apply',
                run: 'click',
            },
            {
                content: 'Pick a valid start date',
                trigger: 'input[name=renting_start_date]',
                run: `edit ${getValidNextStartDatetime()}`,
            },
            {
                content: 'Apply change',
                trigger: '.o_datetime_buttons button.o_apply',
                run: 'click',
            },
            {
                content: 'Check that css_not_available has been removed',
                trigger: 'form[action="/shop/cart/update"]:not(.css_not_available)'
            },
        ],
   });

/** @odoo-module **/

import { registry } from "@web/core/registry";
import helper from '@mrp_workorder/../tests/tours/tour_helper_mrp_workorder';

registry.category("web_tour.tours").add('test_serial_tracked_and_register', { steps: () => [
    {
        trigger: '.o_tablet_client_action',
        run: function() {
            helper.assert(document.querySelector('input[id="finished_lot_id_0"]').value, 'Magic Potion_1');
        }
    },
    {
        trigger: ".o_tablet_client_action",
        run: "click",
    },
    {
        // sn should have been updated to match move_line sn
        trigger: 'div.o_field_widget[name="lot_id"] input ',
        run: function() {
            helper.assert(document.querySelector('input[id="lot_id_0"]').value, 'Magic_2');
        }
    },
    {
        trigger: ".o_tablet_client_action",
        run: "click",
    },
    {
        trigger: `.btn[name="button_start"]`,
        run: "click",
    },
    {
        trigger: 'div.o_field_widget[name="lot_id"] input ',
        tooltipPosition: 'bottom',
        run: "edit Magic_3",
    },
    {
        trigger: `.ui-menu-item > a:contains("Magic_3")`,
        run: "click",
    },
    {
        trigger: ".o_tablet_client_action",
        run: "click",
    },
    {
        trigger: 'div.o_field_widget[name="finished_lot_id"] input ',
        tooltipPosition: 'bottom',
        run: "edit Magic Potion_2",
    },
    {
        trigger: `.ui-menu-item > a:contains("Magic Potion_2")`,
        run: "click",
    },
    {
        // comp sn shouldn't change when produced sn is changed
        trigger: 'div.o_field_widget[name="lot_id"] input',
        run: function() {
            helper.assert(document.querySelector('input[id="lot_id_0"]').value, 'Magic_3');
        }
    },
    {
        trigger: ".o_tablet_client_action",
        run: "click",
    },
    {
        trigger: 'div.o_field_widget[name="lot_id"] input ',
        tooltipPosition: 'bottom',
        run: "edit Magic_1",
    },
    {
        trigger: `.ui-menu-item > a:contains("Magic_1")`,
        run: "click",
    },
    {
        trigger: ".o_tablet_client_action",
        run: "click",
    },
    {
        // produced sn shouldn't change when comp sn is changed
        trigger: 'div.o_field_widget[name="finished_lot_id"] input ',
        run: function() {
            helper.assert(document.querySelector('input[id="finished_lot_id_0"]').value, 'Magic Potion_2');
        }
    },
    {
        trigger: ".o_tablet_client_action",
        run: "click",
    },
    {
        trigger: ".btn-primary[name='action_next']",
        run: "click",
    },
    {
        trigger: "button[name=do_finish]",
        run: "click",
    },
    {
        trigger: ".o_searchview_input",
        run: "click",
    },
]});

registry.category("web_tour.tours").add('test_access_shop_floor_with_multicomany', {
    url: '/odoo/action-menu',
    steps: () => [{
        content: 'Select Shop Floor app',
        trigger: 'a.o_app:contains("Shop Floor")',
        run: "click",
    },{
        content: 'Close the select workcenter panel',
        trigger: 'button.btn-close',
        run: "click",
    },{
        content: 'Check that we entered the app with first company',
        trigger: 'div.o_mrp_display',
        run: "click",
    },{
        content: 'Go back to home menu',
        trigger: '.o_home_menu',
        run: "click",
    },{
        content: 'Click on switch  company menu',
        trigger: '.o_switch_company_menu button',
        run: "click",
    },{
        content: 'Select another company',
        trigger: 'div[role="button"]:contains("Test Company")',
        run: "click",
    },{
        content: 'Check that we switched companies',
        trigger: '.o_switch_company_menu button span:contains("Test Company")',
    },{
        content: 'Select Shop Floor app',
        trigger: 'a.o_app:contains("Shop Floor")',
        run: "click",
    },{
        content: 'Close the select workcenter panel again',
        trigger: '.btn-close',
        run: "click",
    },{
        content: 'Check that we entered the app with second company',
        trigger: 'div.o_mrp_display',
        run: "click",
    },{
        content: 'Check that the WO is not clickable',
        trigger: 'div.o_mrp_display_record.o_disabled',
    }]
})

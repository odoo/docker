/** @odoo-module **/

import { registry } from "@web/core/registry";
import helper from './tour_helper_mrp_workorder';

registry.category("web_tour.tours").add("test_shop_floor", {
    steps: () => [
    {
        content: 'Select the workcenter the first time we enter in shopfloor',
        trigger: '.form-check:has(input[name="Jungle"])',
        run: "click",
    },
    {
        trigger: '.form-check:has(input[name="Jungle"]:checked)',
    },
    {
        trigger: 'footer.modal-footer button.btn-primary',
        run: "click",
    },
    {
        trigger: '.o_control_panel_actions button:contains("Jungle")',
    },
    {
        content: 'Open the employee panel',
        trigger: 'button[name="employeePanelButton"]',
        run: "click",
    },
    {
        content: 'Add operator button',
        trigger: 'button:contains("Operator")',
        run: "click",
    },
    {
        content: "Scan Abbie Seedy's badge",
        trigger: ".modal-body .o_mrp_employee_tree_view",
        run: "scan 659898105101",
    },
    {
        trigger: ".o_mrp_employees_panel li.o_admin_user:contains(Abbie Seedy)",
    },
    {
        content: 'Add operator button',
        trigger: 'button:contains("Operator")',
        run: "click",
    },
    {
        content: 'Select the Billy Demo employee',
        trigger: '.modal-body .o_mrp_employee_tree_view .o_data_row td:contains("Billy Demo")',
        run: "click",
    },
    {
        trigger: '.o_mrp_employees_panel li.o_admin_user:contains(Billy Demo)',
    },
    {
        content: 'Go to workcenter Savannah from MO card',
        trigger: '.o_mrp_record_line button span:contains("Savannah")',
        run: "click",
    },
    {
        trigger: '.o_control_panel_actions button.active:contains("Savannah")',
    },
    {
        content: 'Start the workorder on header click',
        trigger: '.o_finished_product span:contains("Giraffe")',
        run: "click",
    },
    {
        content: "Register production check",
        trigger: ".modal:not(.o_inactive_modal) .btn.fa-plus",
        run: "click",
    },
    {
        content: "Validate production check",
        trigger: '.modal:not(.o_inactive_modal) button:contains("Validate"):enabled',
        run: "click",
    },
    {
        trigger:
            '.modal:not(.o_inactive_modal):contains(Instructions) button[barcode_trigger="NEXT"]',
        run: "scan OBTNEXT",
    },
    {
        trigger: '.modal:not(.o_inactive_modal) .modal-title:contains("Register legs")',
    },
    {
        content: "Component not tracked registration and continue production",
        trigger:
            '.modal:not(.o_inactive_modal):contains(Register legs) button[barcode_trigger="CONT"]',
        run: "click",
    },
    {
        trigger: '.o_field_widget[name="qty_done"] input:value("0.00")',
    },
    {
        content: "Add 2 units",
        trigger: '.o_field_widget[name="qty_done"] input',
        run: "edit 2 && click .modal-body",
    },
    {
        trigger: '.o_field_widget[name="qty_done"] input:value("2.00")',
    },
    {
        content: 'Click on "Validate"',
        trigger: 'button[barcode_trigger="NEXT"]',
        run: "click",
    },
    {
        trigger: '.o_field_widget[name="lot_id"] input:value("NE1")',
    },
    {
        trigger: 'div.o_field_widget[name="lot_id"] input ',
        tooltipPosition: 'bottom',
        run: "edit NE2",
    },
    {
        trigger: `.ui-menu-item > a:contains("NE2")`,
        run: "click",
    },
    {
        trigger: 'button[barcode_trigger="CONT"]',
        run: "click",
    },
    {
        trigger: '.o_field_widget[name="lot_id"] input:value("NE1")',
    },
    {
        trigger: 'button[barcode_trigger="NEXT"]',
        run: "click",
    },
    {
        trigger: '.modal:not(.o_inactive_modal) .modal-title:contains("Release")',
    },
    {
        trigger: ".modal:not(.o_inactive_modal) .modal-header .btn-close",
        run: "click",
    },
    {
        content: 'Open instruction',
        trigger: 'button:contains("Instructions")',
        run: "click",
    },
    {
        trigger: '.modal:not(.o_inactive_modal) .modal-title:contains("Release")',
    },
    {
        trigger: '.modal:not(.o_inactive_modal) button[barcode_trigger="NEXT"]',
        run: "click",
    },
    {
        content: "Close first operation",
        trigger: '.card-footer button[barcode_trigger="CLWO"]:contains(Mark as Done)',
        run: "click",
    },
    {
        content: "Navigate to next operation",
        trigger: "button:contains(Next Operation)",
        run: "click",
    },
    {
        trigger: 'div.o_mrp_display_record:contains("Release") .card-header .fa-play',
        run: "click",
    },
    {
        content: "Open the WO setting menu again",
        trigger: '.o_mrp_display_record:contains("Release") .card-footer button.fa-gear',
        run: "click",
    },
    {
        content: "Add an operation button",
        trigger: '.modal:not(.o_inactive_modal) button[name="addComponent"]',
        run: "click",
    },
    {
        content: 'Ensure the catalog is opened',
        trigger: '.modal:not(.o_inactive_modal) .o_product_kanban_catalog_view',
    },
    {
        content: 'Add Color',
        trigger: '.modal-body .o_searchview_input',
        run: "edit color && press Enter",
    },
    {
        content: 'Ensure the search is done',
        trigger: '.modal-body div.o_searchview_facet:contains("color")'
    },
    {
        trigger: '.modal-body:not(:has(article.o_kanban_record:not(:contains("Color"))))',
    },
    {
        content: 'Add Color',
        trigger: '.modal article.o_kanban_record:contains("Color") button .fa-shopping-cart',
        run: "click",
    },
    {
        content: 'Ensure the Color product is added',
        trigger: '.modal button .fa-trash',
    },
    {
        content: "Close the catalog",
        trigger: '.modal-header .btn-close',
        run: "click",
    },
    {
        trigger: "body:not(:has(.modal))",
    },
    {
        trigger: 'div.o_mrp_display_record .card-header .fa-pause',
        run: "click",
    },
    {
        trigger: 'div.o_mrp_display_record .card-header .fa-play',
    },
    {
        trigger: ".card-footer button[barcode_trigger=CLWO]:contains(Mark as Done):enabled",
        run: "click",
    },
    {
        trigger: ".card-footer button[barcode_trigger=CLWO]:contains(Undo)",
    },
    {
        trigger: ".card-footer button[barcode_trigger=CLMO]",
        run: "click",
    },
    {
        trigger: ".o_nocontent_help",
    },
    {
        content: "Leave shopfloor",
        trigger: ".o_home_menu .fa-sign-out",
        run: "click",
    },
    {
        trigger: ".o_apps",
    },
    ],
});

registry.category("web_tour.tours").add("test_shop_floor_auto_select_workcenter", {
    steps: () => [
        // Select 3 available Work Centers.
        { trigger: "input[name='Preparation Table 1']", run: "click" },
        { trigger: "input[name='Preparation Table 2']", run: "click" },
        { trigger: "input[name='Furnace']", run: "click" },
        { trigger: ".modal-footer button.btn-primary", run: "click" },
        {
            trigger: ".o_control_panel_actions button:nth-child(3)",
            run: () => {
                const selectionButtons = document.querySelectorAll(
                    '.o_control_panel_actions button.text-nowrap'
                );
                helper.assert(selectionButtons.length, 3, "Three WC buttons should be visible");
            },
        },
        // Exit the Shop Floor and re-open it.
        { trigger: ".o_home_menu", run: "click" },
        { trigger: ".o_menuitem[href='/odoo/shop-floor']", run: "click" },
        { trigger: ".o_control_panel_actions button:first-child.active" },
        { trigger: ".o_control_panel_actions button:nth-child(2):not(.active)" },
        { trigger: ".o_control_panel_actions button:nth-child(3):not(.active)" },

        { trigger: ".o_control_panel_actions button.fa-plus", run: "click" },
        { trigger: ".o_mrp_workcenter_dialog" },
        { trigger: "input[name='All MO']", run: "click" },
        { trigger: "input[name='My WO']", run: "click" },
        { trigger: ".modal-footer button.btn-primary", run: "click" },

        // Exit/re-open the Shop Floor again then check first button is selected (not "All MO".)
        { trigger: ".o_home_menu", run: "click" },
        { trigger: ".o_menuitem[href='/odoo/shop-floor']", run: "click" },
        {
            trigger: ".o_action.o_mrp_display",
            run: () => {
                const selectedWC = document.querySelector(
                    ".o_control_panel_actions button:first-child.active"
                );
                helper.assert(selectedWC.innerText.includes("Preparation Table 1"), true);
            }
        },
        // Unselect WCs then re-select them to change the order ("All MO" will be first.)
        { trigger: ".o_control_panel_actions button.fa-plus", run: "click" },
        { trigger: ".o_mrp_workcenter_dialog" },
        { trigger: "input[name='Preparation Table 1']", run: "click" },
        { trigger: "input[name='Preparation Table 2']", run: "click" },
        { trigger: "input[name='Furnace']", run: "click" },
        { trigger: ".modal-footer button.btn-primary", run: "click" },

        { trigger: ".o_web_client:not(.modal-open)" },
        { trigger: ".o_control_panel_actions button.fa-plus", run: "click" },
        { trigger: ".o_mrp_workcenter_dialog" },
        { trigger: "input[name='Preparation Table 1']", run: "click" },
        { trigger: "input[name='Preparation Table 2']", run: "click" },
        { trigger: "input[name='Furnace']", run: "click" },
        { trigger: ".modal-footer button.btn-primary", run: "click" },

        {
            trigger: ".o_web_client:not(.modal-open)",
            run: () => {
                const firstButton = document.querySelector(
                    ".o_control_panel_actions button:first-child"
                );
                helper.assert(firstButton.innerText.includes("All MO"), true);
            }
        },

        // Exit/re-open the Shop Floor once again then check first button is "All MO" and is selected.
        { trigger: ".o_home_menu", run: "click" },
        { trigger: ".o_menuitem[href='/odoo/shop-floor']", run: "click" },
        {
            trigger: ".o_action.o_mrp_display",
            run: () => {
                const selectedWC = document.querySelector(
                    ".o_control_panel_actions button:first-child.active"
                );
                helper.assert(selectedWC.innerText.includes("All MO"), true);
            }
        },
        // Check the MO is visible now but won't be once "Preparation Table 2" will be selected.
        { trigger: ".o_mrp_display_record .o_mrp_record_line:contains('Prepare the pizza')" },
        { trigger: ".o_control_panel_actions button.fa-plus", run: "click" },
        { trigger: ".o_mrp_workcenter_dialog" },
        { trigger: "input[name='All MO']", run: "click" },
        { trigger: "input[name='My WO']", run: "click" },
        { trigger: "input[name='Preparation Table 1']", run: "click" },
        { trigger: ".modal-footer button.btn-primary", run: "click" },
        // Exit/re-open the Shop Floor once again, "Preparation Table 2" should be the first WC.
        { trigger: ".o_home_menu", run: "click" },
        { trigger: ".o_menuitem[href='/odoo/shop-floor']", run: "click" },
        {
            trigger: ".o_view_nocontent .o_nocontent_help" ,
            run: () => {
                const selectedWC = document.querySelector(
                    ".o_control_panel_actions button:first-child.active"
                );
                helper.assert(selectedWC.innerText.includes("Preparation Table 2"), true);
            }
        },
        // Exit the Shop Floor and open it from a WO form view.
        { trigger: ".o_home_menu", run: "click" },
        { trigger: ".o_menuitem[href='/odoo/work-centers']", run: "click" },
        { trigger: "button[data-menu-xmlid='mrp.menu_mrp_manufacturing']", run: "click" },
        { trigger: "a[data-menu-xmlid='mrp.menu_mrp_workorder_todo']", run: "click" },
        { trigger: "[name='workcenter_id'][data-tooltip='Furnace']", run: "click" },
        { trigger: "button[name='action_open_mes']", run: "click" },
        // Check whatever was selected, when we come from a WO form view, only its WC is displayed.
        {
            trigger: ".o_action.o_mrp_display",
            run: () => {
                const selectedWC = document.querySelector(
                    ".o_control_panel_actions button:first-child.active"
                );
                helper.assert(selectedWC.innerText.includes("Furnace"), true);
                const selectionButtons = document.querySelectorAll(
                    '.o_control_panel_actions button.text-nowrap'
                );
                helper.assert(selectionButtons.length, 1, "Only one WC buttons should be visible");
            }
        },
    ],
});

registry.category("web_tour.tours").add("test_generate_serials_in_shopfloor", {
    steps: () => [
    {
        content: 'Make sure workcenter is available',
        trigger: '.form-check:has(input[name="Assembly Line"])',
        run: "click",
    },
    {
        trigger: '.form-check:has(input[name="Assembly Line"]:checked)',
    },
    {
        content: 'Confirm workcenter',
        trigger: 'button:contains("Confirm")',
        run: "click",
    },
    {
        content: 'Select workcenter',
        trigger: 'button.btn-light:contains("Assembly Line")',
        run: "click",
    },
    {
        content: 'Open the wizard',
        trigger: '.o_mrp_record_line .text-truncate:contains("Register byprod")',
        run: "click",
    },
    {
        content: 'Open the serials generation wizard',
        trigger: '.o_widget_generate_serials button',
        run: "click",
    },
    {
        content: 'Input a serial',
        trigger: '#next_serial_0',
        run: "edit 00001",
    },
    {
        content: 'Generate the serials',
        trigger: 'button.btn-primary:contains("Generate")',
        run: "click",
    },
    {
        content: 'Save and close the wizard',
        trigger: '.o_form_button_save:contains("Save")',
        run: "click",
    },
    {
        content: 'Set production as done',
        trigger: 'button.btn-primary:contains("Mark as Done")',
        run: "click",
    },
    {
        content: 'Close production',
        trigger: 'button.btn-primary:contains("Close Production")',
    },
    ],
});

registry.category("web_tour.tours").add("test_canceled_wo", {
    steps: () => [
        {
            content: 'Make sure workcenter is available',
            trigger: '.form-check:has(input[name="Assembly Line"])',
            run: "click",
        },
        {
            trigger: '.form-check:has(input[name="Assembly Line"]:checked)',
        },
        {
            content: 'Confirm workcenter',
            trigger: 'button:contains("Confirm")',
            run: "click",
        },
        {
            content: 'Check MO',
            trigger: 'button.btn-light:contains("Assembly Line")',
            run: () => {
                if (document.querySelectorAll("ul button:not(.btn-secondary)").length > 1)
                    console.error("Multiple Workorders");
            },
        },
    ],
});

registry.category("web_tour.tours").add('test_change_qty_produced', { steps: () => [
        {
            content: 'Make sure workcenter is available',
            trigger: '.form-check:has(input[name="WorkCenter"])',
            run: "click",
        },
        {
            content: 'Make sure that Workcenter was checked',
            trigger: '.form-check:has(input[name="WorkCenter"]:checked)',
        },
        {
            content: 'Confirm workcenter',
            trigger: 'button:contains("Confirm")',
            run: "click",
        },
        {
            content: 'Select workcenter',
            trigger: 'button.btn-light:contains("WorkCenter")',
            run: "click",
        },
        {
            content: 'Open the wizard',
            trigger: '.o_mrp_record_line .text-decoration-line-through:contains("Register Production")',
            run: "click",
        },
        {
            content: 'Edit the quantity producing',
            trigger: 'input[inputmode="decimal"]',
            run: "edit 3",
        },
        {
            content: 'Validate',
            trigger: 'button.btn-primary:contains("Validate")',
            run: "click",
        },
        {
            content: 'Waiting modal to close',
            trigger: "body:not(:has(.o_dialog))",
        },
        {
            content: "Mark the WorkOrder as Done",
            trigger: 'button.btn-primary:contains("Mark as Done")',
            run: "click",
        },
        {
            content: "Check if the WO was finished",
            trigger: 'button.btn-primary:contains("Close Production")',
            run: "click",
        },
        {
            content: "Confirm consumption warning",
            trigger: 'button.btn-primary:contains("Confirm")',
            run: "click",
        },
        {
            content: "Dismiss backorder",
            trigger: 'button.btn-secondary:contains("No Backorder")',
            run: "click",
        },
        {
            content: "Check that there are no open work orders",
            trigger: '.o_nocontent_help',
        },
    ]
});

registry.category("web_tour.tours").add('test_updated_quality_checks', {steps: () => [
    {
        content: 'Make sure workcenter is available',
        trigger: '.form-check:has(input[name="Assembly Line"])',
        run: 'click',
    },
    {
        trigger: '.form-check:has(input[name="Assembly Line"])',
    },
    {
        content: 'Confirm workcenter',
        trigger: 'button:contains("Confirm")',
        run: 'click',
    },
    {
        content: 'Select workcenter',
        trigger: 'button.btn-light:contains("Assembly Line")',
        run: 'click',
    },
    {
        trigger: '.o_control_panel_actions button.active:contains("Assembly Line")',
    },
    {
        content: 'Open quality check dropdown',
        trigger: '.accordion-button',
        run: 'click',
    },
    {
        content: 'Open register production',
        trigger: '.o_mrp_record_line span:contains("Register Production")',
        run: 'click',
    },
    {
        trigger: '.o_workorder_lot span:contains("serial")',
    },
    {
        content: 'Register production check',
        trigger: '.o_workorder_lot .btn.fa-plus',
        run: 'click',
    },
    { trigger: 'button[barcode_trigger="NEXT"]', run: 'click' },
    {
        trigger: '.o_field_widget[name="qty_done"] input:value("1.00")',
    },
    {
        content: 'Quantity shown 1 of 1',
        trigger: 'span[name="component_remaining_qty"]:contains("1.00")',
    },
]})

registry.category("web_tour.tours").add("test_update_tracked_consumed_materials_in_shopfloor", {
    steps: () => [
        {
            content: "Make sure workcenter is available",
            trigger: ".form-check:has(input[name='Lovely Workcenter'])",
            run: "click",
        },
        {
            trigger: ".form-check:has(input[name='Lovely Workcenter'])",
        },
        {
            trigger: "button:contains('Confirm')",
            run: "click",
        },
        {
            content: "Check that we are in the MO view",
            trigger: ".o_mrp_display_records button:contains('Lovely Workcenter')",
        },
        {
            content: "Swap to the WO view of the Lovely Workcenter",
            trigger: "button.btn-light:contains('Lovely Workcenter')",
            run: "click",
        },
        {
            content: "Open register production",
            trigger: ".accordion button:contains('Instructions')",
            run: "click",
        },
        {
            trigger: ".modal-header .modal-title:contains('Register component')",
        },
        {
            trigger: ".modal-header .modal-title:contains('Register component')",
            run: "click",
        },
        {
            content: "Register SN002",
            trigger: ".o_workorder_lot input",
            run: "edit SN002",
        },
        {
            trigger: ".dropdown-item:contains('SN002')",
            run: "click",
        },
        {
            trigger: ".modal-header .modal-title:contains('Register component')",
            run: "click",
        },
        {
            content: "Check that SN002 was registered",
            trigger: ".o_workorder_lot input:value('SN002')",
        },
        {
            trigger: "button:contains('Continue consumption')",
            run: "click",
        },
        {
            trigger: ".modal-header .modal-title:contains('Register component')",
            run: "click",
        },
        {
            content: "check that the quantity was correctly updated",
            trigger: "span[name='component_remaining_qty']:contains('1.00')",
        },
        //  Register SN004 => not available so should take from WH/Stock
        {
            content: "Register SN004",
            trigger: ".o_workorder_lot input",
            run: "edit SN004",
        },
        {
            trigger: ".dropdown-item:contains('SN004')",
            run: "click",
        },
        {
            trigger: ".modal-header .modal-title:contains('Register component')",
            run: "click",
        },
        {
            content: "Check that SN004 was registered",
            trigger: ".o_workorder_lot input:value('SN004')",
        },
        {
            trigger: "button:contains('Continue consumption')",
            run: "click",
        },
        {
            trigger: ".modal-header .modal-title:contains('Register component')",
            run: "click",
        },
        {
            trigger: ".modal-content:not(:has(span[name=component_remaining_qty]))",
        },
        {
            content: "Register SN003",
            trigger: ".o_workorder_lot input",
            run: "edit SN003",
        },
        {
            trigger: ".dropdown-item:contains('SN003')",
            run: "click",
        },
        {
            trigger: ".modal-header .modal-title:contains('Register component')",
            run: "click",
        },
        {
            content: "Check that SN003 was registered",
            trigger: ".o_workorder_lot input:value('SN003')",
        },
        {
            trigger: "button:contains('Validate')",
            run: "click",
        },
        {
            content: "Check that 3 registrations were made",
            trigger: ".accordion button:contains('Instructions'):contains(3/3)",
        },
    ],
});

registry.category("web_tour.tours").add("test_under_consume_materials_in_shopfloor", {
    steps: () => [
        {
            content: "Make sure workcenter is available",
            trigger: ".form-check:has(input[name='Lovely Workcenter'])",
            run: "click",
        },
        {
            trigger: ".form-check:has(input[name='Lovely Workcenter'])",
        },
        {
            trigger: "button:contains('Confirm')",
            run: "click",
        },
        {
            content: "Check that we are in the MO view",
            trigger: ".o_mrp_display_records button:contains('Lovely Workcenter')",
        },
        {
            content: "Swap to the WO view of the Lovely Workcenter",
            trigger: "button.btn-light:contains('Lovely Workcenter')",
            run: "click",
        },
        {
            content: "Open register production",
            trigger: ".accordion button:contains('Instructions')",
            run: "click",
        },
        {
            trigger: ".modal-header .modal-title:contains('Register component')",
        },
        {
            trigger: ".o_field_widget[name='qty_done'] input",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='qty_done'] input",
            run: "edit 3",
        },
        {
            trigger: ".modal-header",
            run: "click",
        },
        {
            trigger: "button:contains('Continue consumption')",
            run: "click",
        },
        {
            trigger: "span[name='component_remaining_qty']:contains('7.00')",
        },
        {
            trigger: ".o_field_widget[name='qty_done'] input",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='qty_done'] input",
            run: "edit 2",
        },
        {
            trigger: ".modal-header",
            run: "click",
        },
        {
            trigger: "button:contains('Validate')",
            run: "click",
        },
        {
            content: "Check that the componenet registration has been completed",
            trigger: ".btn:contains('Mark as Done')",
        },
    ],
});

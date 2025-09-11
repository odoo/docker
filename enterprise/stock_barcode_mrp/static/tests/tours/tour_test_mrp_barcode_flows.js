/** @odoo-module */

import * as helper from '@stock_barcode/../tests/tours/tour_helper_stock_barcode';
import { registry } from "@web/core/registry";
import { stepUtils } from '@stock_barcode/../tests/tours/tour_step_utils';

registry.category("web_tour.tours").add('test_immediate_receipt_kit_from_scratch_with_tracked_compo', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan kit_lot',
    },
    {
        trigger: '.o_barcode_line:contains("Kit Lot") .o_edit',
        run: "click",
    },
    {
        trigger: 'button.o_digipad_increment',
        run: "click",
    },
    {
        trigger: '.o_save',
        run: "click",
    },
    {
        trigger: '.o_barcode_line:contains("Kit Lot") .o_add_quantity',
        run: "click",
    },
    {
        trigger: '.o_barcode_line:contains("Kit Lot") .qty-done:contains("3")',
        run: 'scan simple_kit',
    },
    {
        trigger: '.o_barcode_line:contains("Simple Kit")',
    },
    {
        trigger: '.btn.o_validate_page',
        run: "click",
    },
    {
        trigger: '.o_notification_bar.bg-danger',
    },
    {
        trigger: '.o_barcode_line:contains("Compo Lot")',
        run: function() {
            helper.assertLinesCount(4);
            const [ kit_lot_compo01, simple_kit_compo01, simple_kit_compo02, kit_lot_compo_lot ] = document.querySelectorAll('.o_barcode_line');
            helper.assertLineProduct(kit_lot_compo01, 'Compo 01');
            helper.assertLineProduct(kit_lot_compo_lot, 'Compo Lot');
            helper.assertLineProduct(simple_kit_compo01, 'Compo 01');
            helper.assertLineProduct(simple_kit_compo02, 'Compo 02');
        }
    },
    {
        trigger: '.o_barcode_line:contains("Compo Lot")',
        run: 'scan compo_lot',
    },
    {
        trigger: '.o_barcode_line.o_selected div[name="lot"] .o_next_expected',
        run: 'scan super_lot',
    },
    ...stepUtils.validateBarcodeOperation('.o_line_lot_name:contains("super_lot")'),
]});

registry.category("web_tour.tours").add('test_planned_receipt_kit_from_scratch_with_tracked_compo', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: 'scan kit_lot',
    },
    {
        trigger: '.o_barcode_line:contains("Kit Lot") .o_edit',
        run: "click",
    },
    {
        trigger: 'button.o_digipad_increment',
        run: "click",
    },
    {
        trigger: '.o_save',
        run: "click",
    },
    {
        trigger: '.o_barcode_line:contains("Kit Lot") .o_add_quantity',
        run: "click",
    },
    {
        trigger: '.o_barcode_line:contains("Kit Lot") .qty-done:contains("3")',
        run: 'scan simple_kit',
    },
    {
        trigger: '.o_barcode_line:contains("Simple Kit")',
    },
    {
        trigger: '.btn.o_validate_page',
        run: "click",
    },
    {
        trigger: ".o_notification_bar.bg-danger",
    },
    {
        trigger: '.o_barcode_line:contains("Compo Lot")',
        run: function() {
            helper.assertLinesCount(4);
            const [ kit_lot_compo01, simple_kit_compo01, simple_kit_compo02, kit_lot_compo_lot ] = document.querySelectorAll('.o_barcode_line');
            helper.assertLineProduct(kit_lot_compo01, 'Compo 01');
            helper.assertLineProduct(kit_lot_compo_lot, 'Compo Lot');
            helper.assertLineProduct(simple_kit_compo01, 'Compo 01');
            helper.assertLineProduct(simple_kit_compo02, 'Compo 02');
        }
    },
    {
        trigger: '.o_barcode_line:contains("Compo Lot")',
        run: "click",
    },
    {
        trigger: '.o_selected:contains("Compo Lot")',
        run: 'scan super_lot',
    },
    ...stepUtils.validateBarcodeOperation('.o_line_lot_name:contains("super_lot")'),
]});

registry.category("web_tour.tours").add('test_process_confirmed_mo', { steps: () => [
    {
        trigger: '.o_kanban_record_title:contains("Manufacturing")',
        run: "click",
    },
    {
        trigger: '.o_kanban_record:contains("Final Product")',
        run: "click",
    },
    {
        trigger: '.o_barcode_line_title:contains("Compo 01")',
    },
    {
        trigger: '.o_header .o_barcode_line_title:contains("Final Product")',
        run: "click",
    },
    {
        trigger: 'button[name="produceButton"]',
        run: "click",
    },
    {
        trigger: '.o_line_completed',
    },
    {
        trigger: '.o_header_completed .qty-done:contains("1")',
        run: "click",
    },
    {
        trigger: 'div[data-barcode="compo01"] .qty-done:contains("2")',
        run: "click",
    },
    {
        trigger: '.o_scan_message.o_scan_validate',
    },
    {
        trigger: '.o_validate_page',
        run: "click",
    },
    {
        trigger: '.o_notification_bar.bg-success',
    },
]});

registry.category("web_tour.tours").add('test_barcode_production_create', { steps: () => [
    {
        trigger: ".o_kanban_record_title:contains('Manufacturing')",
        run: "click",
    },
    {
        trigger: ".o-kanban-button-new",
        run: "click",
    },
    // Scans final product, it should create the header line for this product.
    {
        trigger: ".o_scan_message.o_scan_product",
    },
    {
        trigger: '.o_title:contains("New")',
        run: 'scan final',
    },
    {
        trigger: ".o_barcode_line.o_header",
        run: function() {
            helper.assert(helper.getLines().length, 1, "The header's line should be the only line");
            const headerLine = helper.getLine();
            helper.assertLineProduct(headerLine, "Final Product");
            helper.assertLineQty(headerLine, "0/1");
        }
    },
    // Scans components, it should create a line for the component, then increases its quantity.
    { trigger: ".o_scan_message.o_scan_component", run: "scan compo01" },
    {
        trigger: ".o_barcode_line.o_selected",
        run: function() {
            helper.assert(helper.getLines().length, 2);
            const headerLine = helper.getLine({ index: 0 });
            const componentLine = helper.getLine({ barcode: "compo01" });
            helper.assertLineQty(headerLine, "0/1");
            helper.assertLineQty(componentLine, "1");
        }
    },
    { trigger: ".o_barcode_client_action", run: 'scan compo01' },
    {
        trigger: ".o_barcode_line.o_selected .qty-done:contains('2')",
        run: function() {
            helper.assert(helper.getLines().length, 2);
            const headerLine = helper.getLine({ index: 0 });
            const componentLine = helper.getLine({ barcode: "compo01" });
            helper.assertLineQty(headerLine, "0/1");
            helper.assertLineQty(componentLine, "2");
        }
    },
    // Scans the final product again, it should increase the header line's quantity.
    { trigger: ".o_barcode_client_action", run: 'scan final' },
    {
        trigger: ".o_header_completed .qty-done:contains('1')",
        run: function() {
            helper.assert(helper.getLines().length, 2);
            const headerLine = helper.getLine({ index: 0 });
            helper.assertLineQty(headerLine, "1/1");
        }
    },
    { trigger: ".o_barcode_client_action", run: 'scan final' },
    {
        trigger: ".o_header_completed .qty-done:contains('2')",
        run: function() {
            helper.assert(helper.getLines().length, 2);
            const headerLine = helper.getLine({ index: 0 });
            helper.assertLineQty(headerLine, "2/1");
        }
    },
    ...stepUtils.validateBarcodeOperation(".o_scan_message.o_scan_validate"),
]});

registry.category("web_tour.tours").add("test_barcode_production_create_bom", { steps: () => [
    // Creates a new production from the Barcode App.
    {
        trigger: ".o_kanban_record_title:contains('Manufacturing')",
        run: "click",
    },
    {
        trigger: ".o-kanban-button-new",
        run: "click",
    },
    // Scans a product with BoM, it should add it as the final product and add a line for each components.
    {
        trigger: ".o_scan_message.o_scan_product",
    },
    {
        trigger: ".o_title:contains('New')",
        run: "scan final",
    },
    {
        trigger: ".o_barcode_line.o_header",
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines.length, 3, "The header line + 2 components lines");
            const [headerLine, componentLine1, componentLine2] = lines;
            helper.assertLineProduct(headerLine, "Final Product");
            helper.assertLineQty(headerLine, "0/1");
            helper.assertLineProduct(componentLine1, "Compo 01");
            helper.assertLineQty(componentLine1, "0/2");
            helper.assertLineProduct(componentLine2, "Compo 02");
            helper.assertLineQty(componentLine2, "0/3");
        }
    },
    // Scans again the finished product, it should increase its quantity and its components' quantity aswell.
    { trigger: ".o_barcode_client_action", run: 'scan final' },
    {
        trigger: ".o_barcode_line.o_header.o_header_completed",
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines.length, 3, "The header line + 2 components lines");
            const [headerLine, componentLine1, componentLine2] = lines;
            helper.assertLineProduct(headerLine, "Final Product");
            helper.assertLineQty(headerLine, "1/1");
            helper.assertLineProduct(componentLine1, "Compo 01");
            helper.assertLineQty(componentLine1, "2/2");
            helper.assertLineProduct(componentLine2, "Compo 02");
            helper.assertLineQty(componentLine2, "3/3");
        }
    },
    // Scans two more times the final product and validate the production.
    { trigger: ".o_barcode_client_action", run: 'scan final' },
    { trigger: ".o_barcode_client_action", run: 'scan final' },
    {
        trigger: ".o_barcode_line.o_header .qty-done:contains(3)",
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines.length, 3, "The header line + 2 components lines");
            const [headerLine, componentLine1, componentLine2] = lines;
            helper.assertLineProduct(headerLine, "Final Product");
            helper.assertLineQty(headerLine, "3/1");
            helper.assertLineProduct(componentLine1, "Compo 01");
            helper.assertLineQty(componentLine1, "6/2");
            helper.assertLineProduct(componentLine2, "Compo 02");
            helper.assertLineQty(componentLine2, "9/3");
        }
    },
    ...stepUtils.validateBarcodeOperation(".o_scan_message.o_scan_validate"),
]})

registry.category("web_tour.tours").add('test_barcode_production_create_tracked_bom', { steps: () => [
    {
        trigger: '.o_kanban_record_title:contains("Manufacturing")',
        run: "click",
    },
    {
        trigger: '.o-kanban-button-new',
        run: "click",
    },
    {
        trigger: ".o_scan_message.o_scan_product",
    },
    {
        trigger: '.o_title:contains("New")',
        run: 'scan final_lot',
    },
    {
        trigger: ".o_scan_message.o_scan_component",
    },
    {
        trigger: '.o_header .o_barcode_line_title:contains("Final Product2")',
        run: "click",
    },
    {
        trigger: 'div[data-barcode="compo_lot"] .o_barcode_scanner_qty:contains("2")',
    },
    {
        trigger: 'div[data-barcode="compo01"] .o_barcode_scanner_qty:contains("2")',
        run: "click",
    },
    {
        trigger: '.o_header .o_line_button.o_edit',
        run: "click",
    },
    {
        trigger: '.o_button_qty_done',
        run: "click",
    },
    {
        trigger: 'div[name="product_qty"] .o_input',
        run: "edit 3",
    },
    {
        trigger: 'button[name="change_prod_qty"]',
        run: "click",
    },
    {
        trigger: 'span[name="product_uom_qty"]:contains("3")',
    },
    {
        trigger: '.o_save',
        run: "click",
    },
    {
        trigger: '.o_header .o_barcode_scanner_qty:contains("3")',
    },
    {
        trigger: 'div[data-barcode="compo01"] .o_barcode_scanner_qty:contains("3")',
        run: "click",
    },
    {
        trigger: ".o_scan_message.o_scan_component",
    },
    {
        trigger: 'div[data-barcode="compo_lot"] .o_barcode_scanner_qty:contains("3")',
        run: 'scan compo01',
    },
    {
        trigger: 'div[data-barcode="compo01"].o_selected .qty-done:contains("1")',
        run: 'scan compo01',
    },
    {
        trigger: 'div[data-barcode="compo01"].o_selected .qty-done:contains("2")',
        run: 'scan compo01',
    },
    {
        trigger: 'div[data-barcode="compo01"].o_selected.o_line_completed .qty-done:contains("3")',
        run: 'scan compo_lot',
    },
    {
        trigger: '.o_scan_message.o_scan_lot',
        run: 'scan lot01',
    },
    {
        trigger: 'div[data-barcode="compo_lot"].o_selected .qty-done:contains("1")',
        run: 'scan lot01',
    },
    {
        trigger: 'div[data-barcode="compo_lot"].o_selected .qty-done:contains("2")',
        run: 'scan lot01',
    },
    {
        trigger:
            'div[data-barcode="compo_lot"].o_selected.o_line_completed .qty-done:contains("3")',
    },
    {
        trigger: '.o_by_products',
        run: "click",
    },
    {
        trigger: '.o_add_byproduct',
        run: function() {
            const viewByProductsBtn = document.querySelectorAll('.o_by_products');
            const addLineBtn = document.querySelectorAll('.o_add_line');
            const produceBtn = document.querySelectorAll('.o_validate_page');
            helper.assert(viewByProductsBtn.length, 0, 'By product buttons must be hidden');
            helper.assert(addLineBtn.length, 0, 'Add line button must be hidden');
            helper.assert(produceBtn.length, 0, 'Produce button must be hidden');
        }
    },
    {
        trigger: '.o_add_byproduct',
        run: "click",
    },
    {
        trigger: 'div[name="product_id"] .o_input',
        run: "edit By Product",
    },
    {
        trigger: '.dropdown-item:contains("By Product")',
        run: "click",
    },
    {
        trigger: 'div[name="qty_done"] .o_input',
        run() {
            //input type number not supported by tour helpers.
            // It would work if the clipboard was mocked in tours the same way it is in unit tests.
            this.anchor.value = 2;
            this.anchor.dispatchEvent(new InputEvent("input", { bubbles: true }));
        },
    },
    {
        trigger: '.o_save',
        run: "click",
    },
    {
        trigger: '.qty-done:contains("2")',
    },
    {
        trigger: '.o_barcode_line_title:contains("By Product")',
        run: "click",
    },
    {
        trigger: '.o_save_byproduct',
        run: "click",
    },
    {
        trigger: '.o_scan_message.o_scan_final_product',
        run: 'scan final_lot',
    },
    {
        trigger: '.o_scan_message.o_scan_lot',
        run: 'scan lot02',
    },
    {
        trigger: '.o_header .qty-done:contains("1")',
        run: 'scan lot02',
    },
    {
        trigger: '.o_header .qty-done:contains("2")',
        run: 'scan lot02',
    },
    {
        trigger: ".o_header_completed",
    },
    {
        trigger: '.o_scan_message.o_scan_validate',
        run: "click",
    },
    ...stepUtils.validateBarcodeOperation(".o_validate_page.btn-primary"),
]});

registry.category("web_tour.tours").add("test_barcode_production_reserved_from_multiple_locations", { steps: () => [
    {
        trigger: ".o_barcode_client_action",
        run: function() { // Check all lines are here (header + 4 compos)
            const lines = helper.getLines();
            helper.assert(lines.length, 5, "The header line + 4 components lines");
            const [headerLine, line1, line2, line3, line4] = lines;
            helper.assertLineProduct(headerLine, "Final Product");
            helper.assertLineQty(headerLine, "0/3");
            helper.assertLineProduct(line1, "Compo 01");
            helper.assertLineSourceLocation(line1, "WH/Stock/Section 1")
            helper.assertLineQty(line1, "0/1");
            helper.assertLineProduct(line2, "Compo 01");
            helper.assertLineQty(line2, "0/2");
            helper.assertLineSourceLocation(line2, "WH/Stock/Section 2")
            helper.assertLineProduct(line3, "Compo 01");
            helper.assertLineQty(line3, "0/2");
            helper.assertLineSourceLocation(line3, "WH/Stock/Section 3")
            helper.assertLineProduct(line4, "Compo 01");
            helper.assertLineQty(line4, "0/1");
            helper.assertLineSourceLocation(line4, "WH/Stock/Section 4")
        }
    },
    // Scans Shelf 1, Comp 01, Shelf 2 and Comp 01 again.
    {
        trigger: ".o_scan_message.o_scan_src",
        run: "scan LOC-01-01-00",
    },
    {
        trigger: ".o_scan_message.o_scan_component",
        run: "scan compo01",
    },
    {
        trigger: ".o_scan_message.o_scan_component",
    },
    {
        trigger: ".o_barcode_line.o_selected.o_line_completed",
        run: "scan LOC-01-02-00",
    },
    {
        trigger: ".o_barcode_location_line[data-location='WH/Stock/Section 2'].text-bg-800",
        run: "scan compo01",
    },
    // Scans the final product a first time.
    {
        trigger: ".o_barcode_location_line[data-location='WH/Stock/Section 2'] + .o_barcode_line.o_selected",
        run: "scan final",
    },
    {
        trigger: ".o_barcode_location_line[data-location='WH/Stock/Section 2'] + .o_barcode_line:not(.o_selected)",
        run: function() { // Check all lines are here (header + 4 compos)
            const lines = helper.getLines();
            helper.assert(lines.length, 5, "The header line + 4 components lines");
            const [headerLine, line1, line2, line3, line4] = lines;
            helper.assertLineProduct(headerLine, "Final Product");
            helper.assertLineQty(headerLine, "1/3");
            helper.assertLineProduct(line1, "Compo 01");
            helper.assertLineSourceLocation(line1, "WH/Stock/Section 1")
            helper.assertLineQty(line1, "1/1");
            helper.assertLineProduct(line2, "Compo 01");
            helper.assertLineQty(line2, "1/2");
            helper.assertLineSourceLocation(line2, "WH/Stock/Section 2")
            helper.assertLineProduct(line3, "Compo 01");
            helper.assertLineQty(line3, "0/2");
            helper.assertLineSourceLocation(line3, "WH/Stock/Section 3")
            helper.assertLineProduct(line4, "Compo 01");
            helper.assertLineQty(line4, "0/1");
            helper.assertLineSourceLocation(line4, "WH/Stock/Section 4")
        }
    },

    // Scans each locations and their remaining components.
    { trigger: ".o_barcode_client_action", run: "scan LOC-01-02-00" },
    {
        trigger: ".o_barcode_location_line[data-location='WH/Stock/Section 2'].text-bg-800",
        run: "scan compo01",
    },
    { trigger: ".o_barcode_line.o_selected.o_line_completed", run: "scan shelf3" },
    {
        trigger: ".o_barcode_location_line[data-location='WH/Stock/Section 3'].text-bg-800",
        run: "scan compo01",
    },
    { trigger: ".o_barcode_line.o_selected:not(.o_line_completed)", run: "scan compo01" },
    { trigger: ".o_barcode_line.o_selected.o_line_completed", run: "scan shelf4" },
    {
        trigger: ".o_barcode_location_line[data-location='WH/Stock/Section 4'].text-bg-800",
        run: "scan compo01",
    },

    // Scans 2 more times the final product to complete the production, then validates it.
    { trigger: ".o_barcode_line.o_selected.o_line_completed", run: "scan final" },
    { trigger: ".o_barcode_client_action", run: "scan final" },
    {
        trigger: ".o_scan_message.o_scan_validate",
        run: function() { // Check all lines are here (header + 4 compos)
            const lines = helper.getLines();
            helper.assert(lines.length, 5, "The header line + 4 components lines");
            const [headerLine, line1, line2, line3, line4] = lines;
            helper.assertLineProduct(headerLine, "Final Product");
            helper.assertLineQty(headerLine, "3/3");
            helper.assertLineProduct(line1, "Compo 01");
            helper.assertLineSourceLocation(line1, "WH/Stock/Section 1")
            helper.assertLineQty(line1, "1/1");
            helper.assertLineProduct(line2, "Compo 01");
            helper.assertLineQty(line2, "2/2");
            helper.assertLineSourceLocation(line2, "WH/Stock/Section 2")
            helper.assertLineProduct(line3, "Compo 01");
            helper.assertLineQty(line3, "2/2");
            helper.assertLineSourceLocation(line3, "WH/Stock/Section 3")
            helper.assertLineProduct(line4, "Compo 01");
            helper.assertLineQty(line4, "1/1");
            helper.assertLineSourceLocation(line4, "WH/Stock/Section 4")
        }
    },

    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_barcode_production_scan_other_than_reserved', { steps: () => [
    {
        trigger: ".o_barcode_client_action",
        run: function() { // Check all lines are here (header + 2 compos)
            const lines = helper.getLines();
            helper.assert(lines.length, 3, "The final product line + 2 components lines");
            const [headerLine, line1, line2] = lines;
            helper.assertLineProduct(headerLine, "Final Product2");
            helper.assertLineQty(headerLine, "0/2");
            helper.assertLineProduct(line1, "Compo 01");
            helper.assertLineSourceLocation(line1, "WH/Stock")
            helper.assertLineQty(line1, "0/2");
            helper.assertLineProduct(line2, "Compo Lot");
            helper.assertLineQty(line2, "0/2");
            helper.assertLineSourceLocation(line2, "WH/Stock")
        }
    },
    // scan the tracked comp and the non-reserved lot in the same loc as reserved ones
    {
        trigger: ".o_scan_message.o_scan_src",
        run: "scan LOC-01-00-00",
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan compo_lot'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot_02'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan lot_02'
    },

    // Unfold grouped lines for tracked component
    {
        trigger: '.o_line_button.o_toggle_sublines',
        run: "click",
    },
    {
        trigger: '.o_barcode_client_action:contains("lot_01")',
        run: function() {
            helper.assertLinesCount(3);
            helper.assertSublinesCount(2);
            const [ line1, line2 ] = helper.getSublines();
            helper.assert(line1.querySelector('.o_line_lot_name').innerText, "lot_01");
            helper.assert(line1.querySelector('.qty-done').innerText, "0");
            helper.assert(line2.querySelector('.o_line_lot_name').innerText, "lot_02");
            helper.assert(line2.querySelector('.qty-done').innerText, "2");
        }
    },
    // scan the not tracked component from a different location (shelf1) than the reserved
    {
        trigger: ".o_barcode_client_action",
        run: "scan LOC-01-01-00",
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan compo01'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan compo01'
    },
    // scan the final product + its lot name
    {
        trigger: '.o_barcode_client_action',
        run: 'scan final_lot'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan finished_lot'
    },
    {
        trigger: '.o_barcode_client_action',
        run: 'scan finished_lot'
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add("test_barcode_production_component_no_stock", { steps: () => [
    // Creates a new production from the Barcode App.
    {
        trigger: ".o_kanban_record_title:contains('Manufacturing')",
        run: "click",
    },
    {
        trigger: ".o-kanban-button-new",
        run: "click",
    },
    // Scans a product with BoM, it should add it as the final product and add a line for the component.
    {
        trigger: ".o_scan_message.o_scan_product",
    },
    {
        trigger: ".o_title:contains('New')",
        run: "scan final",
    },
    /**
     * Scans the final product again, it should increment the final product qty done, but leaves component line
     * as it is, since its manual consumption (nothing reserved)
     */
    {
        trigger: ".o_scan_message.o_scan_component",
        run: "scan final",
    },
    {
        trigger: ".o_header_completed .qty-done:contains('1')",
        run: function() {
            helper.assert(helper.getLines().length, 2);
            const componentLine = helper.getLine({ barcode: "compo01" });
            helper.assertLineQty(componentLine, "2");
        }
    },
    {
        trigger: ".o_scan_message.o_scan_validate",
        run: "scan final",
    },
    {
        trigger: ".o_header_completed .qty-done:contains('2')",
        run: "scan final",
    },
    {
        trigger: ".o_header_completed .qty-done:contains('3')",
        run: "click",
    },
    {
        trigger: ".o_validate_page",
        run: "click",
    },
    // Confirm consumption warning
    {
        trigger: "button[name='action_confirm']",
        run: "click",
    },
    {
        trigger: ".o_notification_bar.bg-success",
    },
]});

registry.category("web_tour.tours").add('test_mo_scrap_digipad_view', { steps: () => [
    {
        trigger: ".o_barcode_actions",
        run: "click",
    },
    {
        trigger: ".o_barcode_settings",
        run: "click",
    },
    {
        trigger: ".o_scrap",
        run: "click",
    },
    {
        trigger: ".o_qty_done_field_not_completed",
        run: function() {
            const digipadView = document.querySelector(".o_digipad_widget");
            helper.assert(Boolean(digipadView), true, "Scrap view should use the digipad widget.");
        },
    },
]});

registry.category("web_tour.tours").add('test_barcode_production_components_reservation_state_reserved', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: () => {
            helper.assertLinesCount(2);
        }
    },
]});

registry.category("web_tour.tours").add('test_barcode_production_components_reservation_state_unreserved', { steps: () => [
    {
        trigger: '.o_barcode_client_action',
        run: () => {
            helper.assertLinesCount(1);
        }
    },
]});

registry.category("web_tour.tours").add("test_barcode_production_add_scrap", { steps: () => [
    // Creates a new production from the Barcode App.
    {
        trigger: ".o_kanban_record_title:contains('Manufacturing')",
        run: "click",
    },
    {
        trigger: ".o-kanban-button-new",
        run: "click",
    },
    // Scans a product with BoM, it should add it as the final product and add a line for each components.
    {
        trigger: ".o_scan_message.o_scan_product",
    },
    {
        trigger: ".o_title:contains('New')",
        run: "scan final",
    },
    {
        trigger: ".o_barcode_line.o_header",
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines.length, 3, "The header line + 2 components lines");
            const [headerLine, componentLine1, componentLine2] = lines;
            helper.assertLineProduct(headerLine, "Final Product");
            helper.assertLineQty(headerLine, "0/1");
            helper.assertLineProduct(componentLine1, "Compo 01");
            helper.assertLineQty(componentLine1, "0/1");
            helper.assertLineProduct(componentLine2, "Compo 02");
            helper.assertLineQty(componentLine2, "0/1");
        }
    },
    // Add a Scrap product
    {
        trigger: ".o_barcode_client_action",
        run: "scan OBTSCRA",
    },
    {
        trigger: "input#product_id_0",
        run: "edit Compo 01",
    },
    {
        trigger: '.dropdown-item:contains("Compo 01")',
        run: "click",
    },
    {
        trigger: 'button[name="action_validate"]',
        run: "click",
        // Alternatively, we may have triggered this by scanning OBTVALI (once focus is not on an editable input tag !)
        // However, there's still a bug such that OBTVALI will also validate the MO in addition to the scrap form...
    },
    // Ensure adding Compo 01 as a scrap product didn't add it as an used component
    {
        trigger: ".o_barcode_line.o_header",
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines.length, 3, "The header line + 2 components lines");
            const componentLine1 = lines[1];
            helper.assertLineProduct(componentLine1, "Compo 01");
            helper.assertLineQty(componentLine1, "0/1");
        }
    },
    // Further assertions are done server-side as scrapped products aren't shown in barcode interface
]});

registry.category("web_tour.tours").add("test_barcode_production_add_byproduct", { steps: () => [
    // Creates a new production from the Barcode App.
    {
        trigger: ".o_kanban_record_title:contains('Manufacturing')",
        run: "click",
    },
    {
        trigger: ".o-kanban-button-new",
        run: "click",
    },
    //Add Bom Product
    {
        trigger: ".o_scan_message.o_scan_product",
    },
    {
        trigger: ".o_title:contains('New')",
        run: "scan final",
    },

    // Add a By-Product
    {
        trigger: "button.o_by_products",
        run: "click",
    },
    {
        trigger: ".o_barcode_client_action",
        run: "scan byproduct",
    },
    {
        trigger: ".o_barcode_line",
        run: function() {
            helper.assertLinesCount(1)
        }
    },
    // Check `lot_id` field is not displayed for untracked by-product.
    { trigger: ".o_barcode_line .o_edit", run: "click" },
    {
        trigger: ".o_form_view_container",
        run: () => {
            const lotField = document.querySelector(".o_field_widget[name='lot_id'] input");
            helper.assert(Boolean(lotField), false, "lot_id should not be visible");
        }
    },
    { trigger: ".o_discard", run: "click" },
    { trigger: ".o_add_byproduct" },
    // Try (unsuccesfully) to add the final product as a byproduct through scan
    {
        trigger: ".o_barcode_client_action",
        run: 'scan final'
    },
    {
        trigger: ".o_notification_title:contains('Product not Allowed')",
        run: "click",
    },
    {
        trigger: ".o_barcode_line",
        run: function() {
            helper.assertLinesCount(1)
        }
    },
    {
        trigger: ".o_barcode_line",
        run: function() {
            const lines = helper.getLines();
            helper.assert(lines.length, 1, "The 'By Product' Line'");
            const [byProductLine] = lines;
            helper.assertLineProduct(byProductLine, "By Product");
            helper.assertLineQty(byProductLine, "1");
        }
    },
    // Add tracked product (Compo Lot) as a by-product.
    { trigger: ".o_barcode_client_action", run: "scan compo_lot" },
    { trigger: ".o_barcode_line.o_selected div[name='lot'] .o_next_expected" },
    { trigger: ".o_barcode_line.o_selected .o_edit", run: "click" },
    {
        trigger: ".o_form_view_container",
        run: () => {
            const lotField = document.querySelector(".o_field_widget[name='lot_id'] input");
            helper.assert(Boolean(lotField), true, "lot_id should be visible");
            helper.assert(lotField.value, "", "The added by-product should have no lot yet");
        }
    },
    { trigger: ".o_field_widget[name=qty_done] input", run: "clear" },
    { trigger: ".o_field_widget[name=qty_done] input", run: "edit 2" },
    // Check we can create a new lot for by-product.
    { trigger: ".o_field_widget[name=lot_id] input", run: "clear" },
    { trigger: ".o_field_widget[name=lot_id] input", run: "edit byprod_lot_001" },
    { trigger: ".dropdown-item:contains('byprod_lot_001')", run: "click" },
    { trigger: ".o-autocomplete input:last-child"},
    { trigger: '.o_save', run: "click" },
    // Validate by-products and then validate the manufacturing operation.
    {
        trigger: '.o_save_byproduct',
        run: 'click',
    },
    ...stepUtils.validateBarcodeOperation(),
]});

registry.category("web_tour.tours").add('test_split_line_on_exit_for_production', { steps: () => [
    // Opens the manufacturing order and check its lines.
    { trigger: ".o_stock_barcode_main_menu", run: "scan production_split_line_on_exit" },
    {
        trigger: ".o_barcode_client_action",
        run: () => {
            helper.assertLinesCount(3);
            helper.assertLineProduct(0, "Final Product");
            helper.assertLineQty(0, "0/2");
            helper.assertLineProduct(1, "product1");
            helper.assertLineQty(1, "0/4");
            helper.assertLineProduct(2, "product2");
            helper.assertLineQty(2, "0/2");
        }
    },
    // Scans 1x product2 then goes back to the main menu.
    { trigger: ".o_barcode_client_action", run: "scan product2" },
    {
        trigger: ".o_barcode_line.o_selected",
    },
    {
        trigger: "button.o_exit",
        run: "click",
    },
    // Reopens the production => product2 line should be split in two.
    { trigger: ".o_stock_barcode_main_menu", run: "scan production_split_line_on_exit" },
    {
        trigger: ".o_barcode_client_action",
        run: () => {
            helper.assertLinesCount(4);
            helper.assertLineProduct(0, "Final Product");
            helper.assertLineQty(0, "0/2");
            helper.assertLineProduct(1, "product1");
            helper.assertLineQty(1, "0/4");
            helper.assertLineProduct(2, "product2");
            helper.assertLineQty(2, "0/1");
            helper.assertLineProduct(3, "product2");
            helper.assertLineQty(3, "1/1");
        }
    },
    // Scans 3x product1 then goes back again on the main menu.
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    { trigger: ".o_barcode_client_action", run: "scan product1" },
    {
        trigger: ".o_barcode_line.o_selected .qty-done:contains('3')",
    },
    {
        trigger: "button.o_exit",
        run: "click",
    },
    // Re-opens the MO and checks lines.
    { trigger: ".o_stock_barcode_main_menu", run: "scan production_split_line_on_exit" },
    {
        trigger: ".o_barcode_client_action",
        run: () => {
            helper.assertLinesCount(5);
            helper.assertLineProduct(0, "Final Product");
            helper.assertLineQty(0, "0/2");
            helper.assertLineProduct(1, "product1");
            helper.assertLineQty(1, "0/1");
            helper.assertLineProduct(2, "product2");
            helper.assertLineQty(2, "0/1");
            helper.assertLineProduct(3, "product1");
            helper.assertLineQty(3, "3/3");
            helper.assertLineProduct(4, "product2");
            helper.assertLineQty(4, "1/1");
        }
    },
]});

registry.category("web_tour.tours").add("test_barcode_production_component_different_uom", { steps: () => [
        // Creates a new production from the Barcode App.
        {
            trigger: ".o_kanban_record_title:contains('Manufacturing')",
            run: "click",
        },
        {
            trigger: ".o-kanban-button-new",
            run: "click",
        },
        // Scans a product with BoM, it should add it as the final product and add a line for the component.
        {
            trigger: ".o_barcode_client_action",
            run: "scan final",
        },
        {
            trigger: "button[name='produceButton']",
            run: "click",
        },
        {
            trigger: ".o_header_completed",
            run: () => {
                helper.assertLineQty(1, "1 kg");
            }
        }
    ]
});

registry.category("web_tour.tours").add('test_picking_product_with_kit_and_packaging', { steps: () => [
        { trigger: '.btn.o_validate_page', run: 'click' }
    ]
});

registry.category("web_tour.tours").add('test_multi_company_manufacture_creation_in_barcode', { steps: () => [
        // test scan
        { trigger: '.o_stock_barcode_main_menu', run: 'scan company2_mrp_operation' },
        { trigger: '.o_barcode_client_action', run: 'scan final' },
        { trigger: '.o_add_quantity', run: 'click' },
        { trigger: '.btn.o_validate_page', run: 'click' },
        // test form
        { trigger: '.o_stock_barcode_main_menu', run: 'scan company2_mrp_operation' },
        { trigger: '.btn.o_add_line', run: 'click' },
        { trigger: 'div[name="product_id"]', run: 'click' },
        { trigger: 'div[name="product_id"] .o_input', run: 'edit final' },
        { trigger: '.dropdown-item:contains("final")', run: 'click' },
        { trigger: '.btn.o_save', run: 'click' },
        { trigger: '.btn.o_validate_page', run: 'click' },
        { trigger: '.o_stock_barcode_main_menu' }
    ]
});

registry.category("web_tour.tours").add('test_multi_company_record_access_in_mrp_barcode', {
    steps: () => [
        { trigger: '.o_stock_barcode_main_menu', run: 'scan company_mrp_operation' },
        { trigger: '.o_barcode_client_action', run: 'scan second_company_product' },
        { trigger: '.btn.o_add_line', run: 'click' },
        { trigger: 'div[name="product_id"]', run: 'click' },
        { trigger: 'div[name="product_id"] .o_input', run: 'edit second company product' },
        { trigger: '.o_m2o_dropdown_option_create:first-child' },
        { trigger: '.btn.o_discard', run: 'click' },
        { trigger: '.btn.o_exit', run: 'click' },
        { trigger: '.o_stock_barcode_main_menu' }
    ]
});

registry.category("web_tour.tours").add('test_multi_company_record_access_in_mrp_barcode2', {
    steps: () => [
        { trigger: '.o_stock_barcode_main_menu', run: 'scan company2_mrp_operation' },
        { trigger: '.o_barcode_client_action', run: 'scan second_company_product' },
        { trigger: '.btn.o_add_quantity', run: 'click' },
        { trigger: '.btn.o_validate_page', run: 'click' },
        { trigger: '.o_stock_barcode_main_menu' },
    ]
});

registry.category("web_tour.tours").add('test_kit_bom_decomposition_keeps_location', {
    steps: () => [
        /* Test 1: two move lines
            same final product, same bom, different location */
        { trigger: '.o_stock_barcode_main_menu', run: 'scan test_kit_bom_decomposition_keeps_location_picking1' },
        { trigger: '.btn.o_add_line', run: 'click' },
        { trigger: '.o_input[placeholder="Product"]', run: 'click' },
        { trigger: '.o_input[placeholder="Product"]', run: 'edit final' },
        { trigger: '.dropdown-item:contains("Final Product")', run: 'click' },
        { trigger: '.o_input[placeholder="Destination Location"]', run: 'click' },
        { trigger: '.o_input[placeholder="Destination Location"]', run: 'edit LOC-01-01-00' },
        { trigger: '.dropdown-item:contains("Section 1")', run: 'click' },
        { trigger: '.btn.o_save', run: 'click' },
        { trigger: '.btn.o_add_line', run: 'click' },
        { trigger: '.o_input[placeholder="Product"]', run: 'click' },
        { trigger: '.o_input[placeholder="Product"]', run: 'edit final' },
        { trigger: '.dropdown-item:contains("Final Product")', run: 'click' },
        { trigger: '.o_input[placeholder="Destination Location"]', run: 'click' },
        { trigger: '.o_input[placeholder="Destination Location"]', run: 'edit LOC-01-02-00' },
        { trigger: '.dropdown-item:contains("Section 2")', run: 'click' },
        { trigger: '.btn.o_save', run: 'click' },
        { trigger: '.btn.o_validate_page', run: 'click' },
        { trigger: '.o_notification_body' },
        { trigger: '.btn.o_validate_page', run: 'click' },
        /* Test 2: two move lines
            different final product, different bom, different location */
        { trigger: '.o_stock_barcode_main_menu', run: 'scan test_kit_bom_decomposition_keeps_location_picking2' },
        { trigger: '.btn.o_add_line', run: 'click' },
        { trigger: '.o_input[placeholder="Product"]', run: 'click' },
        { trigger: '.o_input[placeholder="Product"]', run: 'edit final' },
        { trigger: '.dropdown-item:contains("Final Product")', run: 'click' },
        { trigger: '.o_input[placeholder="Destination Location"]', run: 'click' },
        { trigger: '.o_input[placeholder="Destination Location"]', run: 'edit LOC-01-01-00' },
        { trigger: '.dropdown-item:contains("Section 1")', run: 'click' },
        { trigger: '.btn.o_save', run: 'click' },
        { trigger: '.btn.o_add_line', run: 'click' },
        { trigger: '.o_input[placeholder="Product"]', run: 'click' },
        { trigger: '.o_input[placeholder="Product"]', run: 'edit final2' },
        { trigger: '.dropdown-item:contains("final2")', run: 'click' },
        { trigger: '.o_input[placeholder="Destination Location"]', run: 'click' },
        { trigger: '.o_input[placeholder="Destination Location"]', run: 'edit LOC-01-02-00' },
        { trigger: '.dropdown-item:contains("Section 2")', run: 'click' },
        { trigger: '.btn.o_save', run: 'click' },
        { trigger: '.btn.o_validate_page', run: 'click' },
        { trigger: '.o_notification_body'},
        { trigger: '.btn.o_validate_page', run: 'click' },
    ]
});

registry.category("web_tour.tours").add('test_always_backorder_mo', { steps: () => [
    { trigger: '.o_kanban_record_title:contains(Manufacturing)', run: 'click' },
    { trigger: '.o_kanban_record:contains(Final Product)', run: 'click' },
    { trigger: '.o_barcode_line.o_header .fa-pencil', run: 'click' },
    { trigger: '.o_digipad_increment', run: "click" },
    { trigger: '.btn.o_save', run: 'click' },
    { trigger: '.o_validate_page', run: 'click' },
    { trigger: '.o_notification_bar.bg-success' },
    { trigger: '.o_kanban_record:contains(Final Product)' },
]});

registry.category("web_tour.tours").add("test_backorder_partial_completion_save_sensible_split", {
    steps: () => [
        { trigger: ".o_stock_barcode_main_menu", run: "scan TBPCSNS mo" },
        {
            trigger:
                '.o_barcode_line:has(.o_barcode_line_title .o_product_label:contains("Final Product")) .o_edit',
            run: "click",
        },
        { trigger: "input", run: "clear" },
        { trigger: "input", run: "edit 5" },
        { trigger: ".o_save", run: "click" },
        {
            trigger:
                '.o_barcode_line:has(.o_barcode_line_title .o_product_label:contains("Compo 01")) .o_edit',
            run: "click",
        },
        { trigger: "input", run: "clear" },
        { trigger: "input", run: "edit 5" },
        { trigger: ".o_save", run: "click" },
        { trigger: ".o_barcode_line" },
        { trigger: ".o_exit", run: "click" },
        { trigger: ".o_stock_barcode_main_menu", run: "scan TBPCSNS mo" },
        { trigger: ".o_validate_page", run: "click" },
        { trigger: 'button[name="action_backorder"]', run: "click" },
        { trigger: ".o_notification_buttons" },
    ],
});

registry.category("web_tour.tours").add("test_barcode_mo_creation_in_mo2", {
    steps: () => [
        { trigger: "button.o_button_operations", run: "click" },
        { trigger: ".o_kanban_record_title:contains('MO2')", run: "click" },
        { trigger: ".o-kanban-button-new", run: "click" },
        {
            content: "Click on the button to add a product",
            trigger: "button.o_add_line",
            run: "click",
        },
        { trigger: "input#product_id_0", run: "edit Product4" },
        { trigger: ".ui-autocomplete a:contains('Product4')", run: "click" },
        { trigger: "button.o_save", run: "click" },
        { trigger: "button.o_validate_page:enabled", run: "click" },
        { trigger: ".o_notification_bar.bg-success" },
        { trigger: ".o_notification .o_notification_close", run: "click" },
        { trigger: "a[href='/odoo/barcode']", run: "click" },
        // Create a new MO by scanning the operation's barcode.
        { trigger: ".o_stock_barcode_main_menu", run: "scan MO2_BARCODE" },
        {
            content: "Click on the button to add a product",
            trigger: "button.o_add_line",
            run: "click",
        },
        { trigger: "input#product_id_0", run: "edit Product4" },
        { trigger: ".ui-autocomplete a:contains('Product4')", run: "click" },
        { trigger: "button.o_save", run: "click" },
        { trigger: "button.o_validate_page:enabled", run: "click" },
        { trigger: ".o_notification_bar.bg-success" },
    ],
});

registry.category("web_tour.tours").add("test_barcode_mo_creation_in_scan_mo2", {
    steps: () => [
        { trigger: ".o_kanban_record_title:contains('MO2')", run: "click" },
        { trigger: ".o-kanban-button-new", run: "click" },
        { trigger: ".o_barcode_client_action", run: "scan MO2_TEST_PRODUCT" },
        { trigger: "button.o_validate_page:enabled", run: "click" },
        { trigger: ".o_notification_bar.bg-success" },
    ],
});

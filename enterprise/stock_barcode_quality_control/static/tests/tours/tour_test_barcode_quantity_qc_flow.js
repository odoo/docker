import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_partial_quantity_check_fail", { steps: () => [
    {
        trigger: 'footer.o_barcode_control button.o_check_quality',
        run: 'click',
    },
    {
        trigger: '.modal-footer button.btn-danger:contains("fail")',
        run: 'click',
    },
    {
        trigger: '.modal-body input.o_input[id="qty_failed_0"]',
        run: 'edit 3'
    },
    {
        trigger: '.modal-body span.o_selection_badge:contains("WH/Stock/Section 1")',
        run: 'click'
    },
    {
        trigger: 'footer.modal-footer button.btn-primary:contains("Confirm")',
        run: 'click'
    },
    {
        trigger: 'body:not(:has(.modal))',
    },
    {
        trigger: 'header.o_barcode_header button.o_exit',
        run: 'click',
    }
]});

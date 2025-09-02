/* @odoo-module */

export const stepUtils = {
    confirmAddingUnreservedProduct() {
        return [
            {
                trigger: ".modal:not(.o_inactive_modal) .modal-title:contains(Add extra product?)",
            },
            {
                trigger: ".modal:not(.o_inactive_modal) .btn-primary",
                run: "click",
            },
            {
                trigger: "body:not(:has(.modal))",
            },
        ];
    },
    inputManuallyBarcode(barcode) {
        return [
            { trigger: '.o_barcode_actions', run: "click" },
            { trigger: 'input#manual_barcode', run: "click" },
            { trigger: 'input#manual_barcode', run: `edit ${barcode}` },
            { trigger: 'input#manual_barcode+button', run: "click" },
        ];
    },
    validateBarcodeOperation(trigger = ".o_barcode_client_action") {
        return [
            {
                trigger: "body:not(:has(.modal))",
            },
            {
                trigger,
                run: "scan OBTVALI",
            },
            {
                trigger: ".o_notification_bar.bg-success",
            },
        ];
    },
    discardBarcodeForm() {
        return [
            {
                isActive: ["auto"],
                content: "discard barcode form",
                trigger: ".o_discard",
                run: "click",
            },
            {
                isActive: ["auto"],
                content: "wait to be back on the barcode lines",
                trigger: ".o_add_line",
            },
        ];
    },
};

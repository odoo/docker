/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add("documents_account_tour", {
    url: "/odoo",
    steps: () => [
        {
    trigger: '.o_app[data-menu-xmlid="documents.menu_root"]',
    content: markup(_t("Want to become a <b>paperless company</b>? Let's discover Odoo Documents.")),
            tooltipPosition: "bottom",
        },
        {
    trigger: 'body:not(:has(.o-FileViewer)) img[src="https://img.youtube.com/vi/Ayab6wZ_U1A/0.jpg"]',
    content: markup(_t("Click on a thumbnail to <b>preview the document</b>.")),
            tooltipPosition: "bottom",
        },
        {
            isActive: ["auto"],
            trigger: '.o_documents_kanban',
        },
        {
    trigger: '[title="Close (Esc)"]',
    content: markup(_t("Click the cross to <b>exit preview</b>.")),
            tooltipPosition: "left",
        },
        {
            isActive: ["auto"],
            trigger: ".o_search_panel_label",
        },
        {
            // equivalent to '.o_search_panel_filter_value:contains('Inbox')' but language agnostic.
    trigger: '.o_search_panel_filter_value:eq(0)',
    content: markup(_t("Let's process documents in your Inbox.<br/><i>Tip: Use Tags to filter documents and structure your process.</i>")),
            tooltipPosition: "bottom",
        },
        {
            trigger: ".o_search_panel_filter_value:eq(0) .o_search_panel_label_title",
            run: "click",
        },
        {
            isActive: ["auto"],
            trigger: 'body:not(:has(.o-FileViewer)) .o_documents_kanban',
        },
        {
    trigger: '.o_kanban_record:contains(mail.png)',
    content: markup(_t("Click on a card to <b>select the document</b>.")),
            tooltipPosition: "bottom",
        },
        {
            // equivalent to '.o_inspector_rule:contains('Send to Legal') .o_inspector_trigger_rule' but language agnostic.
    trigger: '.o_inspector_rule[data-id="3"] .o_inspector_trigger_rule',
    content: markup(_t("Let's tag this mail as legal<br/> <i>Tips: actions can be tailored to your process, according to the workspace.</i>")),
            tooltipPosition: "bottom",
        },
        {
            isActive: ["auto"],
            trigger: ".o_documents_kanban",
        },
        {
            // the nth(0) ensures that the filter of the preceding step has been applied.
    trigger: '.o_kanban_record:nth(0):contains(Mails_inbox.pdf)',
    content: _t("Let's process this document, coming from our scanner."),
            tooltipPosition: "bottom",
        },
        {
            isActive: ["auto"],
            trigger: '[title="Mails_inbox.pdf"]',
        },
        {
    trigger: '.o_inspector_split',
    content: _t("As this PDF contains multiple documents, let's split and process in bulk."),
            tooltipPosition: "bottom",
        },
        {
            isActive: ["auto"],
            trigger: ".o_documents_pdf_canvas:nth(5)", // Makes sure that all the canvas are loaded.
        },
        {
    trigger: '.o_page_splitter_wrapper:nth(3)',
    content: markup(_t("Click on the <b>page separator</b>: we don't want to split these two pages as they belong to the same document.")),
            tooltipPosition: "right",
        },
        {
            isActive: ["auto"],
            trigger: ".o_documents_pdf_manager",
        },
        {
    trigger: '.o_documents_pdf_page_selector:nth(5)',
    content: markup(_t("<b>Deselect this page</b> as we plan to process all bills first.")),
            tooltipPosition: "left",
        },
        {
            isActive: ["auto"],
            trigger: ".o_documents_pdf_manager",
        },
        {
            // equivalent to '.o_pdf_manager_button:contains(Create Vendor Bill)' but language agnostic.
    trigger: '.o_pdf_manager_button:nth-last-child(2)',
    content: _t("Let's process these bills: turn them into vendor bills."),
            tooltipPosition: "bottom",
        },
        {
            isActive: ["auto"],
            trigger: ".o_documents_pdf_manager",
        },
        {
    trigger: '.o_documents_pdf_page_selector',
    content: markup(_t("<b>Select</b> this page to continue.")),
            tooltipPosition: "bottom",
        },
        {
            isActive: ["auto"],
            trigger: ".o_pdf_manager_button:not(:disabled)",
        },
        {
            // equivalent to '.o_pdf_manager_button:contains(Send to Legal)' but language agnostic.
    trigger: '.o_pdf_manager_button:nth-child(4)',
    content: _t("Send this letter to the legal department, by assigning the right tags."),
            tooltipPosition: "bottom",
        },
    ],
});

/** @odoo-module */

import { AbstractMacro } from "@knowledge/macros/abstract_macro";
import { pasteElements } from "@knowledge/macros/utils";

/**
 * Macro that will open the Full Composer Form view dialog in the Form view
 * context of a target record, and paste text content inside it. Does not
 * actually send the message.
 */
export class SendAsMessageMacro extends AbstractMacro {
    /**
     * @override
     * @returns {Array[Object]}
     */
    getSteps() {
        let sendMessageLastClickedEl = null;
        return [
            {
                // Search for the chatter button to send a message and make sure
                // that the composer is visible. Search in notebook tabs too.
                trigger: () => {
                    this.validatePage();
                    const el = this.getFirstVisibleElement(
                        ".o-mail-Chatter-sendMessage:not([disabled])"
                    );
                    if (el) {
                        if (el.classList.contains("active")) {
                            return el;
                        } else if (el !== sendMessageLastClickedEl) {
                            el.click();
                            sendMessageLastClickedEl = el;
                        }
                    } else {
                        this.searchInXmlDocNotebookTab("chatter");
                    }
                    return null;
                },
                action: () => {},
            },
            {
                // Open the full composer Form view Dialog.
                trigger: () => {
                    this.validatePage();
                    return this.getFirstVisibleElement(
                        ".o-mail-Composer-fullComposer:not([disabled])"
                    );
                },
                action: "click",
            },
            {
                // Paste the html data inside the message body.
                trigger: () => {
                    this.validatePage();
                    const dialog = this.getFirstVisibleElement(".o_dialog .o_mail_composer_form");
                    if (dialog) {
                        return this.getFirstVisibleElement(
                            dialog.querySelector('.o_field_html[name="body"] .odoo-editor-editable')
                        );
                    }
                    return null;
                },
                action: (el) => {
                    pasteElements(this.data.dataTransfer, el);
                },
            },
            {
                action: () => this.unblockUI(),
            },
        ];
    }
}

/**
 * Macro that will append content in the target record's html field in its Form
 * view. Does not trigger the save (field will be dirty).
 */
export class UseAsDescriptionMacro extends AbstractMacro {
    /**
     * @override
     * @returns {Array[Object]}
     */
    getSteps() {
        return [
            {
                // Ensure that the Form view is editable
                trigger: () => this.getFirstVisibleElement(".o_form_editable"),
                action: () => {},
            },
            {
                // Search for the target html field and ensure that it is editable.
                // Search in notebook tabs too.
                trigger: () => {
                    this.validatePage();
                    const el = this.getFirstVisibleElement(
                        `.o_field_html[name="${this.data.fieldName}"]`,
                        (element) => element.querySelector(".odoo-editor-editable")
                    );
                    if (el) {
                        return el;
                    }
                    if (this.data.pageName) {
                        this.searchInXmlDocNotebookTab(`page[name="${this.data.pageName}"]`);
                    }
                    return null;
                },
                action: "click",
            },
            {
                // Search for the editable element. Paste the html data inside the
                // field.
                trigger: () => {
                    this.validatePage();
                    return this.getFirstVisibleElement(
                        `.o_field_html[name="${this.data.fieldName}"] .odoo-editor-editable`
                    );
                },
                action: (el) => {
                    el.addEventListener(
                        "onHistoryResetFromPeer",
                        (ev) => pasteElements(this.data.dataTransfer, el),
                        { once: true }
                    );
                    pasteElements(this.data.dataTransfer, el);
                },
            },
            {
                action: () => this.unblockUI(),
            },
        ];
    }
}

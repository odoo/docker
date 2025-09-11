/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add("sign_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="sign.menu_document"]',
            content: markup(_t("Let's <b>prepare & sign</b> our first document.")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_nocontent_help .o_sign_sample",
            content: _t("Try out this sample contract."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger:
                ':iframe .o_sign_field_type_toolbar .o_sign_field_type_button:contains("' +
                _t("Signature") +
                '")',
            content: markup(_t("<b>Drag & drop “Signature”</b> into the bottom of the document.")),
            tooltipPosition: "bottom",
            run: "drag_and_drop",
        },
        {
            trigger: ".o_control_panel .o_sign_template_send",
            content: markup(
                _t(
                    "Well done, your document is ready!<br>Let's send it to get our first signature."
                )
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_field_signer_x2many",
            content: markup(
                _t(
                    "Select the contact who should sign, according to their role.<br>In this example, select your own contact to sign the document yourself."
                )
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: 'button[name="send_request"]',
            content: _t("Let's send the request by email."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_control_panel .o_sign_sign_directly",
            content: markup(
                _t(
                    "Since you're the one signing this document, you can do it directly within Odoo.<br>External users can use the link provided by email."
                )
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ":iframe .o_sign_sign_item_navigator",
            content: _t("Follow the guide to sign the document."),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger:
                ":iframe .o_sign_sign_item_navigator, :iframe .o_sign_sign_item[data-signature]",
            content: markup(
                _t(
                    "Draw your most beautiful signature!<br>You can also create one automatically or load a signature from your computer."
                )
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: "footer.modal-footer button.btn-primary:enabled",
            content: _t("Nearly there, keep going!"),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            isActive: ["auto"],
            trigger: ":iframe body:not(:has(footer.modal-footer button.btn-primary))",
        },
        {
            trigger: ".o_sign_validate_banner button.o_validate_button",
            content: _t("Congrats, your signature is ready to be submitted!"),
            tooltipPosition: "top",
            run: "click",
        },
        {
            trigger: '.modal-dialog button:contains("' + _t("Close") + '")',
            content: markup(
                _t(
                    "That's it, all done!<br>The document is signed, and a copy has been sent by email to all participants, along with a traceability report."
                )
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
    ],
});

/** @odoo-module **/

/**
 * Adapt the step that is specific to the work details when the `worksheet` module is not installed.
 */

import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import "@industry_fsm/js/tours/industry_fsm_tour";

patch(registry.category("web_tour.tours").get("industry_fsm_tour"), {
    steps() {
        const originalSteps = super.steps();
        const fsmStartStepIndex = originalSteps.findIndex((step) => step.id === "fsm_start");
        originalSteps.splice(
            fsmStartStepIndex + 1,
            0,
            {
                isActive: ["auto"],
                trigger: 'button[name="action_timer_stop"]',
            },
            {
            trigger: 'button[name="action_fsm_worksheet"]',
            content: markup(_t('Open your <b>worksheet</b> in order to fill it in with the details of your intervention.')),
            tooltipPosition: 'bottom',
                run: "click",
            },
            {
                isActive: ["auto"],
            trigger: 'body:not(.modal-open) nav.o_main_navbar, button[name="action_generate_new_template"]',
            run: "click",
            },
            {
                isActive: ["auto"],
                trigger: '.o_control_panel:not(:has(button[name="action_fsm_worksheet"]))',
            },
            {
            trigger: '.o_form_sheet div[name] input, .o_form_sheet .note-editable',
            content: markup(_t('Fill in your <b>worksheet</b> with the details of your intervention.')),
            run: "edit My intervention details",
            tooltipPosition: 'bottom',
            },
            {
                isActive: ["auto"],
                trigger: ".o_form_button_save",
                run: "click",
            },
            {
            trigger: ".breadcrumb-item.o_back_button:nth-of-type(2)",
            content: markup(_t("Use the breadcrumbs to return to your <b>task</b>.")),
                tooltipPosition: "bottom",
                run: "click",
            }
        );

        const fsmTimerStopStepIndex = originalSteps.findIndex(
            (step) => step.id === "fsm_save_timesheet"
        );
        originalSteps.splice(
            fsmTimerStopStepIndex + 1,
            0,
            {
                isActive: ["auto"],
                trigger: ".o_form_project_tasks",
            },
            {
            trigger: 'button[name="action_preview_worksheet"]',
            content: markup(_t('<b>Review and sign</b> the <b>task report</b> with your customer.')),
            tooltipPosition: 'bottom',
                run: "click",
            },
            {
                isActive: ["auto"],
                trigger: ".o_project_portal_sidebar",
            },
            {
                trigger: "a[data-bs-target='#modalaccept']:contains(sign report)",
            content: markup(_t('Invite your customer to <b>validate and sign your task report</b>.')),
            tooltipPosition: 'right',
            id: 'sign_report',
                run: "click",
            },
            {
                isActive: ["auto"],
                trigger: "div[name=worksheet_map] h5#task_worksheet",
                content: '"Worksheet" section is rendered',
            },
            {
                isActive: ["auto"],
                trigger: "div[name=worksheet_map] div[class*=row] div:not(:empty)",
                content: "At least a field is rendered",
            },
            {
                trigger: ".modal .o_web_sign_auto_button:contains(auto)",
            content: markup(_t('Save time by automatically generating a <b>signature</b>.')),
            tooltipPosition: 'right',
                run: "click",
            },
            {
                trigger:
                    ".modal .o_portal_sign_submit:enabled:contains(sign report):has(i.fa-check)",
            content: markup(_t('Validate the <b>signature</b>.')),
            tooltipPosition: 'left',
                run: "click",
            },
            {
                trigger: "body:not(:has(a[data-bs-target='#modalaccept']:contains(sign report))",
            },
            {
                trigger: "body:not(:has(.modal:contains(sign report)))",
            },
            {
                trigger: ".alert-info a.alert-link:contains(Back to edit mode)",
                content: markup(_t('Go back to your Field Service <b>task</b>.')),
                tooltipPosition: 'right',
                run: "click",
            },
            {
                trigger: 'button[name="action_send_report"]:enabled',
            content: markup(_t('<b>Send your task report</b> to your customer.')),
            tooltipPosition: 'bottom',
                run: "click",
            },
            {
                trigger: 'button[name="document_layout_save"]:enabled',
            content: markup(_t('Customize your <b>layout</b>.')),
            tooltipPosition: 'right',
                run: "click",
            },
            {
                isActive: ["auto"],
                trigger: ".o_form_project_tasks",
            },
            {
                trigger: 'button.o_mail_send:enabled',
            content: markup(_t('<b>Send your task report</b> to your customer.')),
            tooltipPosition: 'right',
                run: "click",
            }
        );
        return originalSteps;
    },
});

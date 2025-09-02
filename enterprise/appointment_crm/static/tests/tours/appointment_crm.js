/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

const oldWriteText = navigator.clipboard.writeText;

registry.category("web_tour.tours").add('appointment_crm_meeting_tour', {
    url: '/odoo',
    steps: () => [stepUtils.showAppsMenuItem(), {
        trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
        run: 'click',
    },
    {
        trigger: ".o_opportunity_kanban",
    },
    {
        trigger: '.o_kanban_record:contains("Test Opportunity")',
        run: 'click',
    }, {
        trigger: 'button[name="action_schedule_meeting"]',
        run: 'click',
    }, {
        trigger: 'button.dropdownAppointmentLink',
        run: 'click',
    }, {
        trigger: '.o_appointment_button_link:contains("Test AppointmentCRM")',
        run(helpers) {
            // Patch and ignore write on clipboard in tour as we don't have permissions
            navigator.clipboard.writeText = () => { console.info('Copy in clipboard ignored!') };
            helpers.click();
        },
    }, {
        trigger: '.o_appointment_discard_slots',
        async run(helpers) {
            await helpers.click();
            // Re-patch the function with the previous writeText
            navigator.clipboard.writeText = oldWriteText;
        },
    }],
});

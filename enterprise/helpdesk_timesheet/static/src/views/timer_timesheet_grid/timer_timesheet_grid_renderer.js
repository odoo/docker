/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { TimerTimesheetGridRenderer } from "@timesheet_grid/views/timer_timesheet_grid/timer_timesheet_grid_renderer";

patch(TimerTimesheetGridRenderer.prototype, {
    setup() {
        super.setup();
        this.helpdeskTimerHeaderService = useService("helpdesk_timer_header");
    },

    async onWillStart() {
        await super.onWillStart();
        this.helpdeskTimerHeaderService.invalidateCache();
    },
});

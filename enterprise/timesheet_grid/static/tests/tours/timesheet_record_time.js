/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('timesheet_record_time', {
    url: "/odoo",
    steps: () => [
    {
        trigger: ".o_app[data-menu-xmlid='hr_timesheet.timesheet_menu_root']",
        content: "Open Timesheet app.",
        run: "click"
    },
    {
        trigger: '.btn_start_timer',
        content: "Launch the timer to start a new activity.",
        run: "click"
    },
    {
        trigger: 'div[name=name] input',
        content: "Describe your activity.",
        run: "edit Description"
    },
    {
        trigger: '.timesheet-timer div[name="project_id"] input',
        content: "Select the project on which you are working.",
        run: "edit Test Project",
    },
    {
        isActive: ["auto"],
        trigger: ".ui-autocomplete > li > a:contains(Test Project)",
        run: "click",
    },
    {
        trigger: '.btn_stop_timer',
        content: "Stop the timer when you are done.",
        run: "click"
    }
]});

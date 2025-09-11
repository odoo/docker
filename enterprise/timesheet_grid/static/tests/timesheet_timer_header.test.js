import { expect, test, describe, beforeEach } from "@odoo/hoot";
import { click, getActiveElement, queryOne } from "@odoo/hoot-dom";
import { mockDate, animationFrame, delay } from "@odoo/hoot-mock";

import { onRpc, mountView, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { serializeDateTime } from "@web/core/l10n/dates";
import { session } from "@web/session";
import {
    defineTimesheetModels,
    timesheetModels,
} from "@timesheet_grid/../tests/timesheet_mock_models";

describe.current.tags("desktop");
defineTimesheetModels();

beforeEach(() => mockDate("2024-09-02"));
const { AnalyticLine } = timesheetModels;

const timesheetgridViewParams = {
    type: "grid",
    resModel: "account.analytic.line",
    arch: `
        <grid string="Timesheets" js_class="timer_timesheet_grid" create_inline="1" editable="1">
            <field name="project_id" type="row" widget="timesheet_many2one"/>
            <field name="task_id" type="row" widget="timesheet_many2one"/>
            <field name="employee_id" type="row" invisible="1" widget="timesheet_many2one_avatar_employee"/>
            <field name="date" type="col">
                <range name="day" string="Day" span="day" step="day" hotkey="e"/>
                <range name="week" string="Week" span="week" step="day" hotkey="w" default="1"/>
                <range name="month" string="Month" span="month" step="day" hotkey="m"/>
            </field>
            <field name="unit_amount" string="Time Spent" type="measure" widget="timesheet_uom"/>
        </grid>
    `,
};

beforeEach(() => {
    patchWithCleanup(session, {
        user_companies: {
            current_company: 1,
            allowed_companies: {
                1: {
                    id: 1,
                    name: "Hermit",
                    timesheet_uom_id: 1,
                    timesheet_uom_factor: 1,
                },
            },
        },
        uom_ids: {
            1: {
                id: 1,
                name: "hour",
                rounding: 0.01,
                timesheet_widget: "float_time",
            },
        },
    });

    AnalyticLine._records = [
        {
            id: 1,
            display_timer: true,
            is_timesheet: true,
            timer_start: serializeDateTime(luxon.DateTime.now().setZone("utc")),
            company_id: 1,
            date: "2024-09-02",
        },
    ];
});

// These methods are not required for this test.
// These methods can return an empty result and view is still is instantiated without any problems.
const non_relevant_methods = [
    "grid_unavailability",
    "get_daily_working_hours",
    "get_last_validated_timesheet_date",
    "action_timer_unlink",
    "action_timer_stop",
    "get_planned_and_worked_hours",
];

onRpc(({ args, kwargs, method, model }) => {
    if (model == "timer.timer" && method == "get_server_time") {
        return serializeDateTime(luxon.DateTime.now().setZone("utc"));
    }
    if (non_relevant_methods.includes(method)) {
        return [];
    } else if (method == "get_running_timer") {
        return { step_timer: 15 };
    } else if (method == "get_create_edit_project_ids") {
        return [];
    }
});

test("Test to check if start button is always in focus", async () => {
    await mountView(timesheetgridViewParams);

    // At each mount and patch Start Button should be in focus
    expect(".btn_start_timer").toHaveCount(1);
    expect(getActiveElement()).toBe(queryOne(".btn_start_timer"));

    // Click on a clickable button/action should be accessible and should not be disturbed
    // Force focus must not disturb other clicks
    await click(".o_grid_row:not(.o_grid_row_title, .o_grid_row_timer)");
    await delay(50);
    expect(getActiveElement()).toBe(queryOne(".o_grid_component div input"));

    // Click on body which doesn't have any fields/actions must make Start button to come in focus
    await click(document.body);
    expect(getActiveElement()).toBe(queryOne(".btn_start_timer"));
});

test("Test to check if stop button is always in focus", async () => {
    await mountView(timesheetgridViewParams);

    await click(".btn_start_timer");
    await animationFrame();
    // At each mount and patch Stop Button should be in focus
    expect(".btn_stop_timer").toHaveCount(1);
    expect(getActiveElement()).toBe(queryOne(".btn_stop_timer"));

    // Click on a clickable button/input should be accessible and should not be disturbed
    // Force focus must not disturb other clicks/inputs
    await click('.o_field_many2one[name="project_id"] input');
    expect(getActiveElement()).toBe(queryOne('.o_field_many2one[name="project_id"] input'));

    // Click on body which doesn't have any fields/actions must make Stop button to come in focus
    await click(document.body);
    expect(getActiveElement()).toBe(queryOne(".btn_stop_timer"));
});

import { describe, expect, test, beforeEach } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { delay } from "@odoo/hoot-mock";
import { onRpc, mountView } from "@web/../tests/web_test_helpers";

import { defineTimesheetModels } from "./hr_timesheet_models";
import { patchSession } from "@hr_timesheet/../tests/hr_timesheet_models";

defineTimesheetModels();
beforeEach(() => {
    patchSession();
});

describe.current.tags("desktop");

test("timesheet.grid (list)(timer): start & stop", async () => {
    await mountView({
        type: "list",
        resModel: "account.analytic.line",
    });
    expect(".btn_start_timer").toHaveCount(1);

    await click(".btn_start_timer");
    await delay(50);
    expect(".btn_stop_timer").toHaveCount(1);

    await click(".btn_stop_timer");
    await delay(50);
    expect(".btn_start_timer").toHaveCount(1);
});

test("timesheet.grid (list)(timer): start & stop, view is grouped", async () => {
    await mountView({
        type: "list",
        resModel: "account.analytic.line",
        groupBy: [ "project_id"],
    });
    expect(".btn_start_timer").toHaveCount(1);

    await click(".btn_start_timer");
    await delay(50);
    expect(".btn_stop_timer").toHaveCount(1);

    await click(".btn_stop_timer");
    await delay(50);
    expect(".btn_start_timer").toHaveCount(1);
});

test("timesheet.grid (list)(timer): start & stop, view is grouped multiple times", async () => {
    await mountView({
        type: "list",
        resModel: "account.analytic.line",
        groupBy: [ "project_id", "task_id", "name"],
    });
    expect(".btn_start_timer").toHaveCount(1);

    await click(".btn_start_timer");
    await delay(50);
    expect(".btn_stop_timer").toHaveCount(1);

    await click(".btn_stop_timer");
    await delay(50);
    expect(".btn_start_timer").toHaveCount(1);
});

test("timesheet.grid (list)(timer): start without a valid project", async () => {
    onRpc(({ method }) => {
        if (method === "action_start_new_timesheet_timer") {
            return false;
        }
    });
    await mountView({
        type: "list",
        resModel: "account.analytic.line",
    });
    expect(".btn_start_timer").toHaveCount(1);

    await click(".btn_start_timer");
    await delay(50);
    expect(".btn_stop_timer").toHaveCount(1);

    await click(".btn_stop_timer");
    await delay(50);
    expect("div.o_notification_manager h5:contains(Invalid fields:)").toHaveCount(1, {
        message: "The default notification of 'required fields' of a Many2one relation should be raised."
    });
});

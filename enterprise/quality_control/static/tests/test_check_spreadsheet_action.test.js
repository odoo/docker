import { describe, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { defineModels, getService, onRpc } from "@web/../tests/web_test_helpers";

import { mailModels } from "@mail/../tests/mail_test_helpers";
import { addColumns, deleteColumns, setCellContent } from "@spreadsheet/../tests/helpers/commands";

import { mountQualitySpreadsheetAction } from "./helpers/webclient_helpers";
import { defineQualitySpreadsheetModels } from "./helpers/data";

defineQualitySpreadsheetModels();
defineModels(mailModels);

describe("quality check spreadsheet action", () => {
    test("fail with an empty cell", async () => {
        const checkId = 1;
        onRpc("/web/dataset/call_kw/quality.check/do_fail", async function (request, args) {
            const { params } = await request.json();
            expect(params.args).toEqual([checkId]);
            expect.step("do_fail");
            return true;
        });
        await mountQualitySpreadsheetAction({ check_id: checkId });
        await click("button:contains(Save in The check name)");
        await animationFrame();
        expect.verifySteps(["do_fail"])
    });

    test("pass with a truthy cell", async () => {
        const checkId = 1;
        onRpc("/web/dataset/call_kw/quality.check/do_pass", async function (request, args) {
            const { params } = await request.json();
            expect(params.args).toEqual([checkId]);
            expect.step("do_pass");
            return true;
        });
        const { model } = await mountQualitySpreadsheetAction({ check_id: checkId });
        setCellContent(model, "A1", "1");
        await click("button:contains(Save in The check name)");
        await animationFrame();
        expect.verifySteps(["do_pass"])
    });

    test("pass wizard with a truthy cell, do next action", async () => {
        const qualityCheckWizardId = 1;
        const nextCheckSpreadsheetId = 1111;
        onRpc("/web/dataset/call_kw/quality.check.spreadsheet/join_spreadsheet_session", async function (request, args) {
            const { params } = await request.json();
            if (params.args[0] === nextCheckSpreadsheetId) {
                expect.step("join next check")
            }
        });
        onRpc("/web/dataset/call_kw/quality.check.wizard/do_pass", async function (request, args) {
            const { params } = await request.json();
            expect(params.args).toEqual([qualityCheckWizardId]);
            expect.step("do_pass");
            // return the next action
            return {
                type: "ir.actions.client",
                tag: "action_spreadsheet_quality",
                params: {
                    spreadsheet_id: nextCheckSpreadsheetId,
                    ...params,
                },
            };
        });
        const { model } = await mountQualitySpreadsheetAction({
            quality_check_wizard_id: qualityCheckWizardId
        });
        setCellContent(model, "A1", "1");
        await click("button:contains(Save in The check name)");
        await animationFrame();
        expect.verifySteps(["do_pass", "join next check"])
    });

    test("result cell is moved when adding column", async () => {
        const checkId = 1;
        onRpc("/web/dataset/call_kw/quality.check/do_pass", async function (request, args) {
            const { params } = await request.json();
            expect(params.args).toEqual([checkId]);
            expect.step("do_pass");
            return true;
        });
        onRpc("/web/dataset/call_kw/quality.check.spreadsheet/write", async function (request, args) {
            const { params } = await request.json();
            expect(params.args[1].check_cell).toBe("B1");
            expect.step("write");
            return true;
        });
        const { model } = await mountQualitySpreadsheetAction({ check_id: checkId });
        setCellContent(model, "A1", "1");
        addColumns(model, "before", "A", 1)
        await click("button:contains(Save in The check name)");
        await animationFrame();
        expect.verifySteps(["do_pass"])
        // leave the spreadsheet by going to another
        getService("action").doAction({
            type: "ir.actions.client",
            tag: "action_spreadsheet_quality",
            params: {
                spreadsheet_id: 1111,
            },
        })
        await animationFrame();
        expect.verifySteps(["write"])
    });

    test("result cell can be removed", async () => {
        const checkId = 1;
        onRpc("/web/dataset/call_kw/quality.check/do_pass", async function (request, args) {
            expect.step("do_pass");
            return true;
        });
        onRpc("/web/dataset/call_kw/quality.check.spreadsheet/write", async function (request, args) {
            const { params } = await request.json();
            expect(params.args[1].check_cell).toBe("#REF");
            expect.step("write");
            return true;
        });
        const { model } = await mountQualitySpreadsheetAction({ check_id: checkId });
        deleteColumns(model, ["A"])
        await click("button:contains(Save in The check name)");
        await animationFrame();
        expect.verifySteps(["do_pass"])
        // leave the spreadsheet by going to another
        getService("action").doAction({
            type: "ir.actions.client",
            tag: "action_spreadsheet_quality",
            params: {
                spreadsheet_id: 1111,
            },
        })
        await animationFrame();
        expect.verifySteps(["write"])
    });

    test("invalid check cell is equivalent to no condition", async () => {
        const checkId = 1;
        onRpc("/web/dataset/call_kw/quality.check.spreadsheet/join_spreadsheet_session", async function (request, args) {
            const { params } = await request.json();
            const data = this.env["quality.check.spreadsheet"].join_spreadsheet_session(...params.args)
            data.quality_check_cell = "not a valid cell reference";
            return data;
        });
        onRpc("/web/dataset/call_kw/quality.check/do_pass", async function (request, args) {
            expect.step("do_pass");
            return true;
        });
        await mountQualitySpreadsheetAction({ check_id: checkId });
        await click("button:contains(Save in The check name)");
        await animationFrame();
        expect.verifySteps(["do_pass"])
    });

    test("no check cell is equivalent to no condition", async () => {
        const checkId = 1;
        onRpc("/web/dataset/call_kw/quality.check.spreadsheet/join_spreadsheet_session", async function (request, args) {
            const { params } = await request.json();
            const data = this.env["quality.check.spreadsheet"].join_spreadsheet_session(...params.args)
            data.quality_check_cell = false; // False = no value in the py orm
            return data;
        });
        onRpc("/web/dataset/call_kw/quality.check/do_pass", async function (request, args) {
            expect.step("do_pass");
            return true;
        });
        await mountQualitySpreadsheetAction({ check_id: checkId });
        await click("button:contains(Save in The check name)");
        await animationFrame();
        expect.verifySteps(["do_pass"])
    });
});

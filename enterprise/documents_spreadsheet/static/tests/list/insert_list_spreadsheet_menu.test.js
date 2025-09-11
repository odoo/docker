import { defineDocumentSpreadsheetModels } from "@documents_spreadsheet/../tests/helpers/data";
import {
    invokeInsertListInSpreadsheetDialog,
    spawnListViewForSpreadsheet,
    toggleCogMenuSpreadsheet,
} from "@documents_spreadsheet/../tests/helpers/list_helpers";
import { SpreadsheetAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_action";
import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Partner, getBasicServerData } from "@spreadsheet/../tests/helpers/data";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import { getSpreadsheetActionModel } from "@spreadsheet_edition/../tests/helpers/webclient_helpers";
import { contains, patchWithCleanup, toggleActionMenu } from "@web/../tests/web_test_helpers";

defineDocumentSpreadsheetModels();
describe.current.tags("desktop");

let target;

beforeEach(() => {
    target = getFixture();
});

test("Can save a list in a new spreadsheet", async () => {
    await spawnListViewForSpreadsheet({
        mockRPC: async function (route, args) {
            if (
                args.method === "action_open_new_spreadsheet" &&
                args.model === "documents.document"
            ) {
                expect.step("action_open_new_spreadsheet");
            }
        },
    });
    await animationFrame();
    await toggleActionMenu();
    await toggleCogMenuSpreadsheet();
    await contains(".o_insert_list_spreadsheet_menu").click();
    await contains(".modal button.btn-primary").click();
    await animationFrame();
    expect.verifySteps(["action_open_new_spreadsheet"]);
});

test("Can save a list in existing spreadsheet", async () => {
    await spawnListViewForSpreadsheet({
        mockRPC: async function (route, args) {
            if (args.model === "documents.document") {
                /** These two methods are used for the PivotSelectorDialog */
                if (args.method !== "search_count" && args.method !== "get_views") {
                    expect.step(args.method);
                    switch (args.method) {
                        case "get_spreadsheets":
                            return {
                                records: [{ id: 1, name: "My Spreadsheet" }],
                                total: 1,
                            };
                    }
                }
            }
        },
    });

    let spreadsheetAction;
    patchWithCleanup(SpreadsheetAction.prototype, {
        setup() {
            super.setup();
            spreadsheetAction = this;
        },
    });

    await toggleActionMenu();
    await toggleCogMenuSpreadsheet();
    await contains(".o_insert_list_spreadsheet_menu").click();
    await contains(".o-spreadsheet-grid div[data-id='1']").click();
    await contains(".modal button.btn-primary").click();
    await animationFrame();

    expect.verifySteps(["get_spreadsheets", "action_open_spreadsheet", "join_spreadsheet_session"]);
    const model = getSpreadsheetActionModel(spreadsheetAction);
    const sheetId = model.getters.getActiveSheetId();
    expect(model.getters.getSheetName(sheetId)).toBe("Partners (List #1)");
});

test("Sheet name is the list name when the list is inserted", async () => {
    const { env } = await spawnListViewForSpreadsheet();

    let spreadsheetAction;
    patchWithCleanup(SpreadsheetAction.prototype, {
        setup() {
            super.setup();
            spreadsheetAction = this;
        },
    });
    await invokeInsertListInSpreadsheetDialog(env);
    await contains(".modal button.btn-primary").click();
    const model = getSpreadsheetActionModel(spreadsheetAction);
    const sheetId = model.getters.getActiveSheetId();
    expect(model.getters.getSheetName(sheetId)).toBe("Partners (List #1)");
});

test("List name can be changed from the dialog", async () => {
    const { env } = await spawnListViewForSpreadsheet();

    let spreadsheetAction;
    patchWithCleanup(SpreadsheetAction.prototype, {
        setup() {
            super.setup();
            spreadsheetAction = this;
        },
    });
    await invokeInsertListInSpreadsheetDialog(env);
    await contains(".o_sp_name").edit("New name");
    await contains(".modal button.btn-primary").click();
    const model = getSpreadsheetActionModel(spreadsheetAction);
    await waitForDataLoaded(model);
    expect(model.getters.getListName("1")).toBe("New name");
    expect(model.getters.getListDisplayName("1")).toBe("(#1) New name");
});

test("Unsorted List name doesn't contains sorting info", async function () {
    const { env } = await spawnListViewForSpreadsheet();

    await invokeInsertListInSpreadsheetDialog(env);
    expect(".o_sp_name").toHaveValue("Partners");
});

test("Sorted List name contains sorting info", async function () {
    const { env } = await spawnListViewForSpreadsheet({
        orderBy: [{ name: "bar", asc: true }],
    });

    await invokeInsertListInSpreadsheetDialog(env);
    expect(".o_sp_name").toHaveValue("Partners by Bar");
});

test("List name is not changed if the name is empty", async () => {
    const { env } = await spawnListViewForSpreadsheet();

    let spreadsheetAction;
    patchWithCleanup(SpreadsheetAction.prototype, {
        setup() {
            super.setup();
            spreadsheetAction = this;
        },
    });
    await invokeInsertListInSpreadsheetDialog(env);
    target.querySelector(".o_sp_name").value = "";
    await contains(".modal button.btn-primary").click();
    const model = getSpreadsheetActionModel(spreadsheetAction);
    await waitForDataLoaded(model);
    expect(model.getters.getListName("1")).toBe("Partners");
});

test("Grouped list: we take the number of elements not the number of groups", async function () {
    const serverData = getBasicServerData();
    const { env } = await spawnListViewForSpreadsheet({
        serverData,
        groupBy: ["product_id"],
    });

    await invokeInsertListInSpreadsheetDialog(env);
    expect("input#threshold").toHaveValue(Partner._records.length);
});

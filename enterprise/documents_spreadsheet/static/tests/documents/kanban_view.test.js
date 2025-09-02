import { DocumentsSearchPanel } from "@documents/views/search/documents_search_panel";
import {
    defineDocumentSpreadsheetModels,
    getBasicPermissionPanelData,
} from "@documents_spreadsheet/../tests/helpers/data";
import { makeDocumentsSpreadsheetMockEnv } from "@documents_spreadsheet/../tests/helpers/model";
import { mockActionService } from "@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils";
import { XLSX_MIME_TYPES } from "@documents_spreadsheet/helpers";
import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Model } from "@odoo/o-spreadsheet";
import {
    contains,
    mountView,
    onRpc,
    patchWithCleanup,
    preloadBundle,
} from "@web/../tests/web_test_helpers";
import { loadBundle } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { download } from "@web/core/network/download";
import { deepEqual } from "@web/core/utils/objects";
import { SearchPanel } from "@web/search/search_panel/search_panel";
import { getEnrichedSearchArch } from "../helpers/document_helpers";

describe.current.tags("desktop");
defineDocumentSpreadsheetModels();
preloadBundle("spreadsheet.o_spreadsheet");

let target;

const basicDocumentKanbanArch = /* xml */ `
<kanban js_class="documents_kanban">
    <templates>
        <field name="id"/>
        <field name="available_embedded_actions_ids"/>
        <field name="access_token"/>
        <field name="mimetype"/>
        <field name="folder_id"/>
        <field name="active"/>
        <field name="type"/>
        <field name="attachment_id"/>
        <t t-name="card">
            <div>
                <div name="document_preview" class="o_kanban_image_wrapper">a thumbnail</div>
                <i class="fa fa-circle o_record_selector" />
                <field name="name" />
                <field name="handler" />
            </div>
        </t>
    </templates>
</kanban>
`;

/**
 * @returns {Object}
 */
function getTestServerData(spreadsheetData = {}) {
    return {
        models: {
            "documents.document": {
                records: [
                    {
                        id: 1,
                        name: "Workspace1",
                        type: "folder",
                        available_embedded_actions_ids: [],
                    },
                    {
                        id: 2,
                        name: "My spreadsheet",
                        spreadsheet_data: JSON.stringify(spreadsheetData),
                        is_favorited: false,
                        folder_id: 1,
                        handler: "spreadsheet",
                        access_token: "accessTokenMyspreadsheet",
                    },
                ],
            },
        },
    };
}

beforeEach(() => {
    target = getFixture();
    // Due to the search panel allowing double clicking on elements, the base
    // methods have a debounce time in order to not do anything on dblclick.
    // This patch removes those features
    patchWithCleanup(DocumentsSearchPanel.prototype, {
        toggleCategory() {
            return SearchPanel.prototype.toggleCategory.call(this, ...arguments);
        },
        toggleFilterGroup() {
            return SearchPanel.prototype.toggleFilterGroup.call(this, ...arguments);
        },
        toggleFilterValue() {
            return SearchPanel.prototype.toggleFilterValue.call(this, ...arguments);
        },
    });
});

test("download frozen spreadsheet", async function () {
    const serverData = getTestServerData();
    // Only frozen spreadsheet can be downloaded in document.
    serverData.models["ir.attachment"] = { records: [{ id: 1 }] };
    serverData.models["documents.document"].records[1].handler = "frozen_spreadsheet";
    serverData.models["documents.document"].records[1].attachment_id = 1;
    onRpc("/documents/touch/accessTokenMyspreadsheet", () => true);
    await makeDocumentsSpreadsheetMockEnv({
        serverData,
    });
    patchWithCleanup(download, {
        _download: async (options) => {
            expect.step(options.url);
            expect(deepEqual(options.data, {})).toBe(true);
        },
    });
    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });

    await contains(".o_kanban_record:contains(My spreadsheet) .o_record_selector").click({
        ctrlKey: true,
    });
    await contains("button:contains(Download)").click();
    await animationFrame();
    expect.verifySteps(["/documents/content/accessTokenMyspreadsheet"]);
});

test("share a spreadsheet", async function () {
    onRpc("/documents/touch/accessTokenMyspreadsheet", () => true);
    const spreadsheetId = 2;
    const serverData = getTestServerData();
    patchWithCleanup(browser.navigator.clipboard, {
        writeText: async (url) => {
            expect.step("share url copied");
            expect(url).toBe("http://localhost:8069/share/url/132465");
        },
    });
    await makeDocumentsSpreadsheetMockEnv({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "permission_panel_data") {
                expect(args.args[0]).toEqual(spreadsheetId);
                expect.step("permission_panel_data");
                return getBasicPermissionPanelData({ handler: "spreadsheet" });
            }
            if (args.method === "can_upload_traceback") {
                return false;
            }
        },
    });
    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });
    expect(target.querySelector(".spreadsheet_share_dropdown")).toBe(null);
    await contains(".o_kanban_record:contains(My spreadsheet) .o_record_selector").click({
        ctrlKey: true,
    });
    await contains("button:contains(Share)").click();

    await contains(".o_clipboard_button", { timeout: 1500 }).click();
    expect.verifySteps(["permission_panel_data", "share url copied"]);
});

test("Freeze&Share a spreadsheet", async function () {
    onRpc("/documents/touch/accessTokenMyspreadsheet", () => true);
    const spreadsheetId = 2;
    const frozenSpreadsheetId = 1337;
    const model = new Model();
    const serverData = getTestServerData();
    serverData.models["documents.document"].records[1].spreadsheet_data = JSON.stringify(
        model.exportData()
    );
    patchWithCleanup(browser.navigator.clipboard, {
        writeText: async (url) => {
            expect.step("share url copied");
            expect(url).toBe("http://localhost:8069/share/url/132465");
        },
    });
    await makeDocumentsSpreadsheetMockEnv({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "action_freeze_and_copy") {
                const excel = JSON.parse(JSON.stringify(model.exportXLSX().files));

                expect(args.args[0]).toEqual(spreadsheetId);
                expect(args.args[1]).toEqual(JSON.stringify(model.exportData()));
                expect(args.args[2]).toEqual(excel);

                expect.step("spreadsheet_shared");
                return { id: frozenSpreadsheetId };
            }
            if (args.method === "permission_panel_data") {
                expect(args.args[0]).toEqual(frozenSpreadsheetId);
                expect.step("permission_panel_data");
                return getBasicPermissionPanelData({ handler: "spreadsheet" });
            }
            if (args.method === "can_upload_traceback") {
                return false;
            }
        },
    });
    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });
    expect(target.querySelector(".spreadsheet_share_dropdown")).toBe(null);
    await contains(".o_kanban_record:contains(My spreadsheet) .o_record_selector").click({
        ctrlKey: true,
    });
    await contains("button:contains(Freeze and share)").click();
    await contains(".o_clipboard_button", { timeout: 1500 }).click();
    expect.verifySteps(["spreadsheet_shared", "permission_panel_data", "share url copied"]);
});

test.skip("share the full workspace from the share button", async function () {
    const model = new Model();
    const serverData = getTestServerData(model.exportData());
    await makeDocumentsSpreadsheetMockEnv({
        serverData,
        mockRPC: async (route, args) => {
            if (args.method === "web_save") {
                expect.step("spreadsheet_shared");
                const shareVals = args.kwargs.context;
                expect(args.model).toBe("documents.share");
                expect(shareVals.default_folder_id).toBe(1);
                expect(shareVals.default_type).toBe("domain");
                expect(shareVals.default_domain).toEqual([["folder_id", "=", 1]]);
                expect(shareVals.default_spreadsheet_shares).toEqual(
                    JSON.stringify([
                        {
                            spreadsheet_data: JSON.stringify(model.exportData()),
                            excel_files: JSON.parse(JSON.stringify(model.exportXLSX().files)),
                            document_id: 1,
                        },
                    ])
                );
            }
        },
    });
    await loadBundle("spreadsheet.o_spreadsheet");
    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });
    patchWithCleanup(navigator.clipboard, {
        async writeText() {
            expect.step("copy");
        },
    });

    const menu = target.querySelector(".o_control_panel .d-inline-flex");
    await contains(menu.querySelector(".dropdown-toggle")).click();
    await contains(menu.querySelector(".o_documents_kanban_share_domain")).click();
    expect.verifySteps([]);
    await contains(".o_form_button_save").click();
    expect.verifySteps(["spreadsheet_shared", "copy"]);
});

test("open xlsx converts to o-spreadsheet, clone it and opens the spreadsheet", async function () {
    const spreadsheetId = 1;
    const spreadsheetCopyId = 99;
    const serverData = getTestServerData();
    serverData.models["documents.document"].records = [
        {
            id: spreadsheetId,
            name: "My excel file",
            mimetype: XLSX_MIME_TYPES[0],
            thumbnail_status: "present",
        },
    ];
    await makeDocumentsSpreadsheetMockEnv({
        serverData,
        mockRPC: async (route, args) => {
            if (args.method === "clone_xlsx_into_spreadsheet") {
                expect.step("spreadsheet_cloned");
                expect(args.model).toBe("documents.document");
                expect(args.args).toEqual([spreadsheetId]);
                return spreadsheetCopyId;
            }
        },
    });
    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });
    mockActionService((action) => {
        expect.step(action.tag);
        expect(action.params.spreadsheet_id).toEqual(spreadsheetCopyId);
    });
    await contains(".o_kanban_image_wrapper").click();

    // confirm conversion to o-spreadsheet
    await contains(".modal-content .btn.btn-primary").click();
    expect.verifySteps(["spreadsheet_cloned", "action_open_spreadsheet"]);
});

test("open WPS-marked xlsx converts to o-spreadsheet, clone it and opens the spreadsheet", async function () {
    const spreadsheetId = 1;
    const spreadsheetCopyId = 99;
    const serverData = getTestServerData();
    serverData.models["documents.document"].records = [
        {
            id: spreadsheetId,
            name: "My excel file",
            mimetype: XLSX_MIME_TYPES[1],
            thumbnail_status: "present",
        },
    ];
    await makeDocumentsSpreadsheetMockEnv({
        serverData,
        mockRPC: async (route, args) => {
            if (args.method === "clone_xlsx_into_spreadsheet") {
                expect.step("spreadsheet_cloned");
                expect(args.model).toBe("documents.document");
                expect(args.args).toEqual([spreadsheetId]);
                return spreadsheetCopyId;
            }
        },
    });
    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });
    mockActionService((action) => {
        expect.step(action.tag);
        expect(action.params.spreadsheet_id).toEqual(spreadsheetCopyId);
    });
    await contains(".oe_kanban_previewer").click();

    // confirm conversion to o-spreadsheet
    await contains(".modal-content .btn.btn-primary").click();
    expect.verifySteps(["spreadsheet_cloned", "action_open_spreadsheet"]);
});

test("download a frozen spreadsheet document while selecting requested document", async function () {
    onRpc("/documents/touch/accessTokenMyspreadsheet", () => true);
    onRpc("/documents/touch/accessTokenRequest", () => true);
    const serverData = getTestServerData();
    serverData.models["ir.attachment"] = { records: [{ id: 1 }] };
    serverData.models["documents.document"].records = [
        {
            name: "My spreadsheet",
            raw: "{}",
            is_favorited: false,
            folder_id: 1,
            handler: "frozen_spreadsheet",
            type: "binary",
            access_token: "accessTokenMyspreadsheet",
            attachment_id: 1, // Necessary to not be considered as a request
        },
        {
            name: "Request",
            folder_id: 1,
            type: "binary",
            access_token: "accessTokenRequest",
        },
    ];
    await makeDocumentsSpreadsheetMockEnv({
        serverData,
    });
    patchWithCleanup(download, {
        _download: async (options) => {
            expect.step(options.url);
            expect(deepEqual(options.data, {})).toBe(true);
        },
    });
    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });

    await contains(".o_kanban_record:nth-of-type(1) .o_record_selector").click({ ctrlKey: true });
    await contains(".o_kanban_record:nth-of-type(2) .o_record_selector").click({ ctrlKey: true });
    await contains("button:contains(Download)").click();
    // The request is ignored and only the spreadsheet is downloaded.
    expect.verifySteps(["/documents/content/accessTokenMyspreadsheet"]);
});

test("can open spreadsheet while multiple documents are selected along with it", async function () {
    const serverData = getTestServerData();
    serverData.models["documents.document"].records = [
        { id: 1, name: "demo-workspace", type: "folder" },
    ];
    serverData.models["documents.document"].records = [
        {
            name: "test-spreadsheet",
            raw: "{}",
            folder_id: 1,
            handler: "spreadsheet",
            thumbnail_status: "present",
        },
        {
            folder_id: 1,
            mimetype: "image/png",
            name: "test-image-1",
        },
        {
            folder_id: 1,
            mimetype: "image/png",
            name: "test-image-2",
        },
    ];
    await makeDocumentsSpreadsheetMockEnv({ serverData });
    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });

    mockActionService((action) => {
        expect.step(action.tag);
    });
    const fixture = getFixture();
    const records = fixture.querySelectorAll(".o_kanban_record");
    await contains(records[0].querySelector(".o_record_selector")).click();
    await contains(records[1].querySelector(".o_record_selector")).click();
    await contains(records[2].querySelector(".o_record_selector")).click();
    await contains(records[2].querySelector(".oe_kanban_previewer")).click();
    expect(".o-FileViewer").toHaveCount(0);
    expect.verifySteps(["action_open_spreadsheet"]);
});

test("spreadsheet should be skipped while toggling the preview in the FileViewer", async function () {
    const serverData = getTestServerData();
    serverData.models["ir.attachment"] = {
        records: [
            { id: 2, name: "dogsFTW" },
            { id: 3, name: "pug" },
            { id: 4, name: "chihuahua" },
        ],
    };
    serverData.models["documents.document"].records = [
        { id: 1, name: "dogsFTW", type: "folder" },
        {
            id: 2,
            name: "dog-stats",
            raw: "{}",
            folder_id: 1,
            handler: "spreadsheet",
            thumbnail_status: "present",
            access_token: "accessTokendog-stats",
            attachment_id: 2,
        },
        {
            id: 3,
            folder_id: 1,
            mimetype: "image/png",
            name: "pug",
            access_token: "accessTokenpug",
            attachment_id: 3,
        },
        {
            id: 4,
            folder_id: 1,
            mimetype: "image/png",
            name: "chihuahua",
            access_token: "accessTokenchihuahua",
            attachment_id: 4,
        },
    ];
    await makeDocumentsSpreadsheetMockEnv({ serverData });
    await mountView({
        type: "kanban",
        resModel: "documents.document",
        arch: basicDocumentKanbanArch,
        searchViewArch: getEnrichedSearchArch(),
    });

    await contains(".o_kanban_record:contains(chihuahua) div[name='document_preview']").click();
    expect(".o-FileViewer").toHaveCount(1);
    expect(".o-FileViewer-header div:first()").toHaveText("chihuahua");
    await contains(".o-FileViewer-navigation[aria-label='Next']").click();
    expect(".o-FileViewer-header div:first()").toHaveText("pug");
    await contains(".o-FileViewer-navigation[aria-label='Next']").click();
    expect(".o-FileViewer-header div:first()").toHaveText("chihuahua");
});

import { SpreadsheetAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_action";
import { getFixture } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { onMounted } from "@odoo/owl";
import { makeDocumentsSpreadsheetMockEnv } from "@documents_spreadsheet/../tests/helpers/model";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import {
    getSpreadsheetActionEnv,
    getSpreadsheetActionModel,
    prepareWebClientForSpreadsheet,
} from "@spreadsheet_edition/../tests/helpers/webclient_helpers";
import {
    contains,
    getService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { Deferred } from "@web/core/utils/concurrency";
import { WebClient } from "@web/webclient/webclient";

/** @typedef {import("@spreadsheet/o_spreadsheet/o_spreadsheet").Model} Model */

/**
 * Get a webclient with a graph view.
 * The webclient is already configured to work with spreadsheet (env, registries, ...)
 *
 * @param {object} params
 * @param {string} [params.model] Model name of the graph
 * @param {object} [params.serverData] Data to be injected in the mock server
 * @param {function} [params.mockRPC] Mock rpc function
 * @param {any[]} [params.domain] Domain of the graph
 * @param {object} [params.additionalContext] additional context for the action
 * @returns {Promise<object>} Webclient
 */
export async function spawnGraphViewForSpreadsheet(params = {}) {
    await prepareWebClientForSpreadsheet();
    await makeDocumentsSpreadsheetMockEnv(params);
    const webClient = await mountWithCleanup(WebClient);

    await getService("action").doAction(
        {
            name: "graph view",
            res_model: params.model || "partner",
            type: "ir.actions.act_window",
            views: [[false, "graph"]],
            domain: params.domain,
        },
        {
            additionalContext: params.additionalContext || {},
        }
    );
    return webClient;
}

/**
 * @typedef {object} CreateGraphTestParams
 * @property {Array} [domain] Domain of the graph
 * @property {string} [model] graph resModel
 * @property {number} [documentId] ID of an existing document
 * @property {function} [actions] Actions to execute on the graph view
 *                                before inserting in spreadsheet
 * @property {function} [mockRPC] Mock rpc function
 * @property {object} [serverData] Data to be injected in the mock server
 * @property {object} [additionalContext] additional context for the action
 */

/**
 * Create a spreadsheet model from a graph controller
 *
 * @param {CreateGraphTestParams & import("@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils").SpreadsheetTestParams} params
 * @returns {Promise<object>} Webclient
 */
export async function createSpreadsheetFromGraphView(params = {}) {
    let spreadsheetAction = {};
    const def = new Deferred();
    patchWithCleanup(SpreadsheetAction.prototype, {
        setup() {
            super.setup();
            spreadsheetAction = this;
            onMounted(() => {
                def.resolve();
            });
        },
    });
    const webClient = await spawnGraphViewForSpreadsheet({
        model: params.model,
        serverData: params.serverData,
        mockRPC: params.mockRPC,
        domain: params.domain,
        additionalContext: params.additionalContext || {},
    });
    const target = getFixture();
    if (params.actions) {
        await params.actions(target);
    }
    await contains(target.querySelector(".o_graph_insert_spreadsheet")).click();
    if (params.documentId) {
        await contains(`.o-spreadsheet-grid div[data-id='${params.documentId}']`).focus();
    }
    await contains(document.querySelector(".modal-content > .modal-footer > .btn-primary")).click();
    await def;
    await animationFrame();
    const model = getSpreadsheetActionModel(spreadsheetAction);
    await waitForDataLoaded(model);
    return {
        webClient,
        env: getSpreadsheetActionEnv(spreadsheetAction),
        model,
    };
}

export async function openChartSidePanel(model, env) {
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    model.dispatch("SELECT_FIGURE", { id: chartId });
    env.openSidePanel("ChartPanel", {});
    await animationFrame();
}

import {
    SpreadsheetTemplate,
    defineDocumentSpreadsheetModels,
} from "@documents_spreadsheet/../tests/helpers/data";
import { createSpreadsheetFromPivotView } from "@documents_spreadsheet/../tests/helpers/pivot_helpers";
import {
    createSpreadsheet,
    createSpreadsheetTemplate,
} from "@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils";
import { expect, getFixture, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { getBasicData } from "@spreadsheet/../tests/helpers/data";
import { doMenuAction } from "@spreadsheet/../tests/helpers/ui";
import { contains } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { actionService } from "@web/webclient/actions/action_service";

defineDocumentSpreadsheetModels();

const { topbarMenuRegistry } = spreadsheet.registries;

test("new template menu", async function () {
    const serviceRegistry = registry.category("services");
    serviceRegistry.add("actionMain", actionService);
    const fakeActionService = {
        dependencies: ["actionMain"],
        start(env, { actionMain }) {
            return {
                ...actionMain,
                doAction: (actionRequest, options = {}) => {
                    if (
                        actionRequest.tag === "action_open_template" &&
                        actionRequest.params.spreadsheet_id === 111
                    ) {
                        expect.step("redirect");
                    }
                    return actionMain.doAction(actionRequest, options);
                },
            };
        },
    };
    serviceRegistry.add("action", fakeActionService, { force: true });
    const models = getBasicData();
    const { env } = await createSpreadsheetTemplate({
        serverData: { models },
        mockRPC: function (route, args) {
            if (args.model == "spreadsheet.template" && args.method === "create") {
                expect.step("new_template");
                SpreadsheetTemplate._records.push({
                    id: 111,
                    name: "test template",
                    spreadsheet_data: "{}",
                });
                return 111;
            }
        },
    });
    await doMenuAction(topbarMenuRegistry, ["file", "new_sheet"], env);
    await animationFrame();
    expect.verifySteps(["new_template", "redirect"]);
});

test("copy template menu", async function () {
    const serviceRegistry = registry.category("services");
    serviceRegistry.add("actionMain", actionService);
    const fakeActionService = {
        dependencies: ["actionMain"],
        start(env, { actionMain }) {
            return {
                ...actionMain,
                doAction: (actionRequest, options = {}) => {
                    if (
                        actionRequest.tag === "action_open_template" &&
                        actionRequest.params.spreadsheet_id === 111
                    ) {
                        expect.step("redirect");
                    }
                    return actionMain.doAction(actionRequest, options);
                },
            };
        },
    };
    serviceRegistry.add("action", fakeActionService, { force: true });
    const models = getBasicData();
    const { env } = await createSpreadsheetTemplate({
        serverData: { models },
        mockRPC: function (route, args) {
            if (args.model == "spreadsheet.template" && args.method === "copy") {
                expect.step("template_copied");
                const { spreadsheet_data, thumbnail } = args.kwargs.default;
                expect(spreadsheet_data).not.toBe(undefined);
                expect(thumbnail).not.toBe(undefined);
                SpreadsheetTemplate._records.push({
                    id: 111,
                    name: "template",
                    spreadsheet_data,
                    thumbnail,
                });
                return [111];
            }
        },
    });
    await doMenuAction(topbarMenuRegistry, ["file", "make_copy"], env);
    await animationFrame();
    expect.verifySteps(["template_copied", "redirect"]);
});

test("Save as template menu", async function () {
    const serviceRegistry = registry.category("services");
    serviceRegistry.add("actionMain", actionService);
    const fakeActionService = {
        dependencies: ["actionMain"],
        start(env, { actionMain }) {
            return Object.assign({}, actionMain, {
                doAction: (actionRequest, options = {}) => {
                    if (
                        actionRequest === "documents_spreadsheet.save_spreadsheet_template_action"
                    ) {
                        expect.step("create_template_wizard");

                        const context = options.additionalContext;
                        const data = JSON.parse(context.default_spreadsheet_data);
                        const name = context.default_template_name;
                        const cells = data.sheets[0].cells;
                        expect(name).toBe("Untitled spreadsheet - Template", {
                            message: "It should be named after the spreadsheet",
                        });
                        expect(context.default_thumbnail).not.toBe(undefined);
                        expect(cells.A3.content).toBe(`=PIVOT.HEADER(1,"product_id",37)`);
                        expect(cells.B3.content).toBe(
                            `=PIVOT.VALUE(1,"probability:avg","product_id",37,"bar",FALSE)`
                        );
                        expect(cells.A11.content).toBe("😃");
                        return Promise.resolve(true);
                    }
                    return actionMain.doAction(actionRequest, options);
                },
            });
        },
    };
    serviceRegistry.add("action", fakeActionService, { force: true });
    const { env, model } = await createSpreadsheetFromPivotView({
        serverData: {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /*xml*/ `
                        <pivot>
                            <field name="bar" type="col"/>
                            <field name="product_id" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                "partner,false,search": `<search/>`,
            },
        },
    });
    setCellContent(model, "A11", "😃");
    await doMenuAction(topbarMenuRegistry, ["file", "save_as_template"], env);
    await animationFrame();
    expect.verifySteps(["create_template_wizard"]);
});

test("Name template with spreadsheet name", async function () {
    const serviceRegistry = registry.category("services");
    serviceRegistry.add("actionMain", actionService);
    const fakeActionService = {
        dependencies: ["actionMain"],
        start(env, { actionMain }) {
            return Object.assign({}, actionMain, {
                doAction: (actionRequest, options = {}) => {
                    if (
                        actionRequest === "documents_spreadsheet.save_spreadsheet_template_action"
                    ) {
                        expect.step("create_template_wizard");
                        const name = options.additionalContext.default_template_name;
                        expect(name).toBe("My spreadsheet - Template", {
                            message: "It should be named after the spreadsheet",
                        });
                        return Promise.resolve(true);
                    }
                    return actionMain.doAction(actionRequest, options);
                },
            });
        },
    };
    serviceRegistry.add("action", fakeActionService, { force: true });
    const { env } = await createSpreadsheet({
        mockRPC: function (route, args) {
            if (args.method === "create" && args.model === "spreadsheet.template") {
                expect.step("create_template");
                expect(args.args[0].name).toBe("My spreadsheet", {
                    message: "It should be named after the spreadsheet",
                });
            }
        },
    });
    const target = getFixture();
    const input = target.querySelector(".o_sp_name input");
    await contains(input).edit("My spreadsheet");
    await doMenuAction(topbarMenuRegistry, ["file", "save_as_template"], env);
    await animationFrame();
    expect.verifySteps(["create_template_wizard"]);
});

import { Component, useSubEnv, xml } from "@odoo/owl";
import { getFixture } from "@odoo/hoot";

import { MainComponentsContainer } from "@web/core/main_components_container";
import { registry } from "@web/core/registry";
import { getMockEnv } from "@web/../tests/_framework/env_test_helpers";
import { MockServer, mountWithCleanup, makeMockEnv, onRpc } from "@web/../tests/web_test_helpers";
import { getDefaultConfig } from "@web/views/view";
import { parseViewProps } from "@web/../tests/_framework/view_test_helpers";
import { useService } from "@web/core/utils/hooks";
import { useOwnDebugContext } from "@web/core/debug/debug_context";

import { useStudioServiceAsReactive } from "@web_studio/studio_service";
import { ViewEditor } from "@web_studio/client_action/view_editor/view_editor";
import { EditionFlow } from "@web_studio/client_action/editor/edition_flow";

const serviceRegistry = registry.category("services");

class ViewEditorHoc extends Component {
    static template = xml`<ViewEditor action="{}" className="''" />`;
    static components = { ViewEditor };
    static props = ["*"];
    setup() {
        const editionFlow = new EditionFlow(this.env, {
            dialog: useService("dialog"),
            studio: useStudioServiceAsReactive(),
            view: useService("view"),
        });
        useSubEnv({
            editionFlow,
        });
        if (this.env.debug) {
            useOwnDebugContext();
        }
    }
}

class ViewEditorParent extends Component {
    static components = { ViewEditorHoc, MainComponentsContainer };
    static props = {};
    static template = xml`
        <MainComponentsContainer />
        <div class="o_studio h-100">
            <div class="o_web_studio_editor">
                <div class="o_action_manager">
                    <div class="o_web_studio_editor_manager d-flex flex-row w-100 h-100">
                        <ViewEditorHoc />
                    </div>
                </div>
            </div>
        </div>
    `;
}

/**
 * @param {string} type
 * @param {string} arch
 * @param {import("@web/../tests/web_test_helpers")["models"]["Model"]} model
 */
export async function createMockViewResult(type, arch, model) {
    const { models } = MockServer.current;
    return {
        models: Object.fromEntries(
            Object.entries(models).map(([name, model]) => [name, { fields: model._fields }])
        ),
        views: {
            [type]: {
                arch,
                model: model._name,
            },
        },
    };
}

export function disableHookAnimation() {
    const fixture = getFixture();
    fixture.querySelectorAll(".o_web_studio_hook, .o_web_studio_hook_separator").forEach((sep) => {
        sep.style.setProperty("transition", "none", "important");
        sep.style.setProperty("min-height", "20px");
    });
}

function makeMockRPC() {
    onRpc("/web_studio/activity_allowed", () => false);
    onRpc("/web_studio/chatter_allowed", () => false);
    onRpc("/web_studio/edit_view", () => {});
    onRpc("/web_studio/edit_view_arch", () => {});
    onRpc("/web_studio/get_default_value", () => {
        return { default_value: undefined };
    });
    onRpc("/web_studio/get_studio_view_arch", () => ({ studio_view_arch: "" }));
    onRpc("get_approval_spec", ({ args }) => {
        const result = { all_rules: {} };
        const args_list = args[0];
        for (const { model } of args_list) {
            result[model] = [];
        }
        return result;
    });
}

export async function mountViewEditor(params) {
    const actionToEdit = { res_model: params.resModel };
    const config = { ...getDefaultConfig(), ...params.config };
    params.viewId = params.viewId || 99999999;

    prepareRegistry();
    const env = params.env || getMockEnv() || (await makeMockEnv({ config }));

    if (params.type && params.arch) {
        parseViewProps(params);
        actionToEdit.views = [[params.viewId, params.type]];
    }

    makeMockRPC();

    env.services.studio.setParams({
        viewType: params.type,
        editorTab: "views",
        action: actionToEdit,
        controllerState: {
            resId: params.resId,
        },
        mode: "editor",
    });
    return mountWithCleanup(ViewEditorParent, {
        env,
    });
}

function prepareRegistry() {
    registry.category("main_components").remove("mail.ChatHub");
    registry.category("main_components").remove("discuss.CallInvitations");
    registry.category("main_components").remove("bus.connection_alert");
    const REQUIRED_SERVICES = [
        "mail.popout",
        "title",
        "orm",
        "field",
        "name",
        "home_menu",
        "menu",
        "action",
        "studio",
        "notification",
        "dialog",
        "popover",
        "hotkey",
        "localization",
        "company",
        "view",
        "overlay",
        "ui",
        "effect",
        "web_studio.get_approval_spec_batched",
    ];
    Object.keys(serviceRegistry.content).forEach((e) => {
        if (!REQUIRED_SERVICES.includes(e)) {
            serviceRegistry.remove(e);
        }
    });
    serviceRegistry.add("messaging", makeFakeMessagingService());
}

function makeFakeMessagingService() {
    const chatter = {
        update: () => {},
        refresh: () => {},
        exists: () => {},
        delete: () => {},
        thread: {},
    };

    const messaging = {
        models: {
            Chatter: {
                insert: () => chatter,
            },
        },
    };

    const service = {
        get: () => messaging,
        modelManager: {
            messaging,
            messagingCreatedPromise: new Promise((resolve) => resolve()),
            startListening: () => {},
            stopListening: () => {},
            removeListener: () => {},
        },
    };

    return {
        start(env) {
            return service;
        },
    };
}

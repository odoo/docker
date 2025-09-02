import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { EventBus } from "@odoo/owl";
import {
    contains,
    makeServerError,
    mockService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { MainComponentsContainer } from "@web/core/main_components_container";

defineMailModels();

test("Shareable error dialog", async () => {
    expect.errors(1);
    const _bus = new EventBus();
    patchWithCleanup(browser.navigator.clipboard, {
        async writeText(text) {
            expect.step(text);
        },
    });

    mockService("notification", {
        add: (message, options) => {
            expect(message).toBe("The document URL has been copied to your clipboard.");
            expect(options).toEqual({ type: "success" });
            expect.step("Success notification");
        },
    });

    mockService("file_upload", {
        bus: _bus,
        upload: (route, files, params = {}) => {
            if (route === "/documents/upload_traceback") {
                _bus.trigger("FILE_UPLOAD_LOADED", {
                    upload: { data: new FormData(), xhr: { status : 200, response: '["test url"]' } }
                });
                expect.step("Upload traceback");
            }
        },
    })

    const error = makeServerError({
        subType: "Odoo Client Error",
        message: "Message",
        errorName: "client error",
    });

    await mountWithCleanup(MainComponentsContainer);
    onRpc("documents.document", "can_upload_traceback", () => {
        expect.step("Check access rights");
        return true;
    });

    Promise.reject(error);
    await animationFrame();
    expect.verifyErrors(["Message"]);
    expect(".modal-footer button:contains(Close)").toHaveCount(1);
    expect(".modal-footer button:contains(Share)").toHaveCount(1);
    expect(".modal-footer button:contains(Share)").toBeEnabled();
    await contains(".modal-footer button:contains(Share)").click();
    expect(".modal-footer button:contains(Share)").not.toBeEnabled();
    await animationFrame();
    expect.verifySteps([
        "Check access rights",
        "Upload traceback",
        "test url",
        "Success notification",
    ]);
    expect(".modal-footer .o_field_CopyClipboardChar").toHaveCount(1);
    expect(".modal-footer .o_field_CopyClipboardChar").toHaveText("test url");
    await contains(".o_clipboard_button").click();
    await animationFrame();
    expect.verifySteps(["test url"]);
});

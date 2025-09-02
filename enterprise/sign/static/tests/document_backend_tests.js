/** @odoo-module **/

import { getFixture, nextTick, patchWithCleanup, click } from "@web/../tests/helpers/utils";
import { doAction } from "@web/../tests/webclient/helpers";
import { createDocumentWebClient, actionId, defaultMockRPC } from "./action_utils";
import { signInfoService } from "@sign/services/sign_info_service";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";


let serverData;
let config;
let target;

QUnit.module("document_backend_tests", ({ beforeEach }) => {
    beforeEach(() => {
        const data = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    template_id: {
                        string: "Template",
                        type: "many2one",
                        relation: "sign.template",
                    },
                },
                records: [
                    {
                        id: 1,
                        display_name: "some record",
                        template_id: 1,
                    },
                ],
            },
            "sign.template": {
                fields: {
                    display_name: { string: "Template Name", type: "char" },
                },
                records: [
                    {
                        id: 1,
                        display_name: "some template",
                    },
                ],
            },
        };
        serverData = { models: data };
        target = getFixture();
        config = {
            tag: "sign.Document",
        };
        registry.category("services").add("signInfo", signInfoService);
    });

    QUnit.test("simple rendering", async function (assert) {
        assert.expect(9);
        patchWithCleanup(user, { userId: 1 });

        const getDataFromHTML = () => {
            assert.step("getDataFromHTML");
        };

        config = {
            ...config,
            getDataFromHTML,
            actionContext: {
                need_to_sign: true,
            },
            mockRPC: (route) => {
                if (route === "/web/dataset/call_kw/sign.request.item/send_signature_accesses") {
                    assert.step("send_messages");
                    return true;
                } else {
                    return defaultMockRPC(route);
                }
            },
        };

        const webClient = await createDocumentWebClient(config, serverData);
        await doAction(webClient, actionId);
        await nextTick();

        assert.verifySteps(["getDataFromHTML"]);

        assert.strictEqual(
            target.querySelector(".o_sign_document").innerText.trim(),
            "def",
            "should display text from server"
        );

        assert.containsN(target, ".o_sign_resend_access_button", 2);
        assert.strictEqual(
            target.querySelectorAll(".o_sign_resend_access_button")[0].textContent,
            "Resend"
        );
        assert.strictEqual(
            target.querySelectorAll(".o_sign_resend_access_button")[1].textContent,
            "Send"
        );
        assert.containsOnce(target, ".o_sign_sign_directly");

        // click on resend
        await click(target.querySelectorAll(".o_sign_resend_access_button")[0]);
        assert.verifySteps(["send_messages"]);
    });

    QUnit.test("render shared document", async function (assert) {
        assert.expect(3);

        config = {
            ...config,
            actionContext: {
                need_to_sign: true,
                state: "shared",
            },
        };

        const webClient = await createDocumentWebClient(config, serverData);
        await doAction(webClient, actionId);

        assert.strictEqual(
            target.querySelector(".o_sign_document").innerText.trim(),
            "def",
            "should display text from server"
        );

        assert.containsN(target, ".o_sign_resend_access_button", 0);
        assert.containsOnce(target, ".o_sign_sign_directly");
    });

    QUnit.test("do not crash when leaving the action", async function (assert) {
        assert.expect(3);

        config.mockRPC = (route) => {
            if (route === "/sign/get_document/5/abc") {
                assert.step(route);
                return Promise.resolve({
                    html: `
                    <span>
                        def
                        <div class='o_sign_cp_pager'></div>
                    </span>
                    <iframe srcdoc="" class="o_iframe o_sign_pdf_iframe"/>`,
                    context: {},
                });
            }
        };

        const webClient = await createDocumentWebClient(config, serverData);
        await doAction(webClient, actionId);
        await doAction(webClient, actionId);

        assert.verifySteps(["/sign/get_document/5/abc", "/sign/get_document/5/abc"]);
    });

    QUnit.test("show download buttons when state is signed", async (assert) => {
        assert.expect(4);

        config.actionContext = { state: "signed" };

        const webClient = await createDocumentWebClient(config, serverData);

        await doAction(webClient, actionId);

        assert.containsOnce(target, ".o_sign_download_document_button");
        assert.containsOnce(target, ".o_sign_download_log_button");
        assert.ok(
            target
                .querySelector(".o_sign_download_document_button")
                .href.includes("/sign/download/5/abc/completed"),
            "should have correct download URL"
        );
        assert.ok(
            target
                .querySelector(".o_sign_download_log_button")
                .href.includes("/sign/download/5/abc/log"),
            "should have correct download URL"
        );
    });
});

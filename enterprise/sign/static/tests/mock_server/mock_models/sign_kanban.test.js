import { assertSteps, defineMailModels, startServer, step } from "@mail/../tests/mail_test_helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { SignTemplate, SignTemplateTag } from "@sign/../tests/mock_server/mock_models/sign_model";
import { dragoverFiles, dropFiles } from "@web/../tests/utils";
import { defineModels, mountView, onRpc } from "@web/../tests/web_test_helpers";

defineMailModels();
defineModels([SignTemplate, SignTemplateTag]);

describe.current.tags("desktop");

let pyEnv;

beforeEach(async () => {
    pyEnv = await startServer();
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "yop.pdf",
        res_model: "sign.template",
        mimetype: "application/pdf",
    });
    pyEnv["sign.template"].write(1, {
        attachment_id: attachmentId,
    });
});

test("Drop to upload file in kanban", async () => {
    await mountView({
        type: "kanban",
        resModel: "sign.template",
        arch: `
        <kanban js_class="sign_kanban" class="o_sign_template_kanban">
            <templates>
                <t t-name="card">
                    <field name="display_name" class="fw-bolder fs-5"/>
                </t>
            </templates>
        </kanban>`,
    });
    expect(".o_dropzone").toHaveCount(0);
    const file = new File(["test"], "test.pdf", { type: "application/pdf" });
    const fileInput = document.querySelector(".o_sign_template_file_input");
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    fileInput.files = dataTransfer.files;
    await dragoverFiles(".o_content", dataTransfer.files);
    await dropFiles(".o_dropzone", dataTransfer.files);
    onRpc("/web/dataset/call_kw/sign.template/create_with_attachment_data", async (request) => {
        step("attachment create");
        const values = await request.json();
        if (values.params.method === "create_with_attachment_data") {
            expect(values.params.model).toBe("sign.template");
            expect(values.params.args.length).toBe(3);
            const attachmentID = pyEnv["ir.attachment"].create({
                name: values.params.args[0],
                res_model: values.params.model,
                datas: values.params.args[1],
            });
            const signTemplate = pyEnv[values.params.model].create({
                attachment_id: attachmentID,
                active: true,
            });
            return signTemplate;
        }
    });
    expect(".o_dropzone").toHaveCount(1);
    await assertSteps(["attachment create"]);
});

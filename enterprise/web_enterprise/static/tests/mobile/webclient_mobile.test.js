import { describe, expect, test } from "@odoo/hoot";
import { click, queryFirst } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    defineActions,
    defineModels,
    getService,
    fields,
    models,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { WebClientEnterprise } from "@web_enterprise/webclient/webclient";

class Partner extends models.Model {
    name = fields.Char();

    _records = [
        { id: 1, name: "First record" },
        { id: 2, name: "Second record" },
    ];
    _views = {
        "form,false": `
            <form>
                <group>
                    <field name="name"/>
                </group>
            </form>
        `,
        "kanban,false": `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="name"/>
                    </t>
                </templates>
            </kanban>
        `,
        "list,false": `<list><field name="name"/></list>`,
        "search,false": `<search/>`,
    };
}

defineModels([Partner]);

defineActions([
    {
        id: 1,
        xml_id: "action_1",
        name: "Partners Action 1",
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[1, "kanban"]],
    },
    {
        id: 3,
        xml_id: "action_3",
        name: "Partners",
        res_model: "partner",
        mobile_view_mode: "kanban",
        type: "ir.actions.act_window",
        views: [
            [false, "list"],
            [1, "kanban"],
            [false, "form"],
        ],
    },
]);

describe.current.tags("mobile");

test("scroll position is kept", async () => {
    // This test relies on the fact that the scrollable element in mobile
    // is view's root node.
    const record = Partner._records[0];
    Partner._records = [];

    for (let i = 0; i < 80; i++) {
        const rec = Object.assign({}, record);
        rec.id = i + 1;
        rec.name = `Record ${rec.id}`;
        Partner._records.push(rec);
    }

    // force the html node to be scrollable element
    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();

    // partners in list/kanban
    await getService("action").doAction(3);
    expect(".o_kanban_view").toHaveCount(1);

    queryFirst(".o_kanban_view").scrollTo(0, 123);
    await click(".o_kanban_record:eq(20)");
    await animationFrame();
    expect(".o_form_view").toHaveCount(1);
    expect(".o_kanban_view").toHaveCount(0);

    await click(".o_breadcrumb .o_back_button");
    await animationFrame();
    expect(".o_form_view").toHaveCount(0);
    expect(".o_kanban_view").toHaveCount(1);
});

test("Share URL item is not present in the user menu when screen is small", async () => {
    patchWithCleanup(browser, {
        matchMedia: (media) => {
            if (media === "(display-mode: standalone)") {
                return { matches: true };
            }
            return this.super();
        },
    });

    await mountWithCleanup(UserMenu);
    expect(".o_user_menu").toHaveCount(1);
    queryFirst(".o_user_menu").classList.remove("d-none");
    await click(".o_user_menu button");
    await animationFrame();
    expect(".o_user_menu .dropdown-item").toHaveCount(0, {
        message: "share button is not visible",
    });
});

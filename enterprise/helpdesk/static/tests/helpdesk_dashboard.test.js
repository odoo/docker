import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

import { defineHelpdeskModels, helpdeskModels } from "@helpdesk/../tests/helpdesk_test_helpers";

const { ResPartner, ResUsers } = helpdeskModels;

describe.current.tags("desktop");
defineHelpdeskModels();

const mountViewParams = {
    resModel: "helpdesk.team",
    type: "kanban",
    arch: `
        <kanban js_class="helpdesk_team_kanban_view">
            <templates>
                <t t-name="card">
                    <field name="name"/>
                </t>
            </templates>
        </kanban>
    `,
};

beforeEach(() => {
    this.dashboardData = {
        "7days": { count: 0, rating: 0, success: 0 },
        helpdesk_target_closed: 12,
        helpdesk_target_rating: 0,
        helpdesk_target_success: 0,
        my_all: { count: 0, hours: 0, failed: 0 },
        my_high: { count: 0, hours: 0, failed: 0 },
        my_urgent: { count: 0, hours: 0, failed: 0 },
        rating_enable: false,
        show_demo: false,
        success_rate_enable: false,
        today: { count: 0, rating: 0, success: 0 },
    };
});

onRpc(({ method, model, args }) => {
    if (model === "helpdesk.team" && method === "retrieve_dashboard") {
        return this.dashboardData;
    } else if (method === "check_modules_to_install") {
        expect.step(method);
        expect(args[0]).toEqual(["use_sla"]);
        return false;
    } else if (method === "web_save") {
        expect.step(method);
    } else if (model === "res.users" && method === "write") {
        expect(true).toBe(true, { message: "should modify helpdesk_target_closed" });
        this.dashboardData.helpdesk_target_closed = args[1].helpdesk_target_closed;
        return true;
    }
});

test("dashboard basic rendering", async () => {
    await mountView(mountViewParams);
    expect("div.o_helpdesk_content").toHaveCount(1, {
        message: "should render the dashboard",
    });
    expect(".o_helpdesk_content > .o_helpdesk_banner").toHaveCount(1, {
        message: "dashboard should be sibling of renderer element",
    });
    expect(".o_target_to_set").toHaveText("12");
});

test("edit the target", async () => {
    ResUsers._fields.helpdesk_target_closed = fields.Integer({
        string: "helpdesk target closed",
        default: 1,
    });
    Object.assign(ResUsers._records, {
        id: 1,
        name: "Pierre",
        helpdesk_target_closed: 0,
    });

    await mountView(mountViewParams);
    await click(".o_target_to_set:nth-child(1)");
    expect("o_target_to_set").toHaveCount(0, {
        message: "The first one should be an input since the user clicked on it.",
    });
    await click(".o_target_to_set:nth-child(1)");
    await click(".o_target_to_set");
    expect("o_target_to_set").toHaveCount(0, {
        message: "The first one should be an input since the user clicked on it.",
    });
    await animationFrame();
    expect(".o_helpdesk_banner .o_helpdesk_banner_table td > input").toHaveCount(1, {
        message: "The input should be rendered instead of the span.",
    });
    await contains(".o_helpdesk_banner .o_helpdesk_banner_table td > input").edit("1200");
    expect(".o_helpdesk_banner .o_helpdesk_banner_table td > input").toHaveCount(0, {
        message:
            "The input should no longer be rendered since the user finished the edition by pressing Enter key.",
    });
    expect(".o_target_to_set > div:contains('1,200')").toHaveCount(1, {
        message: "should have correct targets",
    });
});

test("dashboard rendering with empty many2one", async () => {
    // add an empty many2one
    class HelpdeskPartner extends models.Model {
        _name = "helpdesk.partner";

        name = fields.Char({ string: "Name" });
    }
    defineModels([HelpdeskPartner]);
    ResPartner._fields.helpdesk_partner_id = fields.Many2one({
        string: "Partner",
        relation: "helpdesk.partner",
    });
    Object.assign(ResPartner._records, {
        id: 1,
        name: "Pierre",
        helpdesk_partner_id: false,
    });
    Object.assign(ResUsers._records, {
        id: 1,
        name: "Pierre",
        partner_id: 1,
    });

    await mountView(mountViewParams);
    expect("div.o_helpdesk_content").toHaveCount(1, {
        message: "should render the dashboard",
    });
});

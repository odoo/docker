/** @odoo-module **/

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { mountInFixture } from "@web/../tests/helpers/mount_in_fixture";
import { click, getFixture, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { getActionManagerServerData } from "@web/../tests/webclient/helpers";
import { browser } from "@web/core/browser/browser";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { ormService } from "@web/core/orm_service";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { actionService } from "@web/webclient/actions/action_service";
import { menuService } from "@web/webclient/menus/menu_service";
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { createEnterpriseWebClient } from "@web_enterprise/../tests/helpers";
import { enterpriseSubscriptionService } from "@web_enterprise/webclient/home_menu/enterprise_subscription_service";
import { homeMenuService } from "@web_enterprise/webclient/home_menu/home_menu_service";
import { shareUrlMenuItem } from "@web_enterprise/webclient/share_url/share_url";

let serverData;
let fixture;
const serviceRegistry = registry.category("services");

// Should test ONLY the webClient and features present in Enterprise
// Those tests rely on hidden view to be in CSS: display: none
QUnit.module("WebClient Enterprise", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        fixture = getFixture();
        serviceRegistry.add("home_menu", homeMenuService);
        serviceRegistry.add("orm", ormService);
        serviceRegistry.add("enterprise_subscription", enterpriseSubscriptionService);
        serviceRegistry.add("popover", popoverService);
    });

    QUnit.test(
        "underlying action's menu items are invisible when HomeMenu is displayed",
        async function (assert) {
            serverData.menus[1].children = [99];
            serverData.menus[99] = {
                id: 99,
                children: [],
                name: "SubMenu",
                appID: 1,
                actionID: 1002,
                xmlid: "",
                webIconData: undefined,
                webIcon: false,
            };
            await createEnterpriseWebClient({ fixture, serverData });
            assert.containsNone(fixture, "nav .o_menu_sections");
            assert.containsNone(fixture, "nav .o_menu_brand");
            await click(fixture.querySelector(".o_app.o_menuitem:nth-child(1)"));
            await nextTick();
            assert.containsOnce(fixture, "nav .o_menu_sections");
            assert.containsOnce(fixture, "nav .o_menu_brand");
            assert.isVisible(fixture.querySelector(".o_menu_sections"));
            assert.isVisible(fixture.querySelector(".o_menu_brand"));
            await click(fixture.querySelector(".o_menu_toggle"));
            assert.containsOnce(fixture, "nav .o_menu_sections");
            assert.containsOnce(fixture, "nav .o_menu_brand");
            assert.isNotVisible(fixture.querySelector(".o_menu_sections"));
            assert.isNotVisible(fixture.querySelector(".o_menu_brand"));
        }
    );

    QUnit.test(
        "Share URL item is present in the user menu when running as PWA",
        async function (assert) {
            patchWithCleanup(browser, {
                matchMedia: (media) => {
                    if (media === "(display-mode: standalone)") {
                        return { matches: true };
                    } else {
                        this._super();
                    }
                },
            });

            serviceRegistry.add("hotkey", hotkeyService);
            serviceRegistry.add("action", actionService);
            serviceRegistry.add("menu", menuService);

            const env = await makeTestEnv();

            registry.category("user_menuitems").add("share_url", shareUrlMenuItem);
            await mountInFixture(UserMenu, fixture, { env });
            await click(fixture.querySelector(".o_user_menu button"));
            assert.containsOnce(fixture, ".o-dropdown--menu .dropdown-item");
            assert.strictEqual(
                fixture.querySelector(".o-dropdown--menu .dropdown-item span").textContent,
                "Share",
                "share button is visible"
            );
        }
    );

    QUnit.test(
        "Share URL item is not present in the user menu when not running as PWA",
        async function (assert) {
            patchWithCleanup(browser, {
                matchMedia: (media) => {
                    if (media === "(display-mode: standalone)") {
                        return { matches: false };
                    } else {
                        this._super();
                    }
                },
            });

            serviceRegistry.add("hotkey", hotkeyService);
            serviceRegistry.add("action", actionService);
            serviceRegistry.add("menu", menuService);

            const env = await makeTestEnv();

            registry.category("user_menuitems").add("share_url", shareUrlMenuItem);
            await mountInFixture(UserMenu, fixture, { env });
            await click(fixture.querySelector(".o_user_menu button"));
            assert.containsNone(
                fixture,
                ".o-dropdown--menu .dropdown-item",
                "share button is not visible"
            );
        }
    );
});

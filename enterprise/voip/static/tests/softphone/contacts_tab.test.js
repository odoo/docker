import { describe, test } from "@odoo/hoot";
import { click, contains, insertText, start, startServer } from "@mail/../tests/mail_test_helpers";
import { setupVoipTests } from "@voip/../tests/voip_test_helpers";

describe.current.tags("desktop");
setupVoipTests();

test("Partners with a phone number are displayed in Contacts tab", async () => {
    const pyEnv = await startServer();
    pyEnv["res.partner"].create([
        { name: "Michel Landline", phone: "+1-307-555-0120" },
        { name: "Maxim Mobile", mobile: "+257 114 7579" },
        { name: "Patrice Nomo" },
    ]);
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".nav-link", { text: "Contacts" });
    await contains(".o-voip-ContactsTab .list-group-item-action", { count: 2 });
    await contains(".o-voip-ContactsTab b", { text: "Michel Landline" });
    await contains(".o-voip-ContactsTab b", { text: "Maxim Mobile" });
    await contains(".o-voip-ContactsTab b", { text: "Patrice Nomo", count: 0 });
});

test("Typing in the search bar fetches and displays the matching contacts", async () => {
    const pyEnv = await startServer();
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".nav-link", { text: "Contacts" });
    pyEnv["res.partner"].create([
        { name: "Morshu RTX", phone: "+61-855-527-77" },
        { name: "Gargamel", mobile: "+61-855-583-671" },
    ]);
    await insertText("input[placeholder=Search]", "Morshu");
    await contains(".o-voip-ContactsTab b", { text: "Morshu RTX" });
    await contains(".o-voip-ContactsTab b", { text: "Gargamel", count: 0 });
});

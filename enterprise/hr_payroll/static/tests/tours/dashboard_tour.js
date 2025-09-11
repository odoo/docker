/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { queryAll } from "@odoo/hoot-dom";

registry.category("web_tour.tours").add('payroll_dashboard_ui_tour', {
    url: '/odoo',
    steps: () => [
    stepUtils.showAppsMenuItem(),
    {
        content: "Open payroll app",
        trigger: '.o_app[data-menu-xmlid="hr_work_entry_contract_enterprise.menu_hr_payroll_root"]',
        run: "click",
    },
    {
        content: "Employees without running contracts",
        trigger: 'a:contains("Employees Without Running Contracts")',
        run: "click",
    },
    {
        content: "Open employee profile",
        trigger: 'tr.o_data_row td[name="name"]',
        run: "click",
    },
    {
        content: "Open new contract form",
        trigger: 'button[name="action_open_contract"]',
        run: "click",
    },
    {
        content: "Save contract with no data",
        trigger: "button.o_form_button_save:enabled",
        run: "click",
    },
    {
        content: "Input contract name",
        trigger: '.o_field_char[name="name"] input',
        id: "input_contract_name",
        run: "edit Laurie's Contract",
    },
    {
        content: "Save contract",
        trigger: "button.o_form_button_save:enabled",
        run: "click",
    },
    {
        content: "Set contract as running",
        trigger: 'button[data-value="open"]',
        run: "click",
    },
    {
        content: "Go back to dashboard",
        trigger: 'a[data-menu-xmlid="hr_payroll.menu_hr_payroll_dashboard_root"]',
        run: "click",
    },
    {
        content: "Check that the no contract error is gone",
        trigger: 'h2:contains("Warning")',
        run: function(actions) {
            const errors = queryAll('.o_hr_payroll_dashboard_block div.row div.col a:contains("Employees Without Running Contracts")').length;
            if (errors) {
                console.error("There should be no no running contract issue on the dashboard");
            }
        },
    },
    {
        content: "Create a new note",
        trigger: 'button.o_hr_payroll_todo_create',
        run: "click",
    },
    {
        content: "Set a name",
        trigger: 'li.o_hr_payroll_todo_tab input',
        run: "edit Dashboard Todo List && click body",
    },
    {
        trigger: "li.o_hr_payroll_todo_tab a.active:contains(Dashboard Todo List)",
    },
    {
        content: "Edit the note in dashboard view",
        trigger: 'div.o_hr_payroll_todo_value',
        run: 'click',
    },
    {
        content: "Write in the note",
        trigger: ".note-editable.odoo-editor-editable",
        run: "editor Todo List",
    }
]});

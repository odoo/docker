/** @odoo-module */

import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

export const timerHelpdeskService = {
    dependencies: ["orm"],
    async: [
        "fetchHelpdeskProjects",
    ],
    start(env, { orm }) {
        let helpdeskProjects;
        return {
            async fetchHelpdeskProjects() {
                const isHelpdeskUser = await user.hasGroup("helpdesk.group_helpdesk_user");
                if (!isHelpdeskUser) {
                    return [];
                }
                const result = await orm.readGroup(
                    "helpdesk.ticket",
                    [["project_id", "!=", false]],
                    ["project_id"],
                    ["project_id"],
                );
                if (result?.length) {
                    helpdeskProjects = result.map((r) => r.project_id[0]);
                }
            },
            get helpdeskProjects() {
                return helpdeskProjects;
            },
            invalidateCache() {
                helpdeskProjects = undefined;
            }
        };
    }
};

registry.category('services').add('helpdesk_timer_header', timerHelpdeskService);

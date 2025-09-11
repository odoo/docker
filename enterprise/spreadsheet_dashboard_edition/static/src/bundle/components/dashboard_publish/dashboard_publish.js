import { Component, useState } from "@odoo/owl";
import { registries } from "@spreadsheet/o_spreadsheet/o_spreadsheet";
import { CheckBox } from "@web/core/checkbox/checkbox";

const { topbarComponentRegistry } = registries;

export class DashboardPublish extends Component {
    static template = "spreadsheet_edition.DashboardPublish";
    static components = { CheckBox };
    static props = {};

    setup() {
        this.state = useState({ isPublished: this.env.isDashboardPublished() });
    }

    get isReadonly() {
        return this.env.isRecordReadonly();
    }

    toggleDashboardPublished() {
        if (this.isReadonly) {
            return;
        }
        this.state.isPublished = !this.state.isPublished;
        this.env.toggleDashboardPublished(this.state.isPublished);
    }
}

topbarComponentRegistry.add("dashboard_publish", {
    component: DashboardPublish,
    isVisible: (env) => env.isDashboardPublished,
    sequence: 15,
});

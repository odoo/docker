/** @odoo-module */

import { Component, useState } from "@odoo/owl";

export class AccountReportButtonsBar extends Component {
    static template = "account_reports.AccountReportButtonsBar";
    static props = {};

    setup() {
        this.controller = useState(this.env.controller);
    }

    //------------------------------------------------------------------------------------------------------------------
    // Buttons
    //------------------------------------------------------------------------------------------------------------------
    get mainButton() {
        for (const button of this.controller.buttons) {
            if (!button.always_show) {
                return button;  // other always_show buttons are displayed in the cog menu
            }
        }
        return null;
    }

    get singleButtons() {
        const buttons= [];

        for (const button of this.controller.buttons)
            if (button.always_show)
                buttons.push(button);

        return buttons;
    }
}

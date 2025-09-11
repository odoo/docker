/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, useRef } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class InitialsAllPagesDialog extends Component {
    static template = "sign.InitialsAllPagesDialog";
    static components = {
        Dialog,
    };
    static props = {
        addInitial: Function,
        close: Function,
        roles: Object,
        responsible: Number,
        pageCount: Number,
    };

    setup() {
        this.selectRef = useRef("role_select");
    }

    get currentRole() {
        return parseInt(this.selectRef.el?.value);
    }

    onAddOnceClick() {
        this.props.addInitial(this.currentRole, false);
        this.props.close();
    }

    onAddToAllPagesClick() {
        this.props.addInitial(this.currentRole, true);
        this.props.close();
    }

    get dialogProps() {
        return {
            size: "md",
            title: _t("Add Initials"),
        };
    }
}

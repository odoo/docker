/* @odoo-module */

import { Component, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("@mail/core/web/activity_model").Activity} activity
 * @extends {Component<Props, Env>}
 */
export class Approval extends Component {
    static template = "approvals.Approval";
    static props = {
        activity: Object,
        onChange: Function,
    };

    setup() {
        this.store = useState(useService("mail.store"));
    }

    async onClickApprove() {
        await this.env.services.orm.call("approval.approver", "action_approve", [
            this.props.activity.approval.id,
        ]);
        this.props.activity.remove();
        this.props.onChange();
    }

    async onClickRefuse() {
        await this.env.services.orm.call("approval.approver", "action_refuse", [
            this.props.activity.approval.id,
        ]);
        this.props.activity.remove();
        this.props.onChange();
    }
}

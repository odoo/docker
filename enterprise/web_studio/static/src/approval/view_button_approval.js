import { useSubEnv } from "@odoo/owl";
import { rpcBus } from "@web/core/network/rpc";
import { UPDATE_METHODS } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { ViewButton } from "@web/views/view_button/view_button";
import { useApproval } from "@web_studio/approval/approval_hook";
import { StudioApproval } from "@web_studio/approval/studio_approval";

registry.category("services").add("clear_caches_on_approval_rules_change", {
    start(env) {
        rpcBus.addEventListener("RPC:RESPONSE", (ev) => {
            const { model, method } = ev.detail.data.params;
            if (["studio.approval.rule"].includes(model) && UPDATE_METHODS.includes(method)) {
                env.bus.trigger("CLEAR-CACHES");
            }
        });
    },
});

patch(ViewButton.prototype, {
    setup() {
        super.setup(...arguments);
        if (this._shouldUseApproval()) {
            let { type, name } = this.props.clickParams;
            if (type && type.endsWith("=")) {
                type = type.slice(0, -1);
            }
            const action = type === "action" && name;
            const method = type === "object" && name;
            this.approval = useApproval({
                getRecord: (props) => props.record,
                action,
                method,
            });

            const onClickViewButton = this.env.onClickViewButton;
            useSubEnv({
                onClickViewButton: (params) => {
                    if (params.clickParams.type === "action") {
                        // if the button is an action then we check the approval client side
                        params.beforeExecute = this.checkBeforeExecute.bind(this);
                    }
                    onClickViewButton(params);
                },
            });
        }
    },

    _shouldUseApproval() {
        const { name } = this.props.clickParams || {};
        const { resModel } = this.props.record || {};
        return name && resModel && this.env.hasApprovalRules?.[resModel];
    },

    async checkBeforeExecute() {
        this.approval.willCheck = true;
        if (!this.approval.resId) {
            const model = this.props.record.model;
            const rec = "resId" in model.root ? model.root : this.props.record;
            await rec.save();
        } else if (this.props.record && this.props.record.isDirty) {
            await this.props.record.save();
        }
        return this.approval.checkApproval();
    },
});

ViewButton.props.push("studioApproval?");
ViewButton.components = Object.assign(ViewButton.components || {}, { StudioApproval });

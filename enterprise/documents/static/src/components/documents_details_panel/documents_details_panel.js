import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { formatFloat } from "@web/core/utils/numbers";
import { CharField } from "@web/views/fields/char/char_field";
import { Many2OneAvatarField } from "@web/views/fields/many2one_avatar/many2one_avatar_field";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";

import { Component, onWillRender, reactive } from "@odoo/owl";

const COMPANY_ROOT_OWNER_ID = 1;

export class DocumentsDetailsPanel extends Component {
    static components = {
        CharField,
        Many2OneAvatarField,
        Many2OneField,
        Many2ManyTagsField,
    };
    static props = {
        record: { type: Object, optional: true },
        nbViewItems: { type: Number, optional: true },
    };
    static template = "documents.DocumentsDetailsPanel";

    setup() {
        this.action = useService("action");
        this.documentService = useService("document.document");
        this.orm = useService("orm");
        onWillRender(() => {
            this.record = reactive(this.props.record || {}, async () => {
                if (this.props.record?.data?.type === "folder") {
                    return this.env.searchModel._reloadSearchModel(true);
                }
            });
        });
    }

    async openLinkedRecord() {
        const { res_model, res_id } = this.record.data || {};
        if (!res_id?.resId || !res_model) {
            return;
        }
        return this.action.doAction({
            type: "ir.actions.act_window",
            res_id: res_id.resId,
            res_model,
            views: [[false, "form"]],
            target: "current",
        });
    }

    get userPermissionViewOnly() {
        return this.record.data?.user_permission !== "edit";
    }

    get fileSize() {
        if (this.record.data?.type !== "folder" || this.props.record.isContainer) {
            const nBytes = this.record.data.file_size || 0;
            if (nBytes) {
                return `${this.record.isContainer ? '~' : ''}${formatFloat(nBytes, { humanReadable: true })}B`;
            }
        }
        return "";
    }

    get rootFolderPlaceholder() {
        return this.props.record.data?.owner_id[0] === user.userId
            ? _t("My Drive")
            : this.props.record.data?.owner_id[0] === COMPANY_ROOT_OWNER_ID
                ? _t("Company")
                : _t("Shared with me");
    }
}

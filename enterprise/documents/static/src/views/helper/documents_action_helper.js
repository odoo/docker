/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";
import { Component, markup, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { escape } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";

export class DocumentsActionHelper extends Component {
    static template = "documents.DocumentsActionHelper";
    static props = [
        "noContentHelp", // Markup Object
    ];

    setup() {
        this.orm = useService("orm");
        this.hasShareReadAccessRights = undefined;
        this.state = useState({
            mailTo: undefined,
        });
        onWillStart(async () => {
            await this.updateShareInformation();
        });
        onWillUpdateProps(async () => {
            await this.updateShareInformation();
        });
    }

    get selectedFolderId() {
        return this.env.searchModel.getSelectedFolderId();
    }

    /**
     * @returns {markup} If the current folder is an actual folder, the action's helper,
     * otherwise a message depending on it being the "All" folder or the "Trash" folder
     */
    get noContentHelp() {
        if (!this.selectedFolderId || ["RECENT", "SHARED", "TRASH", "MY"].includes(this.selectedFolderId)) {
            return markup(
                `<p class='o_view_nocontent_smiling_face'>
                    ${escape(
                        this.selectedFolderId === "TRASH"
                            ? _t("Documents moved to trash will show up here")
                            : this.selectedFolderId === "RECENT" 
                                ? _t("Recently accessed Documents will show up here")
                                : this.selectedFolderId === "SHARED"
                                ? _t("Documents shared with you will appear here")
                                : this.selectedFolderId === "MY"
                                    ? _t("Your personal space")
                                    : _t("Select a folder to upload a document")
                    )}
                </p>`
            );
        }
        return this.props.noContentHelp;
    }

    async updateShareInformation() {
        this.state.mailTo = undefined;
        // Only load data if we are in a single folder.
        let domain = this.env.searchModel.domain.filter(
            (leaf) => Array.isArray(leaf) && leaf.includes("folder_id")
        );
        if (domain.length !== 1) {
            return;
        }
        // make sure we have a mail.alias configured
        domain = Domain.and([domain, [["type", "=", "folder"]], [["alias_name", "!=", false]]]).toList();
        if (this.hasShareReadAccessRights === undefined) {
            this.hasShareReadAccessRights = false;
        }
        if (!this.hasShareReadAccessRights) {
            return;
        }
        const folders = await this.orm.searchRead("documents.document", domain, ["id", "alias_id"], {
            limit: 1,
        });
        if (folders.length) {
            this.state.mailTo = folders[0].alias_id[1];
        }
    }
}

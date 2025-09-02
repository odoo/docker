import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { STATIC_COG_GROUP_ACTION_PIN } from "./documents_cog_menu_group";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { _t } from "@web/core/l10n/translation";

export class DocumentCogMenuPinAction extends Component {
    static template = "documents.DocumentCogMenuPinAction";
    static components = { Dropdown };
    static props = {};

    static isVisible({ config, searchModel, services }, isVisibleAdditional = false) {
        if (!(config && searchModel && searchModel.resModel === "documents.document" && services)) {
            return false;
        }
        const folder = searchModel?.getSelectedFolder();
        const documentService = services["document.document"];
        return (
            folder &&
            documentService &&
            ["kanban", "list"].includes(config.viewType) &&
            (!isVisibleAdditional ||
                isVisibleAdditional({ folder, config, searchModel, documentService }))
        );
    }

    setup() {
        this.action = useService("action");
        this.documentService = useService("document.document");
        this.notification = useService("notification");

        this.documentsState = useState({ actions: null });

        onWillStart(async () => {
            const folderId = this.env.searchModel.getSelectedFolderId();
            this.documentsState.actions = await this.documentService.getActions(folderId);
        });
    }

    async onEnableAction(actionId) {
        const currentFolderId = this.env.searchModel.getSelectedFolderId();
        if (!currentFolderId || typeof currentFolderId !== "number") {
            this.notification.add(_t("You can not pin actions for that folder."), {
                type: "warning",
            });
            return;
        }

        this.documentsState.actions = await this.documentService.enableAction(
            currentFolderId,
            actionId
        );
        this.env.searchModel._reloadSearchModel(true);
    }
}

export const documentCogMenuPinAction = {
    Component: DocumentCogMenuPinAction,
    groupNumber: STATIC_COG_GROUP_ACTION_PIN,
    isDisplayed: (env) =>
        env.model.documentService.userIsDocumentUser &&
        DocumentCogMenuPinAction.isVisible(env, ({ folder, documentService }) =>
            documentService.isEditable(folder)
        )
};

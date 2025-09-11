import { STATIC_COG_GROUP_ACTION_ADVANCED } from "./documents_cog_menu_group";
import { DocumentsCogMenuItem } from "./documents_cog_menu_item";
import { _t } from "@web/core/l10n/translation";

export class DocumentsCogMenuItemDetails extends DocumentsCogMenuItem {
    setup() {
        this.icon = "fa-info-circle";
        this.label = _t("Info & Tags");
        super.setup();
    }

    async doActionOnFolder(folder) {
        await this.env.documentsView.bus.trigger("documents-toggle-chatter");
    }
}

export const documentsCogMenuItemDetails = {
    Component: DocumentsCogMenuItemDetails,
    groupNumber: STATIC_COG_GROUP_ACTION_ADVANCED,
    isDisplayed: (env) =>
        DocumentsCogMenuItem.isVisible(env, ({ folder }) => typeof folder.id === "number"),
};

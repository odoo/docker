/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from "@web/views/list/list_controller";
import { _t } from "@web/core/l10n/translation";

export const patchListControllerExportSelection ={
    getStaticActionMenuItems() {
        const list = this.model.root;
        const isM2MGrouped = list.groupBy.some((groupBy) => {
            const fieldName = groupBy.split(":")[0];
            return list.fields[fieldName].type === "many2many";
        });
        const menuItems = super.getStaticActionMenuItems(...arguments);
        menuItems["insert"] = {
            isAvailable: () => !isM2MGrouped,
            sequence: 15,
            icon: "oi oi-view-list",
            description: _t("Insert in spreadsheet"),
            callback: () => this.env.bus.trigger("insert-list-spreadsheet"),
        };
        return menuItems;
    },
};


export const unpatchListControllerExportSelection =  patch(ListController.prototype, patchListControllerExportSelection);

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { range } from "@web/core/utils/numbers";
import { WarningDialog } from "@web/core/errors/error_dialogs";

import { AbstractSpreadsheetAction } from "@spreadsheet_edition/bundle/actions/abstract_spreadsheet_action";

import { useSubEnv } from "@odoo/owl";
import { useSpreadsheetFieldSyncExtension } from "../field_sync_extension_hook";

export class SpreadsheetFieldSyncAction extends AbstractSpreadsheetAction {
    static template = "spreadsheet_sale_management.SpreadsheetFieldSyncAction";
    static path = "sale-order-spreadsheet";

    resModel = "sale.order.spreadsheet";
    threadField = "sale_order_spreadsheet_id";

    setup() {
        super.setup();
        this.notificationMessage = _t("New quote calculator created");
        useSubEnv({
            makeCopy: this.makeCopy.bind(this),
        });

        useSpreadsheetFieldSyncExtension();
    }

    async execInitCallbacks() {
        await super.execInitCallbacks();
        /**
         * Upon the first time we open the spreadsheet we want to resize the columns
         * of the main list to fit all the data.
         * The catch is we need to have the list data loaded to know the content and resize
         * the columns accordingly.
         */
        if (
            this.spreadsheetData.revisionId === "START_REVISION" &&
            this.stateUpdateMessages.length === 1
        ) {
            const list = this.model.getters.getMainSaleOrderLineList();
            const listDataSource = this.model.getters.getListDataSource(list.id);
            await listDataSource.load();
            this.model.dispatch("AUTORESIZE_COLUMNS", {
                sheetId: this.model.getters.getActiveSheetId(),
                cols: range(0, list.columns.length),
            });
        }
    }

    async writeToOrder() {
        const { commands, errors } = await this.model.getters.getFieldSyncX2ManyCommands();
        if (errors.length) {
            this.dialog.add(WarningDialog, {
                title: _t("Unable to save"),
                message: errors.join("\n\n"),
            });
        } else {
            await this.orm.write("sale.order", [this.orderId], {
                order_line: commands,
            });
            this.env.config.historyBack();
        }
    }

    /**
     * @override
     */
    _initializeWith(data) {
        super._initializeWith(data);
        this.orderId = data.order_id;
        const orderFilter = this.spreadsheetData.globalFilters?.find(
            (filter) => filter.modelName === "sale.order"
        );
        if (orderFilter && this.orderId) {
            orderFilter.defaultValue = [this.orderId];
        }
    }
}

registry
    .category("actions")
    .add("action_sale_order_spreadsheet", SpreadsheetFieldSyncAction, { force: true });

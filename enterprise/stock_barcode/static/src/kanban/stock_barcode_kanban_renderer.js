/** @odoo-module **/

import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { ManualBarcodeScanner } from "../components/manual_barcode";
import { user } from "@web/core/user";
import { useService } from '@web/core/utils/hooks';
import { onWillStart } from "@odoo/owl";

export class StockBarcodeKanbanRenderer extends KanbanRenderer {
    static template = "stock_barcode.KanbanRenderer";
    setup() {
        super.setup(...arguments);
        this.barcodeService = useService('barcode');
        this.dialogService = useService("dialog");
        this.resModel = this.props.list.model.config.resModel;
        this.displayTransferProtip = this.resModel === 'stock.picking';
        onWillStart(this.onWillStart);
    }

    openManualBarcodeDialog() {
        this.dialogService.add(ManualBarcodeScanner, {
            facingMode: "environment",
            onResult: (barcode) => {
                this.barcodeService.bus.trigger("barcode_scanned", { barcode });
            },
            onError: () => {},
        });
    }

    async onWillStart() {
        this.packageEnabled = await user.hasGroup('stock.group_tracking_lot');
        this.trackingEnabled = await user.hasGroup('stock.group_production_lot');
    }
}

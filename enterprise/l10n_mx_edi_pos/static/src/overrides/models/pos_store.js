import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async pay() {
        if (this.company.country_id?.code === "MX") {
            const currentOrder = this.get_order();
            const isRefund = currentOrder.lines.some((x) => x.refunded_orderline_id);
            if (
                (isRefund && currentOrder.lines.some((x) => x.price_subtotal > 0.0)) ||
                (!isRefund && currentOrder.amount_total < 0.0)
            ) {
                this.dialog.add(AlertDialog, {
                    title: _t("Error"),
                    body: _t(
                        "The amount of the order must be positive for a sale and negative for a refund."
                    ),
                });
                return;
            }
        }

        return super.pay(...arguments);
    },
});

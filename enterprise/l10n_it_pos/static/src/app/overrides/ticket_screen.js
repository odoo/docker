/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

patch(TicketScreen.prototype, {
    //@override
    async addAdditionalRefundInfo(order, destinationOrder) {
        if (this.pos.config.company_id.country_id.code !== "IT") {
            super.addAdditionalRefundInfo(...arguments);
        }
        destinationOrder.update({
            it_fiscal_receipt_number: order.it_fiscal_receipt_number,
            it_fiscal_receipt_date: order.it_fiscal_receipt_date,
            it_z_rep_number: order.it_z_rep_number,
        });
    },

    //@override
    async onDoRefund() {
        await super.onDoRefund(...arguments);
        if (this.pos.config.company_id.country_id.code === "IT") {
            this.pos.showScreen("PaymentScreen", { orderUuid: this.pos.selectedOrderUuid });
        }
    },
});

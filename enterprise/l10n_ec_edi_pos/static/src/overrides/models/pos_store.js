/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    // @Override
    async processServerData() {
        await super.processServerData();
        if (this.isEcuadorianCompany()) {
            this["l10n_latam.identification.type"] =
                this.models["l10n_latam.identification.type"].getFirst();
        }
    },
    isEcuadorianCompany() {
        return this.company.country_id?.code == "EC";
    },
    createNewOrder() {
        const order = super.createNewOrder(...arguments);
        if (!order.partner_id && this.isEcuadorianCompany()) {
            order.update({ partner_id: this.session._final_consumer_id });
        }
        return order;
    },
    // @Override
    // For EC, if the partner on the refund was End Consumer we need to allow the user to change it.
    async selectPartner() {
        if (!this.isEcuadorianCompany()) {
            return super.selectPartner(...arguments);
        }
        const currentOrder = this.get_order();
        if (!currentOrder) {
            return;
        }
        const currentPartner = currentOrder.get_partner();
        if (currentPartner && currentPartner.id === this.session._final_consumer_id) {
            this.dialog.add(PartnerList, {
                partner: currentPartner,
                getPayload: (newPartner) => currentOrder.set_partner(newPartner),
            });
            return currentPartner;
        }
        return super.selectPartner(...arguments);
    },
});

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(...arguments);
        if (this.company.country_id?.code == "EC") {
            this.to_invoice = true;
        }
    },
});

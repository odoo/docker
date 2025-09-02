import { PosStore } from "@point_of_sale/app/store/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
const { DateTime } = luxon;

patch(PosStore.prototype, {
    useBlackBoxSweden() {
        return !!this.config.iface_sweden_fiscal_data_module;
    },
    cashierHasPriceControlRights() {
        if (this.useBlackBoxSweden()) {
            return false;
        }
        return super.cashierHasPriceControlRights(...arguments);
    },
    disallowLineQuantityChange() {
        const result = super.disallowLineQuantityChange(...arguments);
        return this.useBlackBoxSweden() || result;
    },
    async push_single_order(order) {
        if (this.useBlackBoxSweden() && order) {
            if (!order.receipt_type) {
                order.receipt_type = "normal";
                order.sequence_number = await this.get_order_sequence_number();
            }
            try {
                order.blackbox_tax_category_a = order.get_specific_tax(25);
                order.blackbox_tax_category_b = order.get_specific_tax(12);
                order.blackbox_tax_category_c = order.get_specific_tax(6);
                order.blackbox_tax_category_d = order.get_specific_tax(0);
                const data = await this.pushOrderToSwedenBlackbox(order);
                if (data.value.error && data.value.error.errorCode != "000000") {
                    throw data.value.error;
                }
                this.setDataForPushOrderFromSwedenBlackBox(order, data);
            } catch (err) {
                this.env.services.dialog.add(AlertDialog, {
                    title: _t("Blackbox error"),
                    body: _t(err.status.message_title ? err.status.message_title : err.status),
                });
                return;
            }
        }
        return super.push_single_order(...arguments);
    },
    async pushOrderToSwedenBlackbox(order) {
        const fdm = this.hardwareProxy.deviceControllers.fiscal_data_module;
        const data = {
            date: new DateTime(order.date_order).toFormat("yyyyMMddHHmm"),
            receipt_id: order.sequence_number.toString(),
            pos_id: order.pos.config.id.toString(),
            organisation_number: this.company.company_registry,
            receipt_total: order.get_total_with_tax().toFixed(2).toString().replace(".", ","),
            negative_total:
                order.get_total_with_tax() < 0
                    ? Math.abs(order.get_total_with_tax()).toFixed(2).toString().replace(".", ",")
                    : "0,00",
            receipt_type: order.receipt_type,
            vat1: order.blackbox_tax_category_a
                ? "25,00;" + order.blackbox_tax_category_a.toFixed(2).replace(".", ",")
                : " ",
            vat2: order.blackbox_tax_category_b
                ? "12,00;" + order.blackbox_tax_category_b.toFixed(2).replace(".", ",")
                : " ",
            vat3: order.blackbox_tax_category_c
                ? "6,00;" + order.blackbox_tax_category_c.toFixed(2).replace(".", ",")
                : " ",
            vat4: order.blackbox_tax_category_d
                ? "0,00;" + order.blackbox_tax_category_d.toFixed(2).replace(".", ",")
                : " ",
        };

        return new Promise((resolve, reject) => {
            fdm.addListener((data) => (data.status === "ok" ? resolve(data) : reject(data)));
            fdm.action({
                action: "registerReceipt",
                high_level_message: data,
            });
        });
    },
    setDataForPushOrderFromSwedenBlackBox(order, data) {
        order.blackbox_signature = data.signature_control;
        order.blackbox_unit_id = data.unit_id;
    },
    async get_order_sequence_number() {
        return await this.data.call("pos.config", "get_order_sequence_number", [this.config.id]);
    },
    async get_profo_order_sequence_number() {
        return await this.data.call("pos.config", "get_profo_order_sequence_number", [
            this.config.id,
        ]);
    },
    getReceiptHeaderData(order) {
        const result = super.getReceiptHeaderData(...arguments);
        result.posIdentifier = this.config.name;
        if (order && this.useBlackBoxSweden()) {
            result.receipt_type = order.receipt_type;
            result.blackboxDate = order.blackbox_date;
            result.isReprint = order.isReprint;
            result.orderSequence = order.sequence_number;
            if (order.isReprint) {
                result.type = "COPY";
            } else if (order.isProfo) {
                result.type = "PRO FORMA";
            } else {
                result.type = (order.amount_total < 0 ? "return" : "") + "receipt";
            }
        }
        return result;
    },
});

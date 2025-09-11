/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    //@override
    export_for_printing() {
        return {
            ...super.export_for_printing(...arguments),
            l10n_ke_edi_oscu_pos_qrsrc: this.l10n_ke_edi_oscu_pos_qrsrc,
            l10n_ke_edi_oscu_pos_date: this.l10n_ke_edi_oscu_pos_date,
            l10n_ke_edi_oscu_pos_receipt_number: this.l10n_ke_edi_oscu_pos_receipt_number,
            l10n_ke_edi_oscu_pos_internal_data: this.l10n_ke_edi_oscu_pos_internal_data,
            l10n_ke_edi_oscu_pos_signature: this.l10n_ke_edi_oscu_pos_signature,
            l10n_ke_edi_oscu_pos_order_json: this.l10n_ke_edi_oscu_pos_order_json,
            l10n_ke_edi_oscu_pos_serial_number: this.l10n_ke_edi_oscu_pos_serial_number,
        };
    },

    wait_for_push_order() {
        return this.config_id.is_kenyan ? true : super.wait_for_push_order(...arguments);
    },
});

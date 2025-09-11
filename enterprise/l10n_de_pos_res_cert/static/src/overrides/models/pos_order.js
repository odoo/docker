import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    // @Override
    setup() {
        super.setup(...arguments);
        this.uiState = {
            ...this.uiState,
            fiskalyLinesSent: false,
        };
    },
    //@Override
    _updateTimeStart(seconds) {
        if (
            !(
                this.isCountryGermanyAndFiskaly() &&
                this.config.module_pos_restaurant &&
                this.l10n_de_fiskaly_time_start
            )
        ) {
            super._updateTimeStart(...arguments);
        }
    },
});

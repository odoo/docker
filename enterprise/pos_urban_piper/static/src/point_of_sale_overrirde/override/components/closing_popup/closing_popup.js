import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";

patch(ClosePosPopup.prototype, {
    /**
     * @override
     */
    async confirm() {
        await this.pos.updateStoreStatus();
        return super.confirm();
    },
});

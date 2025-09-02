import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { AddInfoPopup } from "@l10n_mx_edi_pos/app/add_info_popup/add_info_popup";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.isMxEdiPopupOpen = false;
    },
    //@override
    async toggleIsToInvoice() {
        if (this.pos.company.country_id?.code === "MX" && !this.currentOrder.is_to_invoice()) {
            const payload = await makeAwaitable(this.dialog, AddInfoPopup, {
                order: this.currentOrder,
            });
            if (payload) {
                this.currentOrder.l10n_mx_edi_cfdi_to_public =
                    payload.l10n_mx_edi_cfdi_to_public === true ||
                    payload.l10n_mx_edi_cfdi_to_public === "1";
                this.currentOrder.l10n_mx_edi_usage = payload.l10n_mx_edi_usage;
            } else {
                this.currentOrder.set_to_invoice(!this.currentOrder.is_to_invoice());
            }
        }
        super.toggleIsToInvoice(...arguments);
    },
    areMxFieldsVisible() {
        return this.pos.company.country_id?.code === "MX" && this.currentOrder.is_to_invoice();
    },
});

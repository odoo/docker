import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { onMounted } from "@odoo/owl";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        onMounted(async () => {
            const order = this.pos.get_order();
            if (this.pos.config.company_id.country_id.code === "IT" && !order.nb_print) {
                //make sure we only print the first time around
                await this.printReceipt();
                if (this.pos.config.it_fiscal_cash_drawer) {
                    await this.pos.fiscalPrinter.openCashDrawer();
                }
            }
        });
    },

    async printReceipt() {
        const order = this.pos.get_order();

        const result = order.to_invoice
            ? await this.pos.fiscalPrinter.printFiscalInvoice()
            : await this.pos.fiscalPrinter.printFiscalReceipt();

        if (result.success) {
            this.pos.data.write("pos.order", [order.id], {
                it_fiscal_receipt_number: result.addInfo.fiscalReceiptNumber,
                it_fiscal_receipt_date: result.addInfo.fiscalReceiptDate,
                it_z_rep_number: result.addInfo.zRepNumber,
                //update the number of times the order got printed, handling undefined
                nb_print: order.nb_print ? order.nb_print + 1 : 1,
            });
            return true;
        }
    },
});

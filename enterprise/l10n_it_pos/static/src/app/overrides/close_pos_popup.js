/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";

patch(ClosePosPopup.prototype, {
    downloadSalesReport() {
        if (this.pos.config.company_id.country_id.code !== "IT") {
            return super.downloadSalesReport();
        } else {
            return this.pos.fiscalPrinter.printXReport();
        }
    },
    async closeSession() {
        if (this.pos.config.company_id.country_id.code === "IT") {
            const zResult = await this.pos.fiscalPrinter.printZReport();
            if (!zResult.success) {
                // print XZ report if the Z report failed because of status 17.
                // It means we are in a test environment.
                // Fallback to print XZ report.
                if (zResult.status === "17") {
                    const xzResult = await this.pos.fiscalPrinter.printXZReport();
                    if (!xzResult.success) {
                        return;
                    }
                }
            }
        }
        return super.closeSession();
    },
});

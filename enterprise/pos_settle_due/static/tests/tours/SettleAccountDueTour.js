import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as PartnerList from "@point_of_sale/../tests/tours/utils/partner_list_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as Utils from "@point_of_sale/../tests/tours/utils/common";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("pos_settle_account_due", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.clickPartnerOptions("Partner Test 1"),
            {
                isActive: ["auto"],
                trigger: "div.o_popover :contains('Settle Due Accounts')",
                content: "Check the popover opened",
                run: "click",
            },
            Utils.selectButton("Bank"),
            PaymentScreen.clickValidate(),
            Utils.selectButton("Yes"),
            ProductScreen.closePos(),
            Dialog.confirm("Close Register"),
            {
                trigger: "body:not(:has(.modal))",
            },
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("SettleDueButtonPresent", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.clickPartnerOptions("A Partner"),
            PartnerList.checkDropDownItemText("Deposit money"),
            PartnerList.clickPartnerOptions("B Partner"),
            PartnerList.checkDropDownItemText("Settle due accounts"),
        ].flat(),
});

registry.category("web_tour.tours").add("pos_settle_account_due_update_instantly", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("A Partner"),
            ProductScreen.addOrderline("Desk Pad", "10"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Customer Account"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.clickPartnerButton(),
            {
                trigger: "tr:contains('A Partner') .partner-due:contains('19.80')",
            },
        ].flat(),
});

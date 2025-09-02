import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("FiskalyTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AA Test Partner"),
            ProductScreen.addOrderline("Coca-Cola", "1", "3"),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            Order.hasLine({
                productName: "Coca-Cola",
            }),
            ProductScreen.addOrderline("Coca-Cola", "1", "5"),
            ProductScreen.clickOrderButton(),
            ProductScreen.orderlinesHaveNoChange(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

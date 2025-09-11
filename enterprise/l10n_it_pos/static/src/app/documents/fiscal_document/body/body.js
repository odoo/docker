import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { formatFloat, floatIsZero } from "@web/core/utils/numbers";
import {
    PrintRecMessage,
    PrintRecItem,
    PrintRecTotal,
    PrintRecRefund,
    PrintRecItemAdjustment,
    PrintRecSubtotalAdjustment,
} from "@l10n_it_pos/app/fiscal_printer/commands";

export class Body extends Component {
    static template = "l10n_it_pos.FiscalDocumentBody";

    static components = {
        PrintRecMessage,
        PrintRecItem,
        PrintRecTotal,
        PrintRecRefund,
        PrintRecItemAdjustment,
        PrintRecSubtotalAdjustment,
    };

    setup() {
        this.pos = usePos();
        this.order = this.pos.get_order();
        this.adjustment = this.order.get_rounding_applied() && {
            description: _t("Rounding"),
            amount: this._itFormatCurrency(Math.abs(this.order.get_rounding_applied())),
            adjustmentType: this.order.get_rounding_applied() > 0 ? 6 : 1,
        };
    }

    _itFormatCurrency(amount) {
        const decPlaces = this.order.currency_id.decimal_places;
        return formatFloat(amount, {
            thousandsSep: "",
            digits: [0, decPlaces],
        });
    }
    _itFormatQty(qty) {
        const uom_decimal_places = this.pos.models["decimal.precision"].find(
            (dp) => dp.name === "Product Unit of Measure"
        ).digits;
        const decimal_places = Math.min(3, uom_decimal_places);
        return formatFloat(qty, {
            thousandsSep: "",
            digits: [0, decimal_places],
        });
    }

    get lines() {
        const calculateDiscountAmount = (line) => {
            const { priceWithTaxBeforeDiscount, priceWithTax: priceWithTaxAfterDiscount } =
                line.get_all_prices();
            return priceWithTaxBeforeDiscount - priceWithTaxAfterDiscount;
        };

        return this.order.lines.map((line, index) => {
            const productName = line.get_full_product_name();
            const department = line.tax_ids.map((tax) => tax.tax_group_id.pos_receipt_label)[0];
            const isRefund = line.qty < 0;
            const isReward = line.is_reward_line;
            return {
                isRefund,
                isReward,
                description: isRefund ? _t("%s (refund)", productName) : productName,
                customer_note: line.get_customer_note(),
                quantity: this._itFormatQty(Math.abs(line.qty)),
                // DISCOUNT: Use price before discount because the discounted amount is specified in the printRecItemAdjustment.
                // REFUND: Use the price with tax because there is no adjustment for printRecRefund.
                unitPrice: this._itFormatCurrency(
                    isRefund
                        ? line.get_all_prices(1).priceWithTax
                        : line.get_all_prices(1).priceWithTaxBeforeDiscount
                ),
                department,
                index,
                discount: (!floatIsZero(line.discount) || isReward) && {
                    description: isReward
                        ? productName
                        : _t("%s discount (%s)", productName, `${line.discount}%`),
                    amount: this._itFormatCurrency(
                        isReward
                            ? Math.abs(line.price_subtotal_incl)
                            : calculateDiscountAmount(line)
                    ),
                },
            };
        });
    }

    get payments() {
        return this.order.payment_ids.map((payment) => ({
            description: _t("Payment in %s", payment.payment_method_id.name),
            payment: this._itFormatCurrency(payment.amount),
            paymentType: payment.payment_method_id.it_payment_code,
            index: payment.payment_method_id.it_payment_index,
        }));
    }
}

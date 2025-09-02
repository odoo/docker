import { PaymentWorldline } from "@pos_iot/app/payment";

export class PaymentSix extends PaymentWorldline {
    get_payment_data(uuid) {
        const paymentline = this.pos.get_order().get_paymentline_by_uuid(uuid);
        const pos = this.pos;
        return {
            messageType: "Transaction",
            transactionType: paymentline.transactionType,
            amount: Math.round(paymentline.amount * 100),
            currency: pos.currency.name,
            cid: uuid,
            posId: pos.session.name,
            userId: pos.session.user_id.id,
        };
    }

    send_payment_request(uuid) {
        const paymentline = this.pos.get_order().get_paymentline_by_uuid(uuid);
        paymentline.transactionType = "Payment";

        return super.send_payment_request(uuid);
    }
}

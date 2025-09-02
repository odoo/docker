import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { convertFromEpoch } from "@l10n_de_pos_cert/app/utils";
import { patch } from "@web/core/utils/patch";
import { roundCurrency } from "@point_of_sale/app/models/utils/currency";

patch(PosOrder.prototype, {
    // @Override
    setup(vals) {
        super.setup(...arguments);
        if (this.isCountryGermanyAndFiskaly()) {
            this.fiskalyUuid = this.fiskalyUuid || "";
            this.transactionState = this.transactionState || "inactive"; // Used to know when we need to create the fiskaly transaction

            // Init the tssInformation with the values from the config
            this.l10n_de_fiskaly_transaction_uuid = vals.l10n_de_fiskaly_transaction_uuid || false;
            this.l10n_de_fiskaly_transaction_number =
                vals.l10n_de_fiskaly_transaction_number || false;
            this.l10n_de_fiskaly_time_start = vals.l10n_de_fiskaly_time_start || false;
            this.l10n_de_fiskaly_time_end = vals.l10n_de_fiskaly_time_end || false;
            this.l10n_de_fiskaly_certificate_serial =
                vals.l10n_de_fiskaly_certificate_serial || false;
            this.l10n_de_fiskaly_timestamp_format = vals.l10n_de_fiskaly_timestamp_format || false;
            this.l10n_de_fiskaly_signature_value = vals.l10n_de_fiskaly_signature_value || false;
            this.l10n_de_fiskaly_signature_algorithm =
                vals.l10n_de_fiskaly_signature_algorithm || false;
            this.l10n_de_fiskaly_signature_public_key =
                vals.l10n_de_fiskaly_signature_public_key || false;
            this.l10n_de_fiskaly_client_serial_number =
                vals.l10n_de_fiskaly_client_serial_number || false;
        }
    },
    isCountryGermanyAndFiskaly() {
        return this.isCountryGermany() && !!this.getTssId();
    },
    getTssId() {
        return (
            this.config.l10n_de_fiskaly_tss_id && this.config.l10n_de_fiskaly_tss_id.split("|")[0]
        );
    },
    isCountryGermany() {
        return this.config.is_company_country_germany;
    },
    isTransactionInactive() {
        return this.transactionState === "inactive";
    },
    transactionStarted() {
        this.transactionState = "started";
    },
    isTransactionStarted() {
        return this.transactionState === "started";
    },
    transactionFinished() {
        this.transactionState = "finished";
    },
    isTransactionFinished() {
        return this.transactionState === "finished" || this.l10n_de_fiskaly_time_start;
    },
    // @Override
    export_for_printing(baseUrl, headerData) {
        const receipt = super.export_for_printing(...arguments);
        if (this.isCountryGermanyAndFiskaly()) {
            if (this.isTransactionFinished()) {
                receipt["tss"] = {
                    transaction_number: this.l10n_de_fiskaly_transaction_number,
                    time_start: this.l10n_de_fiskaly_time_start,
                    time_end: this.l10n_de_fiskaly_time_end,
                    certificate_serial: this.l10n_de_fiskaly_certificate_serial,
                    timestamp_format: this.l10n_de_fiskaly_timestamp_format,
                    signature_value: this.l10n_de_fiskaly_signature_value,
                    signature_algorithm: this.l10n_de_fiskaly_signature_algorithm,
                    signature_public_key: this.l10n_de_fiskaly_signature_public_key,
                    client_serial_number: this.l10n_de_fiskaly_client_serial_number,
                    erstBestellung: this.get_orderlines()[0].get_product().display_name,
                };
            } else {
                receipt["tss_issue"] = true;
            }
        } else if (this.isCountryGermany() && !this.getTssId()) {
            receipt["test_environment"] = true;
        }
        return receipt;
    },
    /*
     *  Return an array of { 'payment_type': ..., 'amount': ...}
     */
    _createAmountPerPaymentTypeArray() {
        const amountPerPaymentTypeArray = [];
        this.payment_ids.forEach((line) => {
            amountPerPaymentTypeArray.push({
                payment_type:
                    line.payment_method_id.name.toLowerCase() === "cash" ? "CASH" : "NON_CASH",
                amount: roundCurrency(line.amount, this.currency).toFixed(2),
            });
        });
        const change = this.get_change();
        if (change) {
            amountPerPaymentTypeArray.push({
                payment_type: "CASH",
                amount: roundCurrency(-change, this.currency).toFixed(2),
            });
        }
        return amountPerPaymentTypeArray;
    },
    _updateTimeStart(seconds) {
        this.l10n_de_fiskaly_time_start = convertFromEpoch(seconds);
    },
    _updateTssInfo(data) {
        this.l10n_de_fiskaly_transaction_number = data.number;
        this._updateTimeStart(data.time_start);
        this.l10n_de_fiskaly_time_end = convertFromEpoch(data.time_end);
        // certificate_serial is now called tss_serial_number in the v2 api
        this.l10n_de_fiskaly_certificate_serial = data.tss_serial_number
            ? data.tss_serial_number
            : data.certificate_serial;
        this.l10n_de_fiskaly_timestamp_format = data.log.timestamp_format;
        this.l10n_de_fiskaly_signature_value = data.signature.value;
        this.l10n_de_fiskaly_signature_algorithm = data.signature.algorithm;
        this.l10n_de_fiskaly_signature_public_key = data.signature.public_key;
        this.l10n_de_fiskaly_client_serial_number = data.client_serial_number;
        this.transactionFinished();
    },
});

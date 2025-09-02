import { _t } from "@web/core/l10n/translation";
import { ScaleScreen } from "@point_of_sale/app/screens/scale_screen/scale_screen";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useBus, useService } from "@web/core/utils/hooks";

patch(ScaleScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
        useBus(this.hardwareProxy, "change_status", this.onProxyStatusChange);
    },
    async onProxyStatusChange({ detail: newStatus }) {
        if (this.iot_box.connected && newStatus.drivers.scale?.status === "connected") {
            this._error = false;
        } else {
            if (!this._error) {
                this._error = true;
                this.dialog.add(AlertDialog, {
                    title: _t("Could not connect to IoT scale"),
                    body: _t("The IoT scale is not responding. You should check your connection."),
                });
            }
        }
    },
    get scale() {
        return this.hardwareProxy.deviceControllers.scale;
    },
    get isManualMeasurement() {
        return this.scale?.manual_measurement;
    },
    /**
     * @override
     */
    onMounted() {
        this.iot_box = this.hardwareProxy.iotBoxes.find((box) => box.ip === this.scale.iotIp);
        this._error = false;
        if (!this.isManualMeasurement) {
            this.scale.action({ action: "start_reading" });
        }
        super.onMounted(...arguments);
    },
    /**
     * @override
     */
    onWillUnmount() {
        super.onWillUnmount(...arguments);
        // FIXME action return a promise, but we don't wait for it
        // its possible that the promise wasn't resolved when we remove the listener
        this.scale.action({ action: "stop_reading" });
        this.scale.removeListener();
    },
    measureWeight() {
        this.scale.action({ action: "read_once" });
    },
    /**
     * @override
     * Completely replace how the original _readScale works.
     */
    async _readScale() {
        await this.scale.addListener(this._onValueChange.bind(this));
        await this.scale.action({ action: "read_once" });
    },
    _onValueChange(data) {
        if (data.status.status === "error") {
            this.dialog.add(AlertDialog, {
                body: data.status.message_body,
            });
        } else {
            if (this.state.tareLoading) {
                this.state.tare = data.value;
                this.pos.setScaleTare(data.value);
                setTimeout(() => {
                    this.state.tareLoading = false;
                }, 3000);
            } else {
                this.state.weight = data.value;
                this.pos.setScaleWeight(data.value);
            }
        }
    },
    /**
     * @override
     */
    async handleTareButtonClick() {
        this.state.tareLoading = true;
        this._readScale();
    },
});

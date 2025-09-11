/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';
import { FloatField, floatField } from '@web/views/fields/float/float_field';
import { useIotDevice } from '@iot/iot_device_hook';
import { useService } from '@web/core/utils/hooks';
import { WarningDialog } from '@web/core/errors/error_dialogs';
import { IoTConnectionErrorDialog } from '@iot/iot_connection_error_dialog';

export class IoTMeasureRealTimeValue extends FloatField {
    setup() {
        super.setup();
        this.dialog = useService('dialog');
        this.notification = useService('notification');
        this.getIotDevice = useIotDevice({
            getIotIp: () => {
                if (this.props.record.data.test_type === 'measure') {
                    return this.props.record.data[this.props.ip_field];
                }
            },
            getIdentifier: () => {
                if (this.props.record.data.test_type === 'measure') {
                    return this.props.record.data[this.props.identifier_field];
                }
            },
            onValueChange: (data) => {
                if (this.env.model.root.isInEdition) {
                    // Only update the value in the record when the record is in edition mode.
                    return this.props.record.update({ [this.props.name]: data.value });
                }
            },
        });
    }
    async onTakeMeasure() {
        if (this.getIotDevice()) {
            this.notification.add(_t('Getting measurement...'));
            try {
                const data = await this.getIotDevice().action({ action: 'read_once' });
                if (data.result !== true) {
                    this.dialog.add(WarningDialog, {
                        title: _t('Connection to device failed'),
                        message: _t('Please check if the device is still connected.'),
                    });
                }
                return data;
            } catch {
                this.dialog.add(IoTConnectionErrorDialog, { href: this.props.record.data[this.props.ip_field] });
            }
        }
    }
    get hasDevice() {
        return this.props.record.data[this.props.ip_field] != "";
    }
}
IoTMeasureRealTimeValue.template = `quality_iot.IoTMeasureRealTimeValue`;
IoTMeasureRealTimeValue.props = {
    ...FloatField.props,
    ip_field: { type: String },
    identifier_field: { type: String },
};

registry.category("fields").add("iot_measure", {
    ...floatField,
    component: IoTMeasureRealTimeValue,
    extractProps({ options }) {
        const props = floatField.extractProps(...arguments);
        props.ip_field = options.ip_field;
        props.identifier_field = options.identifier;
        return props;
    },
});

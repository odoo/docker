/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser"
import { DeviceController } from "@iot/device_controller";
import {
    IOT_REPORT_PREFERENCE_LOCAL_STORAGE_KEY,
    removeIoTReportIdFromBrowserLocalStorage,
} from "./client_action/delete_local_storage";

/**
 * Generate a unique identifier (64 bits) in hexadecimal.
 * Copied beacause if imported from web import too many other modules
 * 
 * @returns {string}
 */
function uuid() {
    const array = new Uint8Array(8);
    window.crypto.getRandomValues(array);
    // Uint8Array to hex
    return [...array].map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Get the devices from the ids stored in the localStorage
 * @param orm The ORM service
 * @param stored_content The list of devices in localStorage
 */
async function getDevicesFromIds(orm, stored_content) {
    return await orm.call("ir.actions.report", "get_devices_from_ids", [
        0,
        stored_content,
    ]);
}

/**
 * Send the report to the IoT device using longpolling
 * @param env The environment
 * @param orm The ORM service
 * @param args The arguments to send to the server to render the report
 * @param stored_device_ids The list of devices in localStorage to send the report to
 */
async function longpolling(env, orm, args, stored_device_ids) {
    const [report_id, active_record_ids, report_data, uuid] = args;
    const devices = await getDevicesFromIds(orm, stored_device_ids).catch((error) => {
        console.error("Failed to get devices from ids", error);
        throw error;
    });
    const jobs = await orm.call("ir.actions.report", "render_and_send", [
        report_id,
        devices,
        active_record_ids,
        report_data,
        uuid,
        false, // Do not use websocket
    ]);
    for (const job of jobs) {
        const [ ip, identifier, name, document ] = job;
        const longpollingHasFallback = true; // Prevent `IoTConnectionErrorDialog`
        env.services.notification.add(_t("Sending to printer %s...", name), { type: "info" });

        const iotDevice = new DeviceController(env.services.iot_longpolling, { iot_ip: ip, identifier });
        await iotDevice.action({ document, print_id: uuid }, longpollingHasFallback);
    }
}

/**
 * Try to send the report to the IoT device using longpolling, then fallback to the websocket
 * @param env The environment
 * @param orm The ORM service
 * @param args The arguments to send to the server to render the report
 * @param stored_device_ids The list of devices to send the report to
 */
export async function handleIoTConnectionFallbacks(env, orm, args, stored_device_ids) {
    // Define the connection types in the order of executions to try
    const connectionTypes = [
        () => longpolling(env, orm, args, stored_device_ids),
        () => env.services.iot_websocket.addJob(stored_device_ids, args, false),
    ];
    for (const connectionType of connectionTypes) {
        try {
            await connectionType();
            return;
        } catch {
            console.debug("Send print request failed, attempting another protocol.")
        }
    }

    // Fail notification if all connections failed
    env.services.notification.add(_t("Failed to send to printer."), { type: "danger" });
    removeIoTReportIdFromBrowserLocalStorage(args[0]);  // args[0] = report_id
}

async function iotReportActionHandler(action, options, env) {
    if (action.device_ids && action.device_ids.length) {
        const orm = env.services.orm;
        action.data = action.data || {};
        action.data["device_ids"] = action.device_ids;
        const args = [action.id, action.context.active_ids, action.data, uuid()];
        const report_id = action.id;
        const local_lists = JSON.parse(browser.localStorage.getItem(IOT_REPORT_PREFERENCE_LOCAL_STORAGE_KEY));
        const onClose = options.onClose;
        const stored_device_ids = local_lists ? local_lists[report_id] : undefined;
        if (!stored_device_ids) {
            // Open IoT devices selection wizard
            const action_wizard = await orm.call("ir.actions.report", "get_action_wizard", args);
            await env.services.action.doAction(action_wizard);
        } else {
            // Try longpolling then websocket
            await handleIoTConnectionFallbacks(env, orm, args, stored_device_ids);

            // We close here to prevent premature closure if the device selection modal is displayed.
            env.services.action.doAction({ type: "ir.actions.act_window_close" }, { onClose });
        }

        onClose?.();
        return true;
    }
}

registry
    .category("ir.actions.report handlers")
    .add("iot_report_action_handler", iotReportActionHandler);

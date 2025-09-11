import { Reactive } from "@web/core/utils/reactive";
import { registry } from "@web/core/registry";
import { parseXML } from "@web/core/utils/xml";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import {
    FiscalReceipt,
    FiscalInvoice,
    XReport,
    ZReport,
    XZReport,
} from "@l10n_it_pos/app/documents";
import {
    PrintDuplicateReceipt,
    DisplayText,
    OpenDrawer,
    RTStatus,
    DirectIO,
} from "@l10n_it_pos/app/fiscal_printer/commands";

const DEFAULT_TIMEOUT = 10000;
const DEFAULT_DEVID = "local_printer";
const CONFIG = {
    isHttps: false,
    ip: null,
    showErrorInDialog: true,
    logCommands: true,
};

class EpsonFiscalPrinter extends Reactive {
    constructor(isHttps, ip, ...args) {
        super(...args);
        this.setup(...args);
        CONFIG.ip = ip;
        CONFIG.isHttps = isHttps;
    }
    setup(env, { dialog, epson_fiscal_printer_command }) {
        this.dialog = dialog;
        this.command = epson_fiscal_printer_command;
    }

    async printFiscalReceipt({ timeout, devid } = {}) {
        const command = await this.command.create(FiscalReceipt);
        return this.sendCommand(command, { timeout, devid });
    }

    async printFiscalInvoice({ timeout, devid } = {}) {
        const command = await this.command.create(FiscalInvoice);
        return this.sendCommand(command, { timeout, devid });
    }

    async printXReport({ timeout, devid } = {}) {
        const command = await this.command.create(XReport);
        return this.sendCommand(command, { timeout, devid });
    }

    async printZReport({ timeout, devid } = {}) {
        const command = await this.command.create(ZReport);
        return this.sendCommand(command, { timeout, devid });
    }

    async printXZReport({ timeout, devid } = {}) {
        const command = await this.command.create(XZReport);
        return this.sendCommand(command, { timeout, devid });
    }

    async getRTStatus({ timeout, devid } = {}) {
        const command = await this.command.create(RTStatus);
        return this.sendCommand(command, { timeout, devid });
    }

    async displayText(message, { timeout, devid } = {}) {
        const command = await this.command.create(DisplayText, { message });
        return this.sendCommand(command, { timeout, devid });
    }

    async printDuplicateReceipt({ timeout, devid } = {}) {
        const command = await this.command.create(PrintDuplicateReceipt);
        return this.sendCommand(command, { timeout, devid });
    }

    async openCashDrawer({ timeout, devid } = {}) {
        const command = await this.command.create(OpenDrawer);
        return this.sendCommand(command, { timeout, devid });
    }

    async directIO(cmd, data, { timeout, devid } = {}) {
        const command = await this.command.create(DirectIO, { command: cmd, data });
        return this.sendCommand(command, { timeout, devid });
    }

    async getPrinterSerialNumber() {
        const result = await this.directIO("3217", "01");
        return result.addInfo.responseData;
    }

    async roundCashPayments() {
        const result = await this.directIO("4015", "27001");
        return result;
    }

    async sendCommand(command, { timeout, devid } = {}) {
        if (CONFIG.logCommands) {
            console.log(command.toXML());
        }
        const url = this._getUrl({ timeout, devid });
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "text/xml; charset=utf-8",
                "Content-Length": command.length,
                "If-Modified-Since": "Thu, 01 Jan 1970 00:00:00 GMT",
            },
            body: command,
        });
        if (response.status === 200) {
            const xml = await response.text();
            const parsed = parseXML(xml);
            const result = parsed.children[0].children[0];
            const success = result.attributes["success"].value === "true";
            const code = result.attributes["code"].value;
            const status = result.attributes["status"].value;
            if (!success) {
                console.error(result);
                if (CONFIG.showErrorInDialog && CONFIG.dialogService) {
                    CONFIG.dialogService.add(AlertDialog, {
                        title: _t("Fiscal Printer Error"),
                        body: `CODE: ${code}\nSTATUS: ${status}`,
                    });
                }
            }
            const addInfo = {};
            for (const child of result.children[0].children) {
                if (child.tagName in addInfo) {
                    addInfo[child.tagName] = [addInfo[child.tagName]];
                    addInfo[child.tagName].push(child.textContent);
                } else {
                    addInfo[child.tagName] = child.textContent;
                }
            }
            // remove elementList
            delete addInfo.elementList;
            return { success, code, status, addInfo };
        } else {
            throw new Error(`Error sending command to fiscal printer: ${response.status}`);
        }
    }

    _getUrl({ timeout, devid }) {
        return `${CONFIG.isHttps ? "https" : "http"}://${CONFIG.ip}/cgi-bin/fpmate.cgi?devid=${
            devid || DEFAULT_DEVID
        }&timeout=${timeout || DEFAULT_TIMEOUT}`;
    }
}

const epsonFiscalPrinterService = {
    dependencies: ["dialog", "epson_fiscal_printer_command"],
    start(env, dependencies) {
        return (isHttps, ip) => {
            return new EpsonFiscalPrinter(isHttps, ip, env, dependencies);
        };
    },
};

registry.category("services").add("epson_fiscal_printer", epsonFiscalPrinterService);

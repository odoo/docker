import { registry } from "@web/core/registry";

const tags = [
    "printerFiscalReceipt",
    "displayText",
    "printRecMessage",
    "beginFiscalReceipt",
    "printRecItem",
    "printRecItemAdjustment",
    "printRecSubtotalAdjustment",
    "printRecSubtotal",
    "printBarCode",
    "printRecTotal",
    "endFiscalReceipt",
    "printerFiscalDocument",
    "beginFiscalDocument",
    "endFiscalDocument",
    "printerCommand",
    "queryPrinterStatus",
    "printerFiscalReport",
    "printXReport",
    "printXZReport",
    "printZReport",
    "setLogo",
    "printRecRefund",
    "directIO",
    "printRecItemAdjustment",
    "printDuplicateReceipt",
    "openDrawer",
];

const attributes = [
    "messageType",
    "unitPrice",
    "adjustmentType",
    "paymentType",
    "hRIPosition",
    "hRIFont",
    "codeType",
    "documentType",
    "documentNumber",
    "graphicFormat",
    "adjustmentType",
    "statusType",
];

class Command extends String {
    toXML(indentation = "  ") {
        const reg = /(>)(<)(\/*)/g;
        const formatted = this.replace(reg, "$1\r\n$2$3");
        const lines = formatted.split("\r\n");

        let indent = "";
        const formattedLines = [];
        for (const line of lines) {
            if (/^<\/\w/.test(line)) {
                // Decrease indent for closing elements.
                indent = indent.substring(indentation.length);
            }

            const indentedLine = indent + line;

            if (
                /<\w[^>]*[^/]>.*$/ /// Tag opening
                    .test(line)
            ) {
                indent += indentation; // Increase indent after an opening tag.
            }

            formattedLines.push(indentedLine);
        }

        return formattedLines.join("\r\n");
    }
}

const EpsonFiscalPrinterCommandService = {
    dependencies: ["renderer"],
    start(env, { renderer }) {
        async function create(template, props = {}) {
            const commandRaw = await renderer.toHtml(template, props);

            // replace all tags and attributes
            let htmlString = commandRaw.outerHTML;
            for (const tag of [...tags, ...attributes]) {
                htmlString = htmlString.replaceAll(tag.toLowerCase(), tag);
            }

            // make self-closing tags
            const xmlString = htmlString.replaceAll(/<(\w+)([^>]*)>\s*<\/\1>/g, "<$1$2 />");

            const command =
                '<?xml version="1.0" encoding="utf-8"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body>' +
                xmlString +
                "</s:Body></s:Envelope>";

            return new Command(command);
        }

        return { create };
    },
};

registry.category("services").add("epson_fiscal_printer_command", EpsonFiscalPrinterCommandService);

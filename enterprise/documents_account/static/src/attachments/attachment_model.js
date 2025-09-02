/* @odoo-module */

import { Attachment } from "@mail/core/common/attachment_model";
import { patch } from "@web/core/utils/patch";

patch(Attachment.prototype, {
    get isPdf() {
        if (this.documentData && this.documentData.has_embedded_pdf) {
            return true;
        }
        return super.isPdf;
    },
});

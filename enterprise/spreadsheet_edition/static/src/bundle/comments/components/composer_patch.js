import { patch } from "@web/core/utils/patch";
import { Composer } from "@mail/core/common/composer";
import { _t } from "@web/core/l10n/translation";

patch(Composer.prototype, {
    /**
     * This function overrides the original method so that when the user tries to open a the record
     * from a starred discussion linked to a spreadsheet cell thread, it can be redirected to the corresponding
     * spreadsheet record.
     * @override
     */
    get SEND_TEXT() {
        if (this.props.composer?.thread?.model === "spreadsheet.cell.thread") {
            return _t("Send");
        } else {
            return super.SEND_TEXT;
        }
    },
});

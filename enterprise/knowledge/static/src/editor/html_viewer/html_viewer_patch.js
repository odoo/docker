import { HtmlViewer } from "@html_editor/fields/html_viewer";
import { HtmlUpgradeManager } from "@knowledge/editor/html_migrations/html_upgrade_manager";
import { patch } from "@web/core/utils/patch";

patch(HtmlViewer.prototype, {
    setup() {
        this.htmlUpgradeManager = this.env.htmlUpgradeManager || new HtmlUpgradeManager();
        // super setup is called after because it uses formatValue
        super.setup();
    },

    formatValue(value) {
        const current = super.formatValue(value);
        return this.htmlUpgradeManager.processForUpgrade(current);
    },
});

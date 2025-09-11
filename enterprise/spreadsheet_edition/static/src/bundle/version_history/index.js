/** @odoo-module */

import {
    registries,
    readonlyAllowedCommands,
    invalidateEvaluationCommands,
} from "@odoo/o-spreadsheet";
import { VersionHistorySidePanel } from "./side_panel/version_history_side_panel";
import { _t } from "@web/core/l10n/translation";
import { VersionHistoryPlugin } from "./version_history_plugin";

registries.topbarMenuRegistry.addChild("version_history", ["file"], {
    name: _t("See version history"),
    sequence: 55,
    isVisible: (env) => env.showHistory,
    execute: (env) => env.showHistory(),
    icon: "o-spreadsheet-Icon.VERSION_HISTORY",
});

registries.sidePanelRegistry.add("VersionHistory", {
    title: _t("Version History"),
    Body: VersionHistorySidePanel,
});

registries.featurePluginRegistry.add("odooVersionHistory", VersionHistoryPlugin);

readonlyAllowedCommands.add("GO_TO_REVISION");
invalidateEvaluationCommands.add("GO_TO_REVISION");

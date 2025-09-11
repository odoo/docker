/** @odoo-module **/
import { onMounted, onWillStart, useState, Component, useSubEnv } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { _t } from "@web/core/l10n/translation";
import { pyToJsLocale } from "@web/core/l10n/utils";
import { registry } from "@web/core/registry";

import { UNTITLED_SPREADSHEET_NAME } from "@spreadsheet/helpers/constants";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { Model, stores } from "@odoo/o-spreadsheet";

import { loadSpreadsheetDependencies } from "@spreadsheet/assets_backend/helpers";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { SpreadsheetComponent } from "@spreadsheet/actions/spreadsheet_component";
import { SpreadsheetName } from "../control_panel/spreadsheet_name";
import {
    useSpreadsheetCurrencies,
    useSpreadsheetLocales,
    useSpreadsheetThumbnail,
} from "../../hooks";
import { formatToLocaleString } from "../../helpers/misc";
import { router } from "@web/core/browser/router";
import { RestoreVersionConfirmationDialog } from "../../version_history/restore_version_dialog/restore_version_dialog";
import { OdooDataProvider } from "@spreadsheet/data_sources/odoo_data_provider";
import { SpreadsheetNavbar } from "../../components/spreadsheet_navbar/spreadsheet_navbar";

const { ModelStore, useStoreProvider, SidePanelStore } = stores;

export class VersionHistoryAction extends Component {
    static template = "spreadsheet_edition.VersionHistoryAction";
    static components = {
        SpreadsheetComponent,
        SpreadsheetName,
        SpreadsheetNavbar,
    };
    static props = { ...standardActionServiceProps };
    static target = "fullscreen";

    setup() {
        this.params = this.props.action.params;
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.actionService = useService("action");
        this.resId = this.params.spreadsheet_id || (this.props.state && this.props.state.resId); // used when going back to a spreadsheet via breadcrumb
        this.resModel = this.params.res_model || (this.props.state && this.props.state.remoModel); // used when going back to a spreadsheet via breadcrumb
        this.fromSnapshot =
            this.params.from_snapshot || (this.props.state && this.props.state.fromSnapshot);
        this.loadLocales = useSpreadsheetLocales();
        this.loadCurrencies = useSpreadsheetCurrencies();
        this.getThumbnail = useSpreadsheetThumbnail();

        useSubEnv({
            historyManager: {
                getRevisions: this.getRevisions.bind(this),
                forkHistory: this.forkHistory.bind(this),
                restoreRevision: this.restoreRevision.bind(this),
                renameRevision: this.renameRevision.bind(this),
            },
        });

        this.state = useState({
            spreadsheetName: UNTITLED_SPREADSHEET_NAME,
            revisions: [],
            restorableRevisions: [],
        });

        const stores = useStoreProvider();

        onWillStart(async () => {
            await this.fetchData();
            this.createModel();
            stores.inject(ModelStore, this.model);
        });

        onMounted(() => {
            router.pushState({
                spreadsheet_id: this.resId,
                res_model: this.resModel,
                from_snapshot: this.fromSnapshot,
            });
            this.env.config.setDisplayName(this.state.spreadsheetName);
            const sidePanel = stores.get(SidePanelStore);
            sidePanel.open("VersionHistory", {
                onCloseSidePanel: async () => {
                    const action = await this.env.services.orm.call(
                        this.resModel,
                        "action_open_spreadsheet",
                        [this.resId]
                    );
                    this.env.services.action.doAction(action, {
                        clearBreadcrumbs: true,
                    });
                },
            });
        });
    }

    getRevisions() {
        return this.state.restorableRevisions;
    }

    async renameRevision(revisionId, name) {
        this.state.revisions.find((el) => el.id === revisionId).name = name;
        this.generateRestorableRevisions();
        await this.orm.call(this.resModel, "rename_revision", [this.resId, revisionId, name]);
    }

    async forkHistory(revisionId) {
        const data = this.model.exportData();
        const revision = this.state.restorableRevisions.find((rev) => rev.id === revisionId);
        data.revisionId = revision.nextRevisionId;
        const code = pyToJsLocale(this.model.getters.getLocale().code);
        const timestamp = formatToLocaleString(revision.timestamp, code);
        const name = _t("%(name)s (restored from %(timestamp)s)", {
            name: this.state.spreadsheetName,
            timestamp,
        });
        const defaultValues = {
            thumbnail: this.getThumbnail(),
            name,
        };
        const action = await this.orm.call(this.resModel, "fork_history", [this.resId], {
            revision_id: revisionId,
            spreadsheet_snapshot: data,
            default: defaultValues,
        });
        // Redirect to the forked spreadsheet
        this.actionService.doAction(action, { clearBreadcrumbs: true });
    }

    async restoreRevision(revisionId) {
        const revision = this.state.restorableRevisions.find((rev) => rev.id === revisionId);
        const code = pyToJsLocale(this.model.getters.getLocale().code);
        const timestamp = formatToLocaleString(revision.timestamp, code);
        this.dialog.add(RestoreVersionConfirmationDialog, {
            title: _t("Heads up!"),
            body: _t(
                "If you go ahead, your document will go back to the version from %s.\nAny changes you've made after that time will disappear. Ready to proceed?",
                timestamp
            ),
            makeACopy: () => this.forkHistory(revisionId),
            confirm: async () => {
                const data = this.model.exportData();
                const action = await this.orm.call(
                    this.resModel,
                    "restore_spreadsheet_version",
                    [this.resId],
                    {
                        revision_id: revisionId,
                        spreadsheet_snapshot: data,
                    }
                );
                this.actionService.doAction(action, { clearBreadcrumbs: true });
            },
            cancel: () => {},
        });
    }

    async fetchData() {
        const [spreadsheetHistoryData] = await Promise.all([
            this._fetchData(),
            loadSpreadsheetDependencies(),
        ]);
        this.spreadsheetData = spreadsheetHistoryData.data;
        this.spreadsheetDataLastDate = spreadsheetHistoryData.initial_date;
        this.state.revisions = spreadsheetHistoryData.revisions;
        this.generateRestorableRevisions();
        this.state.spreadsheetName = spreadsheetHistoryData.name;
        this.currentRevisionId =
            spreadsheetHistoryData.revisions.at(-1)?.nextRevisionId ||
            spreadsheetHistoryData.data.revisionId ||
            "START_REVISION";
        this.odooDataProvider = new OdooDataProvider(this.env);
    }

    generateRestorableRevisions() {
        const revs = this.state.revisions
            .slice()
            .filter((el) => el.type !== "SNAPSHOT_CREATED")
            .reverse();
        const firstRevision = revs.at(-1);
        if (firstRevision) {
            revs.push({
                id: 0,
                nextRevisionId: firstRevision.serverRevisionId,
                name: _t("Original data"),
                timestamp: this.spreadsheetDataLastDate,
            });
        }
        this.state.restorableRevisions = revs;
    }

    /**
     * @returns {Promise<SpreadsheetRecord>}
     */
    async _fetchData() {
        const record = await this.orm.call(this.resModel, "get_spreadsheet_history", [
            this.resId,
            !!this.fromSnapshot,
        ]);
        return record;
    }

    /**
     * @private
     */
    _dataSourceBind() {
        const sheetId = this.model.getters.getActiveSheetId();
        this.model.dispatch("EVALUATE_CELLS", { sheetId });
    }

    reloadFromSnapshot() {
        this.actionService.doAction(
            {
                type: "ir.actions.client",
                tag: this.props.action.tag,
                params: {
                    spreadsheet_id: this.resId,
                    res_model: this.resModel,
                    from_snapshot: true,
                },
            },
            { clearBreadcrumbs: true }
        );
    }

    async loadEditAction() {
        const action = await this.env.services.orm.call(this.resModel, "action_open_spreadsheet", [
            this.resId,
        ]);
        this.actionService.doAction(action, {
            clearBreadcrumbs: true,
        });
    }

    createModel() {
        this.odooDataProvider.addEventListener(
            "data-source-updated",
            this._dataSourceBind.bind(this)
        );
        const data = this.spreadsheetData;
        this.model = new Model(
            data,
            {
                custom: {
                    env: this.env,
                    orm: this.orm,
                    odooDataProvider: this.odooDataProvider,
                },
                external: {
                    loadCurrencies: this.loadCurrencies,
                    loadLocales: this.loadLocales,
                },
                mode: "readonly",
            },
            this.state.revisions
        );

        if (this.model.session.serverRevisionId !== this.currentRevisionId) {
            this.model = new Model({});
            if (!this.fromSnapshot) {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Odoo Spreadsheet"),
                    body: _t(
                        "There are missing revisions that prevent to restore the whole edition history.\n\
Would you like to load the more recent modifications?"
                    ),
                    confirm: () => {
                        this.reloadFromSnapshot();
                    },
                    close: () => {
                        this.loadEditAction();
                    },
                });
            } else {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Odoo Spreadsheet"),
                    body: _t(
                        "The history of your spreadsheet is corrupted and you are likely missing recent revisions. This feature cannot be used."
                    ),
                    confirm: () => {
                        this.loadEditAction();
                    },
                });
            }
        }
        if (this.env.debug) {
            // eslint-disable-next-line no-import-assign
            spreadsheet.__DEBUG__ = spreadsheet.__DEBUG__ || {};
            spreadsheet.__DEBUG__.model = this.model;
        }
    }
}

registry.category("actions").add("action_open_spreadsheet_history", VersionHistoryAction, {
    force: true,
});

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { DocumentsBreadcrumbs } from "@documents/components/documents_breadcrumbs";
import { DocumentsCogMenu } from "../cog_menu/documents_cog_menu";
import { useState } from "@odoo/owl";
import { useService, useBus } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";
import { serializeDate } from "@web/core/l10n/dates";
const { DateTime } = luxon;
import { toggleArchive, openDeleteConfirmationDialog } from "@documents/views/hooks";
import { browser } from "@web/core/browser/browser";

// TODO: clean
export class DocumentsControlPanel extends ControlPanel {
    static template = "documents.ControlPanel";
    static components = {
        ...ControlPanel.components,
        DocumentsBreadcrumbs,
        DocumentsCogMenu,
    };

    setup() {
        super.setup();
        this.action = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.documentService = useService("document.document");

        this.documentsState = useState({
            isChatterVisible: this.documentService.isChatterVisible(),
            previewedDocument: null,
        });

        // Document service functions
        this.isEditable = this.documentService.isEditable;
        this.canDownload = this.documentService.canDownload;
        this.isFolderSharable = this.documentService.isFolderSharable;

        useBus(this.documentService.bus, "DOCUMENT_PREVIEWED", async (ev) => {
            this.documentsState.previewedDocument = this.documentService.previewedDocument;
        });
    }

    /**
     * Execute the given `ir.actions.server` on the current selected documents.
     */
    async onDoAction(actionId) {
        const documentIds = this.targetRecords.map((record) => record.data.id);

        const context = {
            active_model: "documents.document",
            active_ids: documentIds,
        };
        const action = await this.orm.call(
            "documents.document",
            "action_execute_embedded_action",
            [actionId],
            { context }
        );
        if (action) {
            // We might need to do a client action (e.g. to open the "Link Record" wizard)
            await this.action.doAction(action, {
                onClose: () => {
                    this.env.searchModel._reloadSearchModel(true);
                },
            });
            if (action.tag !== "display_notification") {
                return;
            }
        }
        this.env.searchModel._reloadSearchModel(true);
        this.documentsState.previewedDocument = null;
    }

    /**
     * Open the permission panel of the selected document.
     */
    async onShare() {
        const documents = this.targetRecords;
        if (documents.length !== 1) {
            return;
        }

        this.env.documentsView.bus.trigger("documents-open-share", {
            id: documents[0].data.id,
            shortcut_document_id: documents[0].data.shortcut_document_id,
        });
    }

    /**
     * Download the selected documents.
     */
    onDownload() {
        const documents = this.targetRecords.filter((rec) => !rec.isRequest());
        if (!documents.length) {
            return;
        }

        const linkDocuments = documents.filter((el) => el.data.type === "url");
        const noLinkDocuments = documents.filter((el) => el.data.type !== "url");
        // Manage link documents
        if (documents.length === 1 && linkDocuments.length) {
            // Redirect to the link
            let url = linkDocuments[0].data.url;
            url = /^(https?|ftp):\/\//.test(url) ? url : `http://${url}`;
            window.open(url, "_blank");
        } else if (noLinkDocuments.length) {
            // Download all documents which are not links
            if (noLinkDocuments.length === 1) {
                download({
                    data: {},
                    url: `/documents/content/${noLinkDocuments[0].data.access_token}`,
                });
            } else {
                download({
                    data: {
                        file_ids: noLinkDocuments.map((rec) => rec.data.id),
                        zip_name: `documents-${serializeDate(DateTime.now())}.zip`,
                    },
                    url: "/documents/zip",
                });
            }
        }
    }

    /**
     * Unlink the selected documents if they are archived.
     */
    async onDelete() {
        const records = this.targetRecords.filter((r) => !r.data.active);
        if (!(await openDeleteConfirmationDialog(this.env.model, true))) {
            return;
        }
        const model = this.env.model;
        await model.root.deleteRecords(records);
        await model.load(this.env.model.config);
        await this.notifyChange();
    }

    /**
     * Send the selected documents to the trash.
     */
    async onArchive() {
        const records = this.targetRecords.filter((r) => r.data.active);
        const recordIds = records.map((r) => r.data.id);
        await toggleArchive(records[0].model, records[0].resModel, recordIds, true);
        await this.notifyChange();
    }

    /**
     * Duplicate the selected documents.
     */
    async onDuplicate() {
        const records = this.targetRecords.filter((r) => r.data.active);
        const recordIds = records.map((r) => r.data.id);
        await this.orm.call("documents.document", "copy", [recordIds]);
        await this.notifyChange();
    }

    /**
     * Restore the selected documents.
     */
    async onRestore() {
        const records = this.targetRecords.filter((r) => !r.data.active);
        const recordIds = records.map((r) => r.data.id);
        await toggleArchive(records[0].model, records[0].resModel, recordIds, false);
        await this.env.searchModel._reloadSearchModel(true);
    }

    /**
     * Open the split / merge tool on the selected PDFs.
     */
    onSplitPDF() {
        const documents = this.targetRecords;
        if (!documents || !documents.every((d) => d.isPdf())) {
            return;
        }

        this.env.documentsView.bus.trigger("documents-open-preview", {
            documents: documents,
            mainDocument: this.targetRecords[0],
            isPdfSplit: true,
            hasPdfSplit: true,
            embeddedActions: this.embeddedActions,
        });
    }

    /**
     * Lock / unlock the selected record.
     */
    async onToggleLock() {
        if (this.targetRecords.length !== 1) {
            return;
        }
        const record = this.targetRecords[0];
        await this.orm.call("documents.document", "toggle_lock", [record.data.id]);
        await record.load();
    }

    /**
     * Open the "rename" form view on the selected record.
     */
    async onRename() {
        if (this.targetRecords.length !== 1) {
            return;
        }
        await this.documentService.openDialogRename(this.targetRecords[0].data.id);
        await this.notifyChange();
    }

    /**
     * Open the chatter (the info will be stored in the local storage of the current user).
     */
    async onToggleChatter() {
        await this.env.documentsView.bus.trigger("documents-toggle-chatter");
        this.documentsState.isChatterVisible = !this.documentsState.isChatterVisible;
    }

    /**
     * Create a shortcut for the selected document.
     */
    async onCreateShortcut() {
        const documents = this.targetRecords;
        if (documents.length !== 1) {
            this.notificationService.add(_t("Shortcuts can only be created one at a time."), {
                type: "danger",
            });
            return;
        }
        await this.orm.call(
            "documents.document",
            "action_create_shortcut",
            [this.targetRecords[0].data.id],
        );
        await this.notifyChange();
    }

    /**
     * Copy the links (comma-separated) of the selected documents.
     */
    async onCopyLinks() {
        const documents = this.targetRecords;

        await this.populateMissingAccessURLsIfAny(documents);

        const linksToShare =
            documents.length > 1
                ? documents.map((d) => d.data.access_url).join(", ")
                : documents[0].data.access_url;

        await browser.navigator.clipboard.writeText(linksToShare);
        const message =
            documents.length > 1
                ? _t("Links copied to clipboard!")
                : _t("Link copied to clipboard!");
        this.notification.add(message, { type: "success" });
    }

    /**
     * Unselect the records in the kanban / list view.
     */
    onUnselectAll() {
        this.env.model.root.selection.forEach((record) => {
            record.toggleSelection(false);
        });
        this.env.model.root.selectDomain(false);
    }

    /**
     * Return the folders of all documents in the view (duplicated are removed).
     */
    get allFoldersIds() {
        const folderIds = this.env.model.root.records
            .map((d) => d.data.folder_id[0])
            .filter((f) => f);

        if (this.currentFolderId && typeof this.currentFolderId === "number") {
            folderIds.push(this.currentFolderId);
        }

        return [...new Set(folderIds)];
    }

    /**
     * Return the common list of actions for the selected / previewed document folders.
     */
    get embeddedActions() {
        if (!this.targetRecords[0]?.data.available_embedded_actions_ids?.records.length) {
            return [];
        }
        const actionsList = this.targetRecords.map((d) =>
            d.data.available_embedded_actions_ids.records.map((rec) => ({
                id: rec.resId,
                name: rec.data.display_name,
            }))
        );
        const actionsListIds = actionsList.map((actions) => actions.map((a) => a.id));
        return actionsList[0].filter((action) =>
            actionsListIds.every((a) => a.includes(action.id))
        );
    }

    /**
     * Return the current folder ID.
     */
    get currentFolderId() {
        return this.env.searchModel.getSelectedFolderId();
    }

    /**
     * Records on which we will execute the actions / see the chatter.
     */
    get targetRecords() {
        return this.documentsState.previewedDocument
            ? [this.documentsState.previewedDocument.record]
            : this.env.model.root.selection;
    }

    async notifyChange() {
        await this.env.model.load();
        await this.env.model.notify();
        await this.env.searchModel._reloadSearchModel(true);
        // The preview will be closed, just update the state for now
        this.documentService.setPreviewedDocument(null);
    }

    get pathBreadcrumbs() {
        // users come from another app
        if (this.env.model.config.context.active_model) {
            return [
                ...this.env.config.breadcrumbs.slice(0, -1),
                {
                    name: this.env.searchModel.getSelectedFolder().display_name,
                },
            ];
        }

        return this.env.searchModel.getSelectedFolderAndParents().reverse().map(folder => {
            return {
                jsId: folder.id,
                name: folder.display_name,
                onSelected: () => {
                    const folderSection = this.env.searchModel.getSections()[0];
                    this.env.searchModel.toggleCategoryValue(folderSection.id, folder.id);
                }
            }
        });
    }

    /**
     * At the time of writing, documents in list view are missing
     * `access_url`. The issue has been fixed by editing the XML;
     * This method is a fallback for clients still having the old XML.
     */
    async populateMissingAccessURLsIfAny(documents) {
        if (documents.every(({ data }) => data.access_url)) {
            return;
        }

        const accessURLsMap = Object.fromEntries(
            (await this.orm.read(
                "documents.document",
                documents.map(({ data: { id } }) => id),
                ["access_url"]
            )).map(({ id, access_url}) => [id, access_url])
        )

        documents.forEach(({ data }) => data.access_url = accessURLsMap[data.id]);
    }
}

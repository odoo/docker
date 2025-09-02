/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { _t } from "@web/core/l10n/translation";
import { DocumentsControllerMixin } from "@documents/views/documents_controller_mixin";
import { openDeleteConfirmationDialog, preSuperSetup, useDocumentView } from "@documents/views/hooks";
import { useRef, useState } from "@odoo/owl";

export class DocumentsListController extends DocumentsControllerMixin(ListController) {
    static template = "documents.DocumentsListController";
    setup() {
        preSuperSetup();
        super.setup(...arguments);
        this.uploadFileInputRef = useRef("uploadFileInput");
        const properties = useDocumentView(this.documentsViewHelpers());
        Object.assign(this, properties);

        this.documentStates = useState({
            previewStore: {},
        });
    }

    /**
     * Override this to add view options.
     */
    documentsViewHelpers() {
        return {
            getSelectedDocumentsElements: () =>
                this.root?.el?.querySelectorAll(
                    ".o_data_row.o_data_row_selected .o_list_record_selector"
                ) || [],
            setPreviewStore: (previewStore) => {
                this.documentStates.previewStore = previewStore;
            },
            isRecordPreviewable: this.isRecordPreviewable.bind(this),
        };
    }

    getStaticActionMenuItems() {
        const isM2MGrouped = this.model.root.isM2MGrouped;
        return {
            export: {
                isAvailable: () => this.isExportEnable,
                sequence: 10,
                description: _t("Export"),
                callback: () => this.onExportData(),
            },
            delete: {
                isAvailable: () => {
                    return this.activeActions.delete
                        && !isM2MGrouped
                        && this.model.root.records.length;
                },
                sequence: 40,
                description: _t("Delete"),
                callback: () => {
                    return this.model.root.records[0].isActive
                        ? this.onArchiveSelectedRecords()
                        : this.onDeleteSelectedRecords();
                },
            },
        };
    }

    async onDeleteSelectedRecords() {
        if (!(await openDeleteConfirmationDialog(this.model, true))) {
            return;
        }
        const root = this.model.root;
        await root.deleteRecords(root.records.filter((record) => record.selected));
        await this.model.notify();
        await this.model.env.documentsView.bus.trigger("documents-close-preview");
    }

    async onArchiveSelectedRecords() {
        if (!(await openDeleteConfirmationDialog(this.model, false))) {
            return;
        }
        await this.toggleArchiveState(true);
        await this.model.env.documentsView.bus.trigger("documents-close-preview");
    }

    isRecordPreviewable(record) {
        return record.isViewable();
    }
}

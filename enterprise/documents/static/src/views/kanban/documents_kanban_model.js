/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { useService } from "@web/core/utils/hooks";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import {
    DocumentsModelMixin,
    DocumentsRecordMixin,
} from "../documents_model_mixin";

export class DocumentsKanbanModel extends DocumentsModelMixin(RelationalModel) {
    setup() {
        super.setup(...arguments);
        this.documentService = useService("document.document");
    }

    /**
     * Ensure that when coming from a URL with a document token, the document is present in the first page.
     */
    async _loadData(config) {
        const data = await super._loadData(config);
        const documentIdToRestore = this.documentService.getOnceDocumentIdToRestore();
        if (
            documentIdToRestore &&
            !data.records.some((record) => record.id === documentIdToRestore)
        ) {
            const missingData = await super._loadData({
                ...config,
                domain: Domain.and([config.domain, [["id", "=", documentIdToRestore]]]).toList(),
            });
            if (missingData?.records?.length) {
                data.records.push(missingData.records[0]);
            }
        }
        return data;
    }
}

export class DocumentsKanbanRecord extends DocumentsRecordMixin(RelationalModel.Record) {

    async onReplaceDocument(ev) {
        if (!ev.target.files.length) {
            return;
        }
        await this.model.env.documentsView.bus.trigger("documents-upload-files", {
            files: ev.target.files,
            accessToken: this.data.access_token,
        });
        ev.target.value = "";
    }
}
DocumentsKanbanModel.Record = DocumentsKanbanRecord;

import { Plugin } from "@html_editor/plugin";
import { isPhrasingContent } from "@html_editor/utils/dom_info";

export class InsertPendingElementPlugin extends Plugin {
    static id = "insertPendingElement";
    static dependencies = ["history", "dom", "selection"];
    resources = {
        start_edition_handlers: this.insertEmbeddedBluePrint.bind(this),
    };

    insertEmbeddedBluePrint() {
        const { resModel, resId } = this.config.getRecordInfo();
        const embeddedBlueprint =
            this.services.knowledgeCommandsService.popPendingEmbeddedBlueprint({
                field: "body",
                resId,
                model: resModel,
            });
        if (embeddedBlueprint) {
            let insert;
            if (isPhrasingContent(embeddedBlueprint)) {
                insert = () => {
                    // insert phrasing content
                    const paragraph = document.createElement("p");
                    paragraph.appendChild(embeddedBlueprint);
                    this.dependencies.selection.setCursorEnd(this.editable);
                    this.dependencies.dom.insert(paragraph);
                    this.dependencies.history.addStep();
                };
            } else {
                insert = () => {
                    // insert block content
                    this.dependencies.selection.setCursorEnd(this.editable);
                    this.dependencies.dom.insert(embeddedBlueprint);
                    const paragraph = document.createElement("p");
                    paragraph.appendChild(document.createElement("br"));
                    this.dependencies.selection.setCursorEnd(this.editable);
                    this.dependencies.dom.insert(paragraph);
                    this.dependencies.history.addStep();
                };
            }
            insert();
            this.editable.addEventListener("onHistoryResetFromPeer", insert, { once: true });
        }
    }
}

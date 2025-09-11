import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";

export class EmbeddedClipboardPlugin extends Plugin {
    static id = "embeddedClipboard";
    static dependencies = ["history", "dom", "selection"];
     resources = {
        user_commands: [
            {
                id: "insertClipboard",
                title: _t("Clipboard"),
                description: _t("Add a clipboard section"),
                icon: "fa-pencil-square",
                run: this.insertClipboard.bind(this),
            }
        ],
        powerbox_items: [
            {
                categoryId: "media",
                commandId: "insertClipboard",
                isAvailable: (selection) =>
                    !closestElement(selection.anchorNode, "[data-embedded='clipboard']"),
            },
        ],
        mount_component_handlers: this.setupNewClipboard.bind(this),
    };

    insertClipboard() {
        const clipboardBlock = renderToElement("knowledge.EmbeddedClipboardBlueprint");
        this.dependencies.dom.insert(clipboardBlock);
        this.dependencies.selection.setCursorStart(clipboardBlock.querySelector("p"));
        this.dependencies.history.addStep();
    }

    setupNewClipboard({ name, env }) {
        if (name === "clipboard") {
            Object.assign(env, {
                editorShared: {
                    preserveSelection: this.dependencies.selection.preserveSelection,
                },
            });
        }
    }
}

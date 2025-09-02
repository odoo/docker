/** @odoo-module */

import { components, helpers } from "@odoo/o-spreadsheet";
import { Component, useRef, useState, useEffect } from "@odoo/owl";
import { formatToLocaleString } from "../../helpers/misc";
import { _t } from "@web/core/l10n/translation";
import { pyToJsLocale } from "@web/core/l10n/utils";

const { createActions } = helpers;

export class VersionHistoryItem extends Component {
    static template = "spreadsheet_edition.VersionHistoryItem";
    static components = { Menu: components.Menu, TextInput: components.TextInput };
    static props = {
        active: Boolean,
        revision: Object,
        onActivation: { optional: true, type: Function },
        onBlur: { optional: true, type: Function },
        editable: { optional: true, type: Boolean },
    };
    setup() {
        this.menuState = useState({
            isOpen: false,
            position: null,
        });
        this.state = useState({ editName: this.defaultName });
        this.menuButtonRef = useRef("menuButton");
        this.itemRef = useRef("item");

        useEffect(() => {
            if (this.props.active) {
                this.itemRef.el.scrollIntoView({
                    behavior: "smooth",
                    block: "center",
                    inline: "nearest",
                });
            }
        });
    }

    get revision() {
        return this.props.revision;
    }

    get defaultName() {
        return (
            this.props.revision.name || this.formatRevisionTimeStamp(this.props.revision.timestamp)
        );
    }

    get formattedTimeStamp() {
        return this.formatRevisionTimeStamp(this.props.revision.timestamp);
    }

    get isLatestVersion() {
        return (
            this.env.historyManager.getRevisions()[0].nextRevisionId ===
            this.revision.nextRevisionId
        );
    }

    renameRevision(newName) {
        this.state.editName = newName;
        if (!this.state.editName) {
            this.state.editName = this.defaultName;
        }
        if (this.state.editName !== this.defaultName) {
            this.env.historyManager.renameRevision(this.revision.id, this.state.editName);
        }
    }

    get menuItems() {
        const actions = [
            {
                name: _t("Make a copy"),
                execute: (env) => {
                    env.historyManager.forkHistory(this.revision.id);
                },
                isReadonlyAllowed: true,
            },
            {
                name: _t("Restore this version"),
                execute: (env) => {
                    env.historyManager.restoreRevision(this.revision.id);
                },
                isReadonlyAllowed: true,
            },
        ];
        if (this.props.editable) {
            actions.unshift({
                name: this.revision.name ? _t("Rename") : _t("Name this version"),
                execute: () => {
                    this.inputRef.el.focus();
                },
                isReadonlyAllowed: true,
            });
        }

        return createActions(actions);
    }

    openMenu() {
        this.props.onActivation(this.revision.nextRevisionId);
        const { x, y, height, width } = this.menuButtonRef.el.getBoundingClientRect();
        this.menuState.isOpen = true;
        this.menuState.position = { x: x + width, y: y + height };
    }

    closeMenu() {
        this.menuState.isOpen = false;
        this.menuState.position = null;
    }

    formatRevisionTimeStamp(ISOdatetime) {
        const code = pyToJsLocale(this.env.model.getters.getLocale().code);
        return formatToLocaleString(ISOdatetime, code);
    }
}

/** @odoo-module */

import { calendarView } from "@web/views/calendar/calendar_view";
import { registry } from "@web/core/registry";

import { Component, useState } from "@odoo/owl";
import { InteractiveEditorSidebar } from "@web_studio/client_action/view_editor/interactive_editor/interactive_editor_sidebar";
import { Property } from "@web_studio/client_action/view_editor/property/property";
import { SidebarViewToolbox } from "@web_studio/client_action/view_editor/interactive_editor/sidebar_view_toolbox/sidebar_view_toolbox";
import { fieldsToChoices } from "@web_studio/client_action/view_editor/editors/utils";
import { SCALE_LABELS } from "@web/views/calendar/calendar_controller";
import { useEditNodeAttributes } from "@web_studio/client_action/view_editor/view_editor_model";

export class CalendarEditorSidebar extends Component {
    static template = "web_studio.ViewEditor.CalendarEditorSidebar";
    static props = {
        openViewInForm: { type: Function, optional: true },
        openDefaultValues: { type: Function, optional: true },
    };
    static components = {
        InteractiveEditorSidebar,
        Property,
        SidebarViewToolbox,
    };

    setup() {
        this.viewEditorModel = useState(this.env.viewEditorModel);
        this.editArchAttributes = useEditNodeAttributes({ isRoot: true });
    }

    get archInfo() {
        return this.viewEditorModel.controllerProps.archInfo;
    }

    onViewAttributeChanged(value, name) {
        return this.editArchAttributes({ [name]: value });
    }

    get quickCreateFields() {
        return fieldsToChoices(this.viewEditorModel.fields, ["char"], (field) => field.store);
    }

    get startDateFields() {
        return fieldsToChoices(this.viewEditorModel.fields, ["date", "datetime"]);
    }

    get delayFields() {
        return fieldsToChoices(this.viewEditorModel.fields, ["float", "integer"]);
    }

    get colorFields() {
        return fieldsToChoices(this.viewEditorModel.fields, ["many2one", "selection"]);
    }

    get allDayFields() {
        return fieldsToChoices(this.viewEditorModel.fields, ["boolean"]);
    }

    get modeChoices() {
        return this.viewEditorModel.controllerProps.archInfo.scales.map((value) => {
            return {
                value,
                label: SCALE_LABELS[value],
            };
        });
    }
}

registry.category("studio_editors").add("calendar", {
    ...calendarView,
    Sidebar: CalendarEditorSidebar,
});

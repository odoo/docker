/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { onWillStart } from "@odoo/owl";

export class NewViewDialog extends ConfirmationDialog {
    static template = "web_studio.NewViewDialog";
    static GROUPABLE_TYPES = ["many2one", "char", "boolean", "selection", "date", "datetime"];
    static MEASURABLE_TYPES = ["integer", "float"];
    static props = {
        ...ConfirmationDialog.props,
        viewType: String,
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.studio = useService("studio");
        this.mandatoryStopDate = ["gantt", "cohort"].includes(this.viewType);

        this.title = _t("Generate %s View", this.viewType);

        this.fieldsChoice = {
            date_start: null,
            date_stop: null,
        };

        onWillStart(async () => {
            const fieldsGet = await this.orm.call(this.studio.editedAction.res_model, "fields_get");
            const fields = Object.entries(fieldsGet).map(([fName, field]) => {
                field.name = fName;
                return field;
            });
            fields.sort((first, second) => {
                if (first.string === second.string) {
                    return 0;
                }
                if (first.string < second.string) {
                    return -1;
                }
                if (first.string > second.string) {
                    return 1;
                }
            });
            this.computeSpecificFields(fields);
        });
    }

    get viewType() {
        return this.props.viewType;
    }

    /**
     * Compute date, row and measure fields.
     */
    computeSpecificFields(fields) {
        this.dateFields = [];
        this.rowFields = [];
        this.measureFields = [];
        fields.forEach((field) => {
            if (field.store) {
                // date fields
                if (field.type === "date" || field.type === "datetime") {
                    this.dateFields.push(field);
                }
                // row fields
                if (this.constructor.GROUPABLE_TYPES.includes(field.type)) {
                    this.rowFields.push(field);
                }
                // measure fields
                if (this.constructor.MEASURABLE_TYPES.includes(field.type)) {
                    // id and sequence are not measurable
                    if (field.name !== "id" && field.name !== "sequence") {
                        this.measureFields.push(field);
                    }
                }
            }
        });
        if (this.dateFields.length) {
            this.fieldsChoice.date_start = this.dateFields[0].name;
            this.fieldsChoice.date_stop = this.dateFields[0].name;
        }
    }

    async _confirm() {
        await rpc("/web_studio/create_default_view", {
            model: this.studio.editedAction.res_model,
            view_type: this.viewType,
            attrs: this.fieldsChoice,
            context: user.context,
        });
        super._confirm();
    }
}
delete NewViewDialog.props.body;

/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { GraphModel } from "@web/views/graph/graph_model";

export class HelpdeskTicketGraphModel extends GraphModel {
    /**
     * @override
     */
    _getDefaultFilterLabel(field) {
        if (field.fieldName === "sla_deadline") {
            return _t("Deadline reached");
        }
        if (field.fieldName == "user_id") {
            return _t("Unassigned");
        }
        return super._getDefaultFilterLabel(field);
    }
}

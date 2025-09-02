/** @odoo-module */

import { formatFloatTime } from "@web/views/fields/formatters";
import { formatFloat } from "@web/core/utils/numbers";

import { Component } from "@odoo/owl";

export class EmployeeOvertimeIndication extends Component {
    static props = {
        allocated_hours: { type: Number, optional: true },
        uom: { type: String, optional: true },
        worked_hours: { type: Number, optional: true },
    };
    static defaultProps = {
        uom: "hours",
    };
    static template = "timesheet_grid.EmployeeOvertimeIndication";

    get shouldShowHours() {
        return this.props.allocated_hours > 0;
    }

    get colorClasses() {
        if (!this.shouldShowHours) {
            return "";
        }
        return this.props.worked_hours < this.props.allocated_hours ? "text-danger" : "text-success";
    }

    get overtime() {
        return this.props.worked_hours - this.props.allocated_hours;
    }

    get overtimeIndication() {
        if (!this.shouldShowHours) {
            return null;
        }
        if (this.overtime === 0) {
            return null; // nothing to display
        }
        let overtimeIndication = this.overtime > 0 ? "+" : "";
        if (this.props.uom === "days") {
            // format in days
            overtimeIndication += formatFloat(this.overtime);
        } else {
            // format in hours
            overtimeIndication += formatFloatTime(this.overtime);
        }
        return overtimeIndication;
    }
}

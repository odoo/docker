import { HrGanttRenderer } from "@hr_gantt/hr_gantt_renderer";
 import {AttendanceGanttRowProgressBar} from "./attendance_row_progress_bar";

 export class AttendanceGanttRenderer extends HrGanttRenderer {
    static components = {
        ...HrGanttRenderer.components,
        GanttRowProgressBar: AttendanceGanttRowProgressBar,
    };
    onPillClicked(ev, pill) {
        this.model.mutex.exec(
            () => this.props.openDialog({ resId: pill.record.id })
        )
    }
    /**
     * @override
     * If multiple columns have been selected, keep the check_out's value overwise remove it.
     */
    onCreate(rowId, columnStart, columnStop) {
        const { start, stop } = this.getColumnStartStop(columnStart, columnStop);
        const context = this.model.getDialogContext({rowId, start, stop, withDefault: true});
        if (columnStart == columnStop){
            delete context.check_out;
            delete context.default_check_out;
        }
        this.props.create(context);
    }
}


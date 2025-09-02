import { ProjectTaskCalendarController } from "@project/views/project_task_calendar/project_task_calendar_controller";

export class FsmMyTaskCalendarController extends ProjectTaskCalendarController {
    async editRecord(record, context = {}, shouldFetchFormViewId = true) {
        if (this.env.isSmall) {
            return this.action.doAction("industry_fsm.project_task_fsm_mobile_server_action");
        }
        return super.editRecord(record, context, shouldFetchFormViewId);
    }
}

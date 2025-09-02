import { ganttView } from "@web_gantt/gantt_view";
import { registry } from "@web/core/registry";
import { ProjectGanttRenderer } from "./project_gantt_renderer";

export const projectGanttView = {
    ...ganttView,
    Renderer: ProjectGanttRenderer,
};

registry.category("views").add("project_gantt", projectGanttView);

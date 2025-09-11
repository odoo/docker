import { fields, models } from "@web/../tests/web_test_helpers";

export class HelpdeskTeam extends models.Model {
    _name = "helpdesk.team";

    name = fields.Char();
    use_sla = fields.Boolean({ string: "Use SLA" });
    use_alias = fields.Boolean({ string: "Use Alias" });
    use_helpdesk_timesheet = fields.Boolean({ string: "Use Timesheet" });
    stage_ids = fields.Many2many({ relation: "helpdesk.stage" });

    _records = [
        { name: "Team 1", use_sla: true, use_alias: true },
        { name: "Team 2", use_alias: true },
    ];
}

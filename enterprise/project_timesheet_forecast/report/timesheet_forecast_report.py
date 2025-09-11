# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.sql import drop_view_if_exists, SQL


class TimesheetForecastReport(models.Model):

    _name = "project.timesheet.forecast.report.analysis"
    _description = "Timesheet & Planning Statistics"
    _auto = False
    _rec_name = 'entry_date'
    _order = 'entry_date desc'

    entry_date = fields.Date('Date', readonly=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', readonly=True)
    company_id = fields.Many2one('res.company', string="Company", readonly=True)
    project_id = fields.Many2one('project.project', string='Project', readonly=True)
    line_type = fields.Selection([('forecast', 'Planning'), ('timesheet', 'Timesheet')], string='Type', readonly=True)
    effective_hours = fields.Float('Effective Time', readonly=True)
    planned_hours = fields.Float('Planned Time', readonly=True)
    difference = fields.Float('Time Remaining', readonly=True)
    user_id = fields.Many2one('res.users', string='Assigned to', readonly=True)
    is_published = fields.Boolean(readonly=True)
    effective_costs = fields.Float('Effective Costs', readonly=True)
    planned_costs = fields.Float('Planned Costs', readonly=True)

    def _number_of_days_without_weekend(self):
        return """
            WITH no_weekend_days AS (
                SELECT
                    F.id AS forecast_id,
                    GREATEST(COUNT(*), 1) AS no_weekend_days_count
                FROM
                    planning_slot F,
                    generate_series(F.start_datetime, F.end_datetime, '1 day') AS g(day)
                WHERE EXTRACT(ISODOW FROM g.day) < 6
                GROUP BY F.id
            )
        """

    @api.model
    def _select(self):
        nb_days_with_clause = self._number_of_days_without_weekend()
        select_str = """
            %s
            SELECT
                d::date AS entry_date,
                F.employee_id AS employee_id,
                F.company_id AS company_id,
                F.project_id AS project_id,
                F.user_id AS user_id,
                0.0 AS effective_hours,
                0.0 As effective_costs,
                F.allocated_hours / W.no_weekend_days_count AS planned_hours,
                (F.allocated_hours / W.no_weekend_days_count) * E.hourly_cost AS planned_costs,
                F.allocated_hours / W.no_weekend_days_count AS difference,
                'forecast' AS line_type,
                F.id AS id,
                CASE WHEN F.state = 'published' THEN TRUE ELSE FALSE END AS is_published
        """ % (nb_days_with_clause)
        return select_str

    @api.model
    def _from(self):
        from_str = """
            FROM generate_series(
                (SELECT min(start_datetime) FROM planning_slot)::date,
                (SELECT max(end_datetime) FROM planning_slot)::date,
                '1 day'::interval
            ) d
                LEFT JOIN planning_slot F ON d::date >= F.start_datetime::date AND d::date <= F.end_datetime::date
                LEFT JOIN hr_employee E ON F.employee_id = E.id
                LEFT JOIN resource_resource R ON E.resource_id = R.id
                LEFT JOIN no_weekend_days W ON F.id = W.forecast_id
        """
        return from_str

    @api.model
    def _select_union(self):
        select_str = """
            SELECT
                A.date AS entry_date,
                E.id AS employee_id,
                A.company_id AS company_id,
                A.project_id AS project_id,
                A.user_id AS user_id,
                A.unit_amount / UOM.factor * HOUR_UOM.factor AS effective_hours,
                (A.unit_amount / UOM.factor * HOUR_UOM.factor) * E.hourly_cost AS effective_costs,
                0.0 AS planned_hours,
                0.0 AS planned_costs,
                -A.unit_amount / UOM.factor * HOUR_UOM.factor AS difference,
                'timesheet' AS line_type,
                -A.id AS id,
                TRUE AS is_published
        """
        return select_str

    @api.model
    def _from_union(self):
        return """
            FROM account_analytic_line A
                LEFT JOIN hr_employee E ON A.employee_id = E.id
        """

    @api.model
    def _from_union_timesheet_uom(self):
        return """
            LEFT JOIN uom_uom UOM ON A.product_uom_id = UOM.id,
            (
                SELECT U.factor
                  FROM uom_uom U
                 WHERE U.id = %s
            ) HOUR_UOM
        """ % (self.env.ref('uom.product_uom_hour').id)

    @api.model
    def _where_union(self):
        where_str = """
            WHERE A.project_id IS NOT NULL
        """
        return where_str

    @api.model
    def _where(self):
        where_str = """
            WHERE
                EXTRACT(ISODOW FROM d.date) IN (
                    SELECT A.dayofweek::integer+1 FROM resource_calendar_attendance A WHERE A.calendar_id = R.calendar_id
                )
        """
        return where_str

    def init(self):
        query = "(%s %s %s) UNION (%s %s %s %s)" % (
            self._select(),
            self._from(),
            self._where(),
            self._select_union(),
            self._from_union(),
            self._from_union_timesheet_uom(),
            self._where_union()
        )

        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL("""CREATE or REPLACE VIEW %s as (%s)""", SQL.identifier(self._table), SQL(query)))

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if not orderby and groupby:
            orderby_list = [groupby] if isinstance(groupby, str) else groupby
            orderby_list = [field.split(':')[0] for field in orderby_list]
            orderby = ','.join([f"{field} desc" if field == 'entry_date' else field for field in orderby_list])
        return super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

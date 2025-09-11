# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class TimesheetForecastReport(models.Model):
    _inherit = "project.timesheet.forecast.report.analysis"

    planned_revenues = fields.Float('Planned Revenues', readonly=True)
    effective_revenues = fields.Float('Effective Revenues', readonly=True)
    planned_margin = fields.Float('Planned Margin', readonly=True)
    effective_margin = fields.Float('Effective Margin', readonly=True)
    planned_billable_hours = fields.Float('Planned Billable Time', readonly=True)
    effective_billable_hours = fields.Float('Effective Billable Time', readonly=True)
    planned_non_billable_hours = fields.Float('Planned Non-Billable Time', readonly=True)
    effective_non_billable_hours = fields.Float('Effective Non-Billable Time', readonly=True)

    @api.model
    def _select(self):
        return super()._select() + """,
            (F.allocated_hours / W.no_weekend_days_count) * (SOL.price_unit * P_UOM.factor / HOUR_UOM.factor) AS planned_revenues,
            (F.allocated_hours / W.no_weekend_days_count) * (SOL.price_unit * P_UOM.factor / HOUR_UOM.factor - E.hourly_cost) AS planned_margin,
            CASE WHEN F.sale_line_id IS NOT NULL THEN
                (F.allocated_hours / W.no_weekend_days_count)
            ELSE 0 END AS planned_billable_hours,
            CASE WHEN F.sale_line_id IS NULL THEN
                (F.allocated_hours / W.no_weekend_days_count)
            ELSE 0 END AS planned_non_billable_hours,
            0.0 AS effective_revenues,
            0.0 AS effective_margin,
            0.0 AS effective_billable_hours,
            0.0 AS effective_non_billable_hours
        """

    @api.model
    def _from(self):
        return super()._from() + """
            LEFT JOIN sale_order_line SOL ON SOL.id = F.sale_line_id
            LEFT JOIN uom_uom P_UOM ON SOL.product_uom = P_UOM.id,
            (SELECT U.factor FROM uom_uom U WHERE U.id = %s) HOUR_UOM
        """ % (self.env.ref('uom.product_uom_hour').id)

    @api.model
    def _select_union(self):
        return super()._select_union() + """,
            0.0 AS planned_revenues,
            0.0 AS planned_margin,
            0.0 AS planned_billable_hours,
            0.0 AS planned_non_billable_hours,
            (A.unit_amount / UOM.factor * HOUR_UOM.factor) * (SOL.price_unit * P_UOM.factor / HOUR_UOM.factor) AS effective_revenues,
            (A.unit_amount / UOM.factor * HOUR_UOM.factor) * (SOL.price_unit * P_UOM.factor / HOUR_UOM.factor - E.hourly_cost) AS effective_margin,
            CASE WHEN A.so_line IS NOT NULL THEN (A.unit_amount / UOM.factor * HOUR_UOM.factor) ELSE 0 END AS effective_billable_hours,
            CASE WHEN A.so_line IS NULL THEN (A.unit_amount / UOM.factor * HOUR_UOM.factor) ELSE 0 END AS effective_non_billable_hours
        """

    @api.model
    def _from_union(self):
        return super()._from_union() + """
            LEFT JOIN project_task T ON A.task_id = T.id
            LEFT JOIN sale_order_line SOL ON A.so_line = SOL.id
            LEFT JOIN uom_uom P_UOM ON SOL.product_uom = P_UOM.id
        """

    @api.model
    def _where_union(self):
        return super()._where_union() + "AND A.employee_id = E.id"

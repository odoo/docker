# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class QualityPoint(models.Model):
    _inherit = "quality.point"

    @api.model
    def _get_domain_for_production(self, quality_points_domain):
        return quality_points_domain

    @api.constrains('measure_on', 'picking_type_ids')
    def _check_measure_on(self):
        for point in self:
            if point.measure_on == 'move_line' and any(pt.code == 'mrp_operation' for pt in point.picking_type_ids):
                raise UserError(_("The Quantity quality check type is not possible with manufacturing operation types."))


class QualityCheck(models.Model):
    _inherit = "quality.check"

    production_id = fields.Many2one(
        'mrp.production', 'Production Order', check_company=True)

    def _compute_qty_line(self):
        record_without_production = self.env['quality.check']
        for qc in self:
            if qc.production_id:
                qc.qty_line = qc.production_id.qty_producing
            else:
                record_without_production |= qc
        return super(QualityCheck, record_without_production)._compute_qty_line()

    def _can_move_line_to_failure_location(self):
        self.ensure_one()
        if self.production_id and self.quality_state == 'fail' and self.point_id.measure_on == 'move_line':
            self.move_line_id = self.production_id.finished_move_line_ids.filtered(
                lambda ml: ml.product_id == self.product_id
            )
            return True

        return super()._can_move_line_to_failure_location()


class QualityAlert(models.Model):
    _inherit = "quality.alert"

    production_id = fields.Many2one(
        'mrp.production', "Production Order", check_company=True)

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models, Command


class QualityCheck(models.Model):
    _inherit = 'quality.check'

    def add_check_in_chain(self, notify_bom=False):
        self.ensure_one()
        super().add_check_in_chain(notify_bom=notify_bom)
        if not self.workorder_id.production_id.bom_id or not self.env.user.has_group('mrp.group_mrp_user'):
            return
        # Need to sudo all ECOs calls as we want to make this available to all MRP basic users.
        eco = self.env['mrp.eco'].sudo().search([
            ('bom_id', '=', self.workorder_id.production_id.bom_id.id),
            ('state', 'in', ('confirmed', 'progress')),
        ], limit=1)
        if not eco:
            wo_name = f'{self.workorder_id.name}/{self.workorder_id.production_id.name}'
            name = _("Instruction Suggestions (%(wo_name)s)", wo_name=wo_name)
            eco_type = self.env.ref('mrp_plm.ecotype_bom_update', raise_if_not_found=False)
            if not eco_type:
                eco_type = self.env['mrp.eco.type'].sudo().search([], limit=1)
            stage = self.env['mrp.eco.stage'].sudo().search([
                ('type_ids', 'in', eco_type.ids)
            ], limit=1)
            eco = self.env['mrp.eco'].sudo().create({
                'name': name,
                'product_tmpl_id': self.product_id.product_tmpl_id.id,
                'bom_id': self.workorder_id.production_id.bom_id.id,
                'type_id': eco_type.id,
                'stage_id': stage.id,
            })
            eco.action_new_revision()

        # get the operation in the eco's new bom similar to the current one
        operation = eco.new_bom_id.operation_ids.filtered(lambda o: o._get_sync_values() == self.workorder_id.operation_id._get_sync_values())
        quality_point_data = {
            'title': _("New Step Suggestion: %s", self.title or ''),
            'operation_id': operation.id,
            'product_ids': self.product_id.ids,
            'team_id': self.team_id.id,
            'company_id': self.company_id.id,
            'test_type_id': self.test_type_id.id,
            'picking_type_ids': [Command.link(self.workorder_id.production_id.picking_type_id.id)],
            'source_document': 'step',
            'note': self.note,
            'worksheet_document': self.worksheet_document,
        }
        # Would need 'quality.group_quality_manager' otherwise, but we want this to be available for MRP basic users.
        point = self.env['quality.point'].sudo().create(quality_point_data)
        self.point_id = point
        # Resequence quality points according to checks
        current_sequence = 10
        points = self.env['quality.point'].search([('operation_id', '=', operation.id)])
        check = self.env['quality.check'].search([
            ('point_id.operation_id', 'in', (operation.id, self.workorder_id.operation_id.id)),
            ('previous_check_id', '=', False), ('production_id', '=', self.production_id.id)
        ])
        while check:
            point = check.point_id if check.point_id.operation_id == operation else points.filtered(lambda p: p._get_sync_values() == check.point_id._get_sync_values())[0]
            points -= point
            if point.sequence != current_sequence:
                point.sequence = current_sequence
            current_sequence += 10
            check = check.next_check_id

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    ucm_code = fields.Char("UCM code", groups="hr.group_hr_user")

    @api.constrains('ucm_code')
    def _check_ucm_code(self):
        if any(we.ucm_code and len(we.ucm_code) not in [2, 3] for we in self):
            raise ValidationError(_('The code should have 2 or 3 characters!'))

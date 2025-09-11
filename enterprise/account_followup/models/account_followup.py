# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from datetime import timedelta


class FollowupLine(models.Model):
    _name = 'account_followup.followup.line'
    _description = 'Follow-up Criteria'
    _order = 'delay asc'
    _check_company_auto = True

    name = fields.Char('Description', required=True, translate=True)
    delay = fields.Integer('Due Days', required=True,
                           help="The number of days after the due date of the invoice to wait before sending the reminder. "
                                "Can be negative if you want to send the reminder before the invoice due date.")
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)

    mail_template_id = fields.Many2one(comodel_name='mail.template', domain="[('model', '=', 'res.partner')]")
    send_email = fields.Boolean('Send Email', default=True)
    join_invoices = fields.Boolean(string="Attach Invoices", default=True)
    additional_follower_ids = fields.Many2many(string="Add followers", comodel_name='res.users',
                                               help="If set, those users will be added as followers on the partner and receive notifications about any email reply made by the partner on the reminder email.")

    sms_template_id = fields.Many2one(comodel_name='sms.template', domain="[('model', '=', 'res.partner')]")
    send_sms = fields.Boolean('Send SMS Message')

    create_activity = fields.Boolean(string='Schedule Activity')
    activity_summary = fields.Char(string='Summary')
    activity_note = fields.Text(string='Note')
    activity_type_id = fields.Many2one(comodel_name='mail.activity.type', string='Activity Type', default=False)
    activity_default_responsible_type = fields.Selection([('followup', 'Follow-up Responsible'), ('salesperson', 'Salesperson'), ('account_manager', 'Account Manager')],
                                                         string='Responsible', default='followup', required=True,
                                                         help="Determine who will be assigned to the activity:\n"
                                                              "- Follow-up Responsible (default)\n"
                                                              "- Salesperson: Sales Person defined on the invoice\n"
                                                              "- Account Manager: Sales Person defined on the customer")

    auto_execute = fields.Boolean(string="Automatic", default=False)

    _sql_constraints = [
        ('days_uniq', 'unique(company_id, delay)', 'Days of the follow-up lines must be different per company'),
        ('uniq_name', 'unique(company_id, name)', 'A follow-up action name must be unique. This name is already set to another action.'),
    ]

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        default = dict(default or {})
        company_ids = [self.company_id.id]
        if 'company_id' in default:
            company_ids += default['company_id']

        highest_delay_per_company_id = {
            row['company_id'][0]: row['delay']
            for row in self.read_group(
                domain=[('company_id', 'in', company_ids)],
                fields=['company_id', 'delay:max'],
                groupby='company_id',
            )
        }
        for line, vals in zip(self, vals_list):
            if 'delay' not in default:
                # If several records from the same company are copied in batch, we need to ensure that their delay aren't
                # set to the same value, we offset it by highest existing delay + 15 arbitrary days (cumulative).
                company_id = default.get('company_id', line.company_id.id)
                highest_delay_per_company_id[company_id] += 15
                vals['delay'] = highest_delay_per_company_id[company_id]
            vals['name'] = default.get(
                'name',
                 _("%(delay)s days (copy of %(name)s)", delay=vals['delay'], name=line.name),
             )
        return vals_list

    @api.onchange('auto_execute')
    def _onchange_auto_execute(self):
        if self.auto_execute:
            self.create_activity = False

    def _get_next_date(self):
        """ Computes the next date used to set a next_followup_action_date for a partner

        The next date will be typically set in (next level delay - current level delay) days
        There are 3 exceptions to this:
        - no next level -> next date set in (current level delay - previous level delay) days
        - no next level AND only 1 level -> next date set in (current level delay) days
        - no level at all -> next date not set (handled by partner, this method won't be called)
        """
        self.ensure_one()
        next_followup = self._get_next_followup()
        if next_followup:
            delay = next_followup.delay - self.delay
        else:
            previous_followup = self._get_previous_followup()
            if previous_followup:
                delay = self.delay - previous_followup.delay
            else:
                delay = self.delay
        return fields.Date.context_today(self) + timedelta(days=delay)

    def _get_next_followup(self):
        self.ensure_one()
        return self.env['account_followup.followup.line'].search([('delay', '>', self.delay), ('company_id', '=', self.env.company.id)], order="delay asc", limit=1)

    def _get_previous_followup(self):
        self.ensure_one()
        return self.env['account_followup.followup.line'].search([('delay', '<', self.delay), ('company_id', '=', self.env.company.id)], order="delay desc", limit=1)

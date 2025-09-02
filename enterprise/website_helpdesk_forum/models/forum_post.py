# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ForumPost(models.Model):
    _inherit = 'forum.post'

    ticket_id = fields.Many2one('helpdesk.ticket', export_string_translation=False)
    show_ticket = fields.Boolean(compute='_compute_show_ticket', export_string_translation=False)

    @api.depends_context('uid')
    @api.depends('ticket_id')
    def _compute_show_ticket(self):
        allowed_tickets = self.ticket_id._filtered_access('read')
        for post in self:
            post.show_ticket = post.ticket_id in allowed_tickets

    @api.model
    def _search_get_detail(self, website, order, options):
        res = super()._search_get_detail(website, order, options)

        team = self.env['helpdesk.team']
        if options.get('helpdesk'):
            team = team.browse(self.env['ir.http']._unslug(options['helpdesk'])[1])

        if not team:
            return res

        domain = website.website_domain()
        domain += [('state', '=', 'active'), ('can_view', '=', True)]
        website_forum_ids = team.sudo().website_forum_ids
        if website_forum_ids:
            domain += [('forum_id', 'in', website_forum_ids.ids)]

        if options.get('max_date'):
            domain = [('create_date', '>=', options['max_date'])] + domain
        if options.get('tag'):
            domain = [('tag_ids.name', 'ilike', options['tag'])] + domain
        res['base_domain'] = [domain]
        res['search_fields'].append('tag_ids.name')

        return res

    def open_forum_post(self, edit=False):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/forum/%s/%s%s/%s' % (self.env['ir.http']._slug(self.forum_id), edit and 'post/' or '', self.env['ir.http']._slug(self), edit and 'edit' or ''),
            'target': 'self',
        }

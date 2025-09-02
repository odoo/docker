# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models, api


class Users(models.Model):
    _name = 'res.users'
    _inherit = 'res.users'
    @api.model_create_multi
    def create(self, vals_list):
        users = super(Users, self).create(vals_list)
        if not self.env.context.get('knowledge_skip_onboarding_article'):
            users.filtered(lambda user: not user.partner_share)._generate_tutorial_articles()
        return users

    def _generate_tutorial_articles(self):
        articles_to_create = []
        for user in self:
            self = self.with_context(lang=user.lang or self.env.user.lang)
            render_ctx = {'object': user}
            body = self.env['ir.qweb']._render(
                'knowledge.knowledge_article_user_onboarding',
                render_ctx,
                minimal_qcontext=True,
                raise_if_not_found=False
            )
            if not body:
                break

            articles_to_create.append({
                'article_member_ids': [(0, 0, {
                    'partner_id': user.partner_id.id,
                    'permission': 'write',
                })],
                'body': body,
                'icon': "👋",
                'internal_permission': 'none',
                'is_article_visible_by_everyone': False,
                'favorite_ids': [(0, 0, {
                    'sequence': 0,
                    'user_id': user.id,
                })],
                'name': _('Welcome %s', user.name),
            })

        if articles_to_create:
            self.env['knowledge.article'].sudo().create(articles_to_create)

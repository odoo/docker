# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class Website(models.Model):
    _inherit = "website"

    def get_suggested_controllers(self):
        suggested_controllers = super(Website, self).get_suggested_controllers()
        suggested_controllers.append((_('Helpdesk Customer Satisfaction'), self.env['ir.http']._url_for('/helpdesk/rating'), 'helpdesk'))
        return suggested_controllers

    def configurator_get_footer_links(self):
        links = super().configurator_get_footer_links()
        links.append({'text': _("Help"), 'href': '/help'})
        return links

class Menu(models.Model):
    _inherit = "website.menu"

    def _compute_visible(self):
        """ Display helpdesk team menus even if they are unpublished """
        helpdesk_menus = self.filtered(lambda menu: menu.url and menu.url[:9] == "/helpdesk")
        if self.env.user._is_internal(): # avoid extra query if not needed
            helpdesk_menus.is_visible = True
            return super(Menu, self - helpdesk_menus)._compute_visible()
        published_menus, = self.env['helpdesk.team']._read_group(
            [('is_published', '=', True), ('website_menu_id', '!=', False)],
            [], ['website_menu_id:recordset']
        )[0]
        for menu in helpdesk_menus:
            menu.is_visible = menu in published_menus
        return super(Menu, self - helpdesk_menus)._compute_visible()

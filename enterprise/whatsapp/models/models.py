# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import exceptions, models, _
from odoo.tools import format_datetime


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    def _whatsapp_get_portal_url(self):
        """ List is defined here else we need to create bridge modules. """
        if self._name in {
            'sale.order',
            'account.move',
            'project.project',
            'project.task',
            'purchase.order',
            'helpdesk.ticket',
        } and hasattr(self, 'get_portal_url'):
            self.ensure_one()
            return self.get_portal_url()
        contactus_page = self.env.ref('website.contactus_page', raise_if_not_found=False)
        return contactus_page.url if contactus_page else False

    def _whatsapp_get_responsible(self, related_message=False, related_record=False, whatsapp_account=False):
        """ Try to find suitable responsible users for a record.
         This is typically used when trying to find who to add to the discuss.channel created when
         a customer replies to a sent 'whatsapp.template'. In short: who should be notified.

         Heuristic is as follows:
         - Try to find a 'user_id/user_ids' field on the record, use that as responsible if available;
         - Always add the author of the original message
           (If you send a template to a customer, you should be able to reply to his questions.)
         - If nothing found, fallback on the first available among the following:
           - The creator of the record
           - The last editor of the record
           - Ultimate fallback is the people configured as 'notify_user_ids' on the whatsapp account

        For each of those, we only take into account active internal users, that are not the
        superuser, to avoid having the responsible set to 'Odoobot' for automated processes.

        This method can be overridden to force specific responsible users. """

        self.ensure_one()
        responsible_users = self.env['res.users']

        def filter_suitable_users(user):
            return user.active and user._is_internal() and not user._is_superuser()

        for field in ['user_id', 'user_ids']:
            if field in self._fields and self[field]:
                responsible_users = self[field].filtered(filter_suitable_users)

        if related_message:
            # add the message author even if we already have a responsible
            responsible_users |= related_message.author_id.user_ids.filtered(filter_suitable_users)

        if responsible_users:
            # do not go further if we found suitable users
            return responsible_users

        if related_message and not related_record:
            related_record = self.env[related_message.model].browse(related_message.res_id)

        if related_record:
            responsible_users = related_record.create_uid.filtered(filter_suitable_users)

            if not responsible_users:
                responsible_users = related_record.write_uid.filtered(filter_suitable_users)

        if not responsible_users:
            if not whatsapp_account:
                whatsapp_account = self.env['whatsapp.account'].search([], limit=1)

            responsible_users = whatsapp_account.notify_user_ids

        return responsible_users

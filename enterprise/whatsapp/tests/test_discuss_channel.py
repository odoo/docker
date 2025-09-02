# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo.addons.whatsapp.tests.common import WhatsAppCommon
from odoo.tests import tagged, users


@tagged('wa_message')
class DiscussChannel(WhatsAppCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_channel_wa, cls.test_channel_wa2, cls.test_channel_std = cls.env['discuss.channel'].create([
            {
                'channel_partner_ids': [(4, cls.user_wa_admin.partner_id.id)],
                'channel_type': 'whatsapp',
                'name': 'Dummy WA Channel',
                'wa_account_id': cls.whatsapp_account.id,
                'whatsapp_number': '911234567891',
                'whatsapp_partner_id': cls.whatsapp_customer.id,
            }, {
                'channel_partner_ids': [(4, cls.user_wa_admin.partner_id.id)],
                'channel_type': 'whatsapp',
                'name': 'Dummy WA Channel 2',
                'wa_account_id': cls.whatsapp_account.id,
                'whatsapp_number': '911234567891',
                'whatsapp_partner_id': cls.whatsapp_customer.id,
            }, {
                'channel_partner_ids': [(4, cls.user_wa_admin.partner_id.id)],
                'channel_type': 'channel',
                'name': 'Dummy Test Channel',
            }
        ])

    def test_gc_whatsapp_inactive(self):
        for test_record, delay_days, mark_read in ((self.test_channel_wa, 2, True), (self.test_channel_wa2, 6, False)):  # 2 days - 6 days
            with self.subTest(test_record=test_record):
                test_record.channel_pin(pinned=True)
                member_of_operator = self.env["discuss.channel.member"].search(
                    [
                        ("channel_id", "=", test_record.id),
                        ("partner_id", "=", self.user_wa_admin.partner_id.id),
                    ]
                )
                message = test_record.message_post(
                    author_id=self.whatsapp_customer.id,
                    body='TestBody',
                    message_type='whatsapp_message',
                    subtype_xmlid='mail.mt_comment',
                )
                if mark_read:
                    member_of_operator._mark_as_read(message.id)
                self.assertTrue(member_of_operator.is_pinned)
                with freeze_time(datetime.now() + timedelta(days=delay_days)):
                    member_of_operator._gc_unpin_whatsapp_channels()
                self.assertFalse(member_of_operator.is_pinned)

    @users('user_wa_admin')
    def test_post_with_outbound(self):
        """ Test automatic whatsapp message creation when posting on a whatsapp
        channel: should create an outbound wa message """
        test_channel_wa = self.test_channel_wa.with_env(self.env)
        with self.mockWhatsappGateway():
            new_msg = test_channel_wa.message_post(
                author_id=test_channel_wa.whatsapp_partner_id.id,
                body='TestBody',
                message_type='whatsapp_message',
                subtype_xmlid='mail.mt_comment',
            )
        wa_message = new_msg.wa_message_ids
        self.assertEqual(len(wa_message), 1)
        self.assertEqual(wa_message.message_type, 'outbound')
        self.assertEqual(wa_message.mobile_number, f'+{test_channel_wa.whatsapp_number}')
        self.assertTrue(wa_message.msg_uid)
        self.assertEqual(wa_message.state, 'sent')
        self.assertEqual(wa_message.wa_account_id, self.test_channel_wa.wa_account_id)

        # should not be supported on other channels / models
        for test_record in (self.whatsapp_customer, self.test_channel_std):
            with self.subTest(test_record=test_record), self.mockWhatsappGateway():
                new_msg = test_record.message_post(
                    author_id=test_channel_wa.whatsapp_partner_id.id,
                    body='TestBody',
                    message_type='whatsapp_message',
                    subtype_xmlid='mail.mt_comment',
                )
                self.assertFalse(new_msg.wa_message_ids)

    @users('user_wa_admin')
    def test_post_with_whatsapp_inbound_msg_uid(self):
        """ Test automatic whatsapp message creation when posting from whatsapp
        specific controller """
        test_channel_wa = self.test_channel_wa.with_env(self.env)
        new_msg = test_channel_wa.message_post(
            author_id=test_channel_wa.whatsapp_partner_id.id,
            body='TestBody',
            message_type='whatsapp_message',
            subtype_xmlid='mail.mt_comment',
            whatsapp_inbound_msg_uid='msg.uid.123456789',
        )
        wa_message = new_msg.wa_message_ids
        self.assertEqual(len(wa_message), 1)
        self.assertEqual(wa_message.message_type, 'inbound')
        self.assertEqual(wa_message.mobile_number, f'+{test_channel_wa.whatsapp_number}')
        self.assertEqual(wa_message.msg_uid, 'msg.uid.123456789')
        self.assertEqual(wa_message.state, 'received')
        self.assertEqual(wa_message.wa_account_id, self.test_channel_wa.wa_account_id)

        # should not be supported on other channels / models
        for test_record in (self.whatsapp_customer, self.test_channel_std):
            with self.subTest(test_record=test_record):
                with self.assertRaises(ValueError):
                    test_record.message_post(
                        author_id=test_channel_wa.whatsapp_partner_id.id,
                        body='TestBody',
                        message_type='whatsapp_message',
                        subtype_xmlid='mail.mt_comment',
                        whatsapp_inbound_msg_uid='msg.uid.123456789',
                    )

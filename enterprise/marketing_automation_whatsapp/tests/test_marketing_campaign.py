# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.whatsapp.tests.common import WhatsAppCommon, MockIncomingWhatsApp


class MarketingCampaign(WhatsAppCommon, MockIncomingWhatsApp):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.phone = '+32499123456'
        cls.tracked_url = 'https://www.tracked.com'
        cls.dynamic_url = 'https://www.dynamic.com'
        cls.template = cls.env['whatsapp.template'].create({
            'body': 'Hello {{1}}',
            'name': 'Test-dynamic',
            'status': 'approved',
            'wa_account_id': cls.whatsapp_account.id,
            'button_ids': [
                        (0, 0, {
                            'sequence': 0,
                            'button_type': 'url',
                            'name': 'tracked url',
                            'url_type': 'tracked',
                            'website_url': cls.tracked_url,
                        }),
                        (0, 0, {
                            'sequence': 1,
                            'button_type': 'url',
                            'name': 'dynamic url',
                            'url_type': 'dynamic',
                            'website_url': cls.dynamic_url,
                        })
                ],
            'variable_ids': [
                (0, 0, {'name': "{{1}}", 'line_type': "body", 'field_type': 'free_text', 'demo_value': cls.tracked_url}),
            ],
        })

        cls.whatsapp_test_customer = cls.env['res.partner'].create({
            'name': 'Wa Test Marketing Automation',
            'mobile': cls.phone
        })

        cls.campaign = cls.env['marketing.campaign'].create({
            'domain': [('mobile', '=', cls.phone), ('name', '=', 'Wa Test Marketing Automation')],
            'model_id': cls.env['ir.model']._get_id('res.partner'),
            'name': 'Test Campaign',
        })

        vals = {
            'name': 'Test Activity',
            'activity_type': 'whatsapp',
            'whatsapp_template_id': cls.template.id,
            'campaign_id': cls.campaign.id,
            'model_id': cls.env['ir.model']._get_id('res.partner')
        }
        cls.activity = cls.env['marketing.activity'].create(vals)
        cls.tracker_values = {'campaign_id': cls.campaign.utm_campaign_id.id, 'url': cls.tracked_url}

    def test_detect_responses(self):
        """ Test reply mechanism on whatsapp """
        self.campaign.sync_participants()

        # send message
        with self.mockWhatsappGateway():
            self.campaign.execute_activities()

        traces = self.env['marketing.trace'].search([
            ('activity_id', 'in', self.activity.ids),
        ])
        # recieve message
        with self.mockWhatsappGateway():
            self._receive_whatsapp_message(
                self.whatsapp_account, "Hello, it's reply", self.phone,
            )
        self.assertEqual(traces.whatsapp_message_id.state, 'replied')

    def test_get_template_button_component_tracking(self):
        button_component = self.template._get_template_button_component()
        button1_url = button_component['buttons'][0]['url']
        button1_example = button_component['buttons'][0]['example']
        host_url = self.env['link.tracker'].get_base_url().strip('/')

        self.assertEqual(button1_url, host_url + '/{{1}}')
        self.assertEqual(button1_example, host_url + '/???')

    def test_ma_tracked_button(self):
        self.campaign.sync_participants()

        # send message
        with self.mockWhatsappGateway():
            self.campaign.execute_activities()

        traces = self.env['marketing.trace'].search([
            ('activity_id', 'in', self.activity.ids),
        ])
        link_tracker = self.env['link.tracker'].search_or_create([self.tracker_values])
        wa_link_suffix = f'r/{link_tracker.code}/w/{traces.whatsapp_message_id.id}'

        btn_1 = [c for c in self._wa_msg_sent_vals[0]['components'] if c['type'] == 'button' and c['index'] == 0]
        btn_2 = [c for c in self._wa_msg_sent_vals[0]['components'] if c['type'] == 'button' and c['index'] == 1]
        self.assertEqual(btn_1[0]['parameters'][0]['text'], wa_link_suffix)
        self.assertEqual(btn_2[0]['parameters'][0]['text'], '???')

    def test_ma_tracked_variable(self):
        self.campaign.sync_participants()

        # send message
        with self.mockWhatsappGateway():
            self.campaign.execute_activities()

        traces = self.env['marketing.trace'].search([
            ('activity_id', 'in', self.activity.ids),
        ])
        self._wa_msg_sent_vals[0]['components'][0]
        tracked_variable = next((c for c in self._wa_msg_sent_vals[0]['components'] if c['type'] == 'body'), None)
        link_tracker = self.env['link.tracker'].search_or_create([self.tracker_values])

        wa_link_suffix = f'{link_tracker.short_url}/w/{traces.whatsapp_message_id.id}'
        self.assertEqual(tracked_variable['parameters'][0]['text'], wa_link_suffix)

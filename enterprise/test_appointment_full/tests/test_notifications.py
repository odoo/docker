from datetime import datetime
from freezegun import freeze_time
from unittest.mock import patch

from odoo.addons.appointment.tests.common import AppointmentCommon
from odoo.addons.google_calendar.models.res_users import User as GoogleUser
from odoo.addons.google_calendar.tests.test_sync_common import TestSyncGoogle
from odoo.addons.microsoft_calendar.models.res_users import User as MsftUser
from odoo.addons.microsoft_calendar.tests.common import TestCommon as MsftTestCommon
from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService


class TestAppointmentNotificationCommon(AppointmentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        attendee_ids = cls.env['res.partner'].create([
            {'name': f'p{n}', 'email': f'p{n}@test.lan'} for n in range(2)
        ])

        cls.calendar_event = cls.env['calendar.event'].create({
            'name': 'Test Notification Appointment',
            'appointment_type_id': cls.apt_type_bxls_2days.id,
            'start': datetime(2020, 2, 1, 10),
            'stop': datetime(2020, 2, 1, 11),
            'user_id': cls.apt_manager.id,
            'partner_ids': [(4, cls.apt_manager.partner_id.id)] + [(4, attendee.id) for attendee in attendee_ids],
        })


class TestAppointmentNotificationsMail(TestAppointmentNotificationCommon):
    @freeze_time('2020-02-01 09:00:00')
    def test_appointment_cancel_notification_mail(self):
        appointment = self.calendar_event
        self.env.flush_all()
        self.cr.precommit.run()
        with self.mock_mail_gateway():
            appointment.with_context(mail_notify_author=True).action_archive()
            self.env.flush_all()
            self.cr.precommit.run()
        self.assertMailMail(appointment.partner_id, 'sent', author=appointment.partner_id)
        self.assertMailMail(appointment.partner_ids - appointment.partner_id, 'sent', author=appointment.partner_id)


class TestSyncOdoo2GoogleMail(TestSyncGoogle, TestAppointmentNotificationCommon):
    @freeze_time('2020-02-01 09:00:00')
    @patch.object(GoogleUser, '_get_google_calendar_token', lambda user: 'some-token')
    def test_appointment_cancel_notification_gcalendar(self):
        self.env['res.users.settings'].create({'user_id': self.env.user.id})
        self.env.user.res_users_settings_id._set_google_auth_tokens('some-token', '123', 10000)
        appointment = self.calendar_event
        appointment.google_id = 'test_google_id'
        self.env.flush_all()
        self.cr.precommit.run()
        with self.mock_mail_gateway(mail_unlink_sent=False), self.mock_google_sync():
            appointment.action_archive()
            self.env.flush_all()
            self.cr.precommit.run()
        self.assertGoogleEventPatched('test_google_id', {'status': 'cancelled'}, timeout=3)
        self.assertNotSentEmail()


class TestAppointmentNotificationsMicrosoftCalendar(MsftTestCommon, TestAppointmentNotificationCommon):
    @freeze_time('2020-02-01 09:00:00')
    @patch.object(MsftUser, '_get_microsoft_calendar_token', lambda user: 'some-token')
    def test_appointment_cancel_notification_msftcalendar(self):
        appointment = self.calendar_event
        appointment.microsoft_id = 'test_msft_id'
        with self.mock_mail_gateway(), patch.object(MicrosoftCalendarService, 'delete') as mock_delete:
            appointment.action_archive()
            self.env.flush_all()
            self.cr.precommit.run()
            self.env.cr.postcommit.run()
        mock_delete.assert_called_once_with('test_msft_id', token='some-token', timeout=3)
        self.assertNotSentEmail()

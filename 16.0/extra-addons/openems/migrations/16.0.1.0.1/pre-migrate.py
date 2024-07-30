def migrate(cr, version):
    cr.execute("""
               SELECT device_id, user_id, time_to_wait, last_notification
               INTO openems_alerting_migrate
               FROM openems_device_user_role
               WHERE time_to_wait > 0;
               """)

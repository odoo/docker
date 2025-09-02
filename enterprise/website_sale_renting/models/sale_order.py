# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
from datetime import timedelta

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _is_cart_ready(self):
        """Whether the cart is valid and can be confirmed (and paid for)

        :rtype: bool
        """
        res = super()._is_cart_ready()
        return res and (not self.is_rental_order or self._available_dates_for_renting())

    def _check_cart_is_ready_to_be_paid(self):
        self.ensure_one()
        if not self._available_dates_for_renting():
            raise ValidationError(_(
                "Some of your rental products cannot be rented during the selected period and your"
                " cart must be updated. We're sorry for the inconvenience."
            ))
        return super()._check_cart_is_ready_to_be_paid()

    def _verify_updated_quantity(self, order_line, product_id, new_qty, **kwargs):
        new_qty, warning = super()._verify_updated_quantity(
            order_line, product_id, new_qty, **kwargs
        )
        product = self.env['product.product'].browse(product_id)
        if new_qty > 0 and product.rent_ok and not self._is_valid_renting_dates():
            self.shop_warning = self._build_warning_renting(product)
            return 0, self.shop_warning

        return new_qty, warning

    def convert_to_website_tz(self, value):
        """ Convert a given naive datetime into the website's timezone.

        The naive datetime value is assumed to be in UTC timezone (default database format).

        :param datetime value: The date to convert.
        :return: naive datetime expressed in the website timezone.
        :rtype: naive datetime
        """
        return pytz.utc.localize(value).astimezone(
            pytz.timezone(self.website_id.tz)
        ).replace(tzinfo=None)

    def _is_valid_renting_dates(self):
        """ Check if the pickup and return dates are valid.

        :return: Whether the pickup and return dates are valid.
        :rtype: bool
        """
        self.ensure_one()
        if not self.has_rented_products:
            return True
        days_forbidden = self.company_id._get_renting_forbidden_days()
        converted_rental_start_date = self.convert_to_website_tz(self.rental_start_date)
        converted_rental_return_date = self.convert_to_website_tz(self.rental_return_date)
        converted_current_datetime = self.convert_to_website_tz(fields.Datetime.now())
        return (
            # 15 minutes of allowed time between adding the product to cart and paying it.
            converted_rental_start_date >= converted_current_datetime - timedelta(minutes=15)
            and converted_rental_start_date.isoweekday() not in days_forbidden
            and converted_rental_return_date.isoweekday() not in days_forbidden
            and self._get_renting_duration() >= self.company_id.renting_minimal_time_duration
        )

    def _cart_update_order_line(self, *args, start_date=None, end_date=None, **kwargs):
        """Override to update rental order fields on the cart after line update."""
        has_rental_dates = self.rental_start_date and self.rental_return_date
        if not has_rental_dates and (start_date and end_date):
            self.write({
                'rental_start_date': start_date,
                'rental_return_date': end_date,
            })
            has_rental_dates = True
        # `in_rental_app` context makes sure rentable products added in cart becomes `is_rental`
        # cart lines
        self_ctx = self.with_context(in_rental_app=True)
        res = super(SaleOrder, self_ctx)._cart_update_order_line(*args, **kwargs)
        if self.is_rental_order and not self.has_rented_products:
            self.write({
                'is_rental_order': False,
                'rental_start_date': False,
                'rental_return_date': False,
            })
        return res

    def _build_warning_renting(self, product):
        """ Build the renting warning on SO to warn user a product cannot be rented on that period.

        Note: self.ensure_one()

        :param ProductProduct product: The product concerned by the warning
        """
        self.ensure_one()
        company = self.company_id
        days_forbidden = company._get_renting_forbidden_days()
        pickup_forbidden = self.rental_start_date.isoweekday() in days_forbidden
        return_forbidden = self.rental_return_date.isoweekday() in days_forbidden
        message = _("""
            Some of your rental products (%(product)s) cannot be rented during the
            selected period and your cart must be updated. We're sorry for the
            inconvenience.
        """, product=product.name)
        if self.rental_start_date < fields.Datetime.now():
            message += _("""Your rental product cannot be pickedup in the past.""")
        elif pickup_forbidden and return_forbidden:
            message += _("""
                Your rental product had invalid dates of pickup (%(start_date)s) and
                return (%(end_date)s). Unfortunately, we do not process pickups nor
                returns on those weekdays.
            """, start_date=self.rental_start_date, end_date=self.rental_return_date)
        elif pickup_forbidden:
            message += _("""
                Your rental product had invalid date of pickup (%(start_date)s).
                Unfortunately, we do not process pickups on that weekday.
            """, start_date=self.rental_start_date)
        elif return_forbidden:
            message += _("""
                Your rental product had invalid date of return (%(end_date)s).
                Unfortunately, we do not process returns on that weekday.
            """, end_date=self.rental_return_date)
        minimal_duration = company.renting_minimal_time_duration
        if self._get_renting_duration() < minimal_duration:
            message += _("""
                Your rental duration was too short. Unfortunately, we do not process
                rentals that last less than %(duration)s %(unit)s.
            """, duration=minimal_duration, unit=company.renting_minimal_time_unit)

        return message

    def _get_renting_duration(self):
        """ Return the renting rounded-up duration. """
        return self.env['product.pricing']._compute_duration_vals(
            self.rental_start_date, self.rental_return_date
        )[self.company_id.renting_minimal_time_unit]

    def _is_renting_possible_in_hours(self):
        """ Whether all products in the cart can be rented in a period computed in hours. """
        rental_order_lines = self.order_line.filtered('is_rental')
        return all('hour' in line.product_id.product_pricing_ids.mapped('recurrence_id.unit')
                   for line in rental_order_lines)

    def _cart_update_renting_period(self, start_date, end_date):
        self.ensure_one()
        current_start_date = self.rental_start_date
        current_end_date = self.rental_return_date
        self.write({
            'rental_start_date': start_date,
            'rental_return_date': end_date,
        })
        if not self._available_dates_for_renting():
            # shop_warning can be set by stock if invalid dates
            self.shop_warning = self.shop_warning or _("""
                The new period is not valid for some products of your cart.
                Your changes on the rental period are not taken into account.
            """)
            self.write({
                'rental_start_date': current_start_date,
                'rental_return_date': current_end_date,
            })
        else:
            rental_lines = self.order_line.filtered('is_rental')
            self.env.add_to_compute(rental_lines._fields['name'], rental_lines)
            self._recompute_rental_prices()
            rental_lines = self.order_line.filtered('is_rental')
            rental_lines._compute_name()

    def _available_dates_for_renting(self):
        """Hook to override with the stock availability"""
        return self._is_valid_renting_dates()

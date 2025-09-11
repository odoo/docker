# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError


class l10nChSicknessInsurance(models.Model):
    _name = 'l10n.ch.sickness.insurance'
    _description = 'Swiss: Sickness Insurances (IJM)'

    name = fields.Char(required=True)
    customer_number = fields.Char(required=True)
    contract_number = fields.Char(required=True)
    # https://www.swissdec.ch/fileadmin/user_upload/_Datenempfaenger/Empfaengerliste.pdf
    insurance_company = fields.Char(required=True)
    insurance_code = fields.Char(required=True)
    insurance_company_address_id = fields.Many2one('res.partner')
    line_ids = fields.One2many('l10n.ch.sickness.insurance.line', 'insurance_id')

    @api.depends('insurance_company')
    def _compute_insurance_code(self):
        for insurance in self:
            insurance.insurance_code = insurance.insurance_company


class l10nChSicknessInsuranceLine(models.Model):
    _name = 'l10n.ch.sickness.insurance.line'
    _description = 'Swiss: Sickness Insurances Line (IJM)'
    _rec_name = 'solution_name'

    insurance_id = fields.Many2one('l10n.ch.sickness.insurance')
    solution_name = fields.Char()
    solution_type = fields.Selection(selection=[
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C')], required=True)
    solution_number = fields.Selection(selection=[
        ('0', '0'),
        ('1', '1'),
        ('2', '2')], required=True)
    rate_ids = fields.One2many('l10n.ch.sickness.insurance.line.rate', 'line_id')

    def _get_threshold(self, target):
        if not self:
            return 0
        valid_rates = self.env['l10n.ch.sickness.insurance.line.rate']
        for rate in self.rate_ids:
            if rate.date_from <= target and (not rate.date_to or target <= rate.date_to):
                valid_rates += rate
        if valid_rates:
            return max(valid_rates.mapped('wage_to'))
        raise UserError(_('No IJM threshold found for date %s', target))

    def _get_rates(self, target, gender="male"):
        if not self:
            return 0, 0, 0, 0
        for rate in self.rate_ids:
            if rate.date_from <= target and (not rate.date_to or target <= rate.date_to):
                if gender == "male":
                    return rate.wage_from, rate.wage_to, rate.male_rate, int(rate.employer_part)
                if gender == "female":
                    return rate.wage_from, rate.wage_to, rate.female_rate, int(rate.employer_part)
                raise UserError(_('No found rate for gender %s', gender))
        raise UserError(_('No IJM rates found for date %s', target))


class l10nChSicknessInsuranceLineRate(models.Model):
    _name = 'l10n.ch.sickness.insurance.line.rate'
    _description = 'Swiss: Sickness Insurances Line Rate (IJM)'

    line_id = fields.Many2one('l10n.ch.sickness.insurance.line')
    date_from = fields.Date(string="From", required=True)
    date_to = fields.Date(string="To")
    wage_from = fields.Float(string="Wage From")
    wage_to = fields.Float(string="Wage To")
    male_rate = fields.Float(string="Male Rate (%)", digits='Payroll Rate')
    female_rate = fields.Float(string="Female Rate (%)", digits='Payroll Rate')
    employer_part = fields.Selection([
        ('0', '0 %'),
        ('50', '50 %'),
        ('100', '100 %'),
    ], default='50')

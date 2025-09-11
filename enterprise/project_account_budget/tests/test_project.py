# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import Command
from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestProject(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Plan',
        })

        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Project - AA',
            'code': 'AA-1234',
            'plan_id': cls.analytic_plan.id,
        })
        cls.project_goats.write({
            'account_id': cls.analytic_account.id,
        })

    def test_get_budget_items(self):
        if not self.project_pigs.account_id:
            self.assertEqual(self.project_pigs._get_budget_items(False), None, 'No budget should be return since no AA is set into the project.')
        self.assertTrue(self.env.user.has_group('analytic.group_analytic_accounting'))
        self.assertDictEqual(
            self.project_goats._get_budget_items(False),
            {
                'data': [],
                'total': {'allocated': 0, 'progress': 0, 'spent': 0},
                'can_add_budget': False,
            },
            'No budget has been created for this project.'
        )

        today = date.today()
        budget = self.env['budget.analytic'].create({
            'name': 'Project Goats Budget',
            'date_from': today.replace(day=1),
            'date_to': today + relativedelta(months=1, days=-1),
            'budget_line_ids': [Command.create({
                'account_id': self.analytic_account.id,
                'budget_amount': 500,
            })],
        })
        budget.action_budget_confirm()

        budget_items = self.project_goats._get_budget_items(False)
        del budget_items['data'][0]['name']  # remove the name because it is a lazy translation.
        del budget_items['data'][0]['id']
        self.assertDictEqual(budget_items, {
            'data': [
                {
                    'allocated': 500,
                    'budgets': [],
                    'progress': -1.0,
                    'spent': 0.0,
                },
            ],
            'total': {'allocated': 500.0, 'spent': 0.0, 'progress': -1.0},
            'can_add_budget': False,
        })

    def test_get_budget_items_with_action(self):
        today = date.today()
        budgets = self.env['budget.analytic']
        for budget_name, planned_amount in [
            ('Project Goats Budget', 500),
            ('Project Pigs Budget', 1000),
        ]:
            budget = self.env['budget.analytic'].create({
                'name': budget_name,
                'date_from': today.replace(day=1),
                'date_to': today + relativedelta(months=1, days=-1),
                'budget_line_ids': [
                    Command.create({
                        'account_id': self.analytic_account.id,
                        'budget_amount': planned_amount,
                    }),
                ],
            })
            budget.action_budget_confirm()
            budgets += budget

        self.env.user.groups_id += self.env.ref('account.group_account_user')
        self.assertTrue(self.env.user.has_group('analytic.group_analytic_accounting'))
        budget_items = self.project_goats.with_context({'allowed_company_ids': [self.env.company.id]})._get_budget_items(with_action=True)
        del budget_items['data'][0]['name']  # remove the name because it is a lazy translation.
        del budget_items['data'][0]['id']
        del budget_items['data'][1]['name']  # remove the name because it is a lazy translation.
        del budget_items['data'][1]['id']
        self.assertDictEqual(budget_items, {
            'data': [
                {
                    'allocated': 500.0,
                    'progress': -1.0,
                    'spent': 0.0,
                    'budgets': [],
                    'action': {
                        'name': 'action_view_budget_lines',
                        'type': 'object',
                        'domain': f'[["id", "in", {budgets[0].budget_line_ids.ids}]]',
                    }
                },
                {
                    'allocated': 1000.0,
                    'progress': -1.0,
                    'spent': 0.0,
                    'budgets': [],
                    'action': {
                        'name': 'action_view_budget_lines',
                        'type': 'object',
                        'domain': f'[["id", "in", {budgets[1].budget_line_ids.ids}]]',
                    }
                },
            ],
            'total': {'allocated': 1500.0, 'spent': 0.0, 'progress': -1.0},
            'form_view_id': self.env.ref('project_account_budget.view_budget_analytic_form_dialog').id,
            'can_add_budget': True,
            'company_id': self.env.company.id,
        })

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.fields import Datetime
from odoo.tests import new_test_user

from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.addons.project.models.project_task import CLOSED_STATES


class TestTaskGanttView(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_gantt_test_1, cls.user_gantt_test_2, cls.user_gantt_test_3 = (
            new_test_user(cls.env, login=f'ganttviewuser{i}', groups='project.group_project_user')
            for i in range(1, 4)
        )
        cls.project_gantt_test_1, cls.project_gantt_test_2 = cls.env['project.project'].create([{
            'name': 'Project Gantt View Test',
        }] * 2)
        cls.tasks = cls.env['project.task'].create([
            {
                'name': 'Test gantt 1',
                'project_id': cls.project_gantt_test_1.id,
                'user_ids': False,
            },
            {
                'name': 'Test gantt 2',
                'project_id': cls.project_gantt_test_1.id,
                'user_ids': False,
            },
        ])

    def test_empty_line_task_last_period(self):
        """ In the gantt view of the tasks of a project, there should be an empty
            line for a user if they have a task planned in the last or current
            period for that project, whether or not is open.
        """
        self.env['project.task'].with_context({'mail_create_nolog': True}).create([{
            'name': 'Proute',
            'user_ids': user,
            'project_id': self.project_gantt_test_1.id,
            'state': state,
            'planned_date_begin': planned_date,
            'date_deadline': planned_date,
        } for user, state, planned_date in [
            (self.user_gantt_test_1, '1_done', Datetime.to_datetime('2023-01-01')),
            (self.user_gantt_test_2, '01_in_progress', Datetime.to_datetime('2023-01-01')),
            (self.user_gantt_test_3, '1_done', Datetime.to_datetime('2023-02-15')),
        ]])

        domain = [
            ('project_id', '=', self.project_gantt_test_1.id),
            ('state', 'not in', list(CLOSED_STATES)),
        ]

        displayed_gantt_users = self.env['project.task'].with_context({
            'gantt_start_date': Datetime.to_datetime('2023-02-01'),
            'gantt_scale': 'month',
        })._group_expand_user_ids(None, domain)

        self.assertTrue(self.user_gantt_test_1 in displayed_gantt_users, 'There should be an empty line for test user 1')
        self.assertTrue(self.user_gantt_test_2 in displayed_gantt_users, 'There should be an empty line for test user 2')
        self.assertTrue(self.user_gantt_test_3 in displayed_gantt_users, 'There should be an empty line for test user 3')

    def test_empty_line_task_last_period_all_tasks(self):
        """ In the gantt view of the 'All Tasks' action, there should be an empty
            line for a user if they have a task planned in the last or current
            period for any project (private tasks are excluded), whether or not
            that task is open.
        """
        self.env['project.task'].with_context({'mail_create_nolog': True}).create([{
            'name': 'Proute',
            'user_ids': user,
            'project_id': project_id,
            'state': '1_done',
            'planned_date_begin': planned_date,
            'date_deadline': planned_date,
        } for project_id, user, planned_date in [
            (self.project_gantt_test_1.id, self.user_gantt_test_1, Datetime.to_datetime('2023-01-01')),
            (self.project_gantt_test_2.id, self.user_gantt_test_2, Datetime.to_datetime('2023-01-02')),
            (False, self.user_gantt_test_3, Datetime.to_datetime('2023-01-01'))
        ]])

        displayed_gantt_users = self.env['project.task'].with_context({
            'gantt_start_date': Datetime.to_datetime('2023-01-02'),
            'gantt_scale': 'day',
        })._group_expand_user_ids(None, [('state', 'not in', list(CLOSED_STATES))])

        self.assertTrue(self.user_gantt_test_1 in displayed_gantt_users, 'There should be an empty line for test user 1')
        self.assertTrue(self.user_gantt_test_2 in displayed_gantt_users, 'There should be an empty line for test user 2')
        self.assertFalse(self.user_gantt_test_3 in displayed_gantt_users, 'There should be no empty line for test user 3')

    @freeze_time('2020-01-12')
    def test_get_all_deadlines(self):
        self.project_pigs.write({'date_start': '2020-01-05', 'date': '2020-02-10'})
        self.project_goats.write({'date_start': '2019-01-01', 'date': '2020-01-15'})
        project_pigs_milestone_1, project_pigs_milestone_2, dummy, project_goats_milestone_1, dummy = self.env['project.milestone'].create([
            {'name': 'Milestone 1 (project pigs)', 'project_id': self.project_pigs.id, 'deadline': '2020-01-10'},
            {'name': 'Milestone 2 (project pigs)', 'project_id': self.project_pigs.id, 'deadline': '2020-01-30'},
            {'name': 'Milestone 3 (project pigs)', 'project_id': self.project_pigs.id, 'deadline': '2020-02-10'},
            {'name': 'Milestone 1 (project goats)', 'project_id': self.project_goats.id, 'deadline': '2020-01-15'},
            {'name': 'Milestone 2 (project goats)', 'project_id': self.project_goats.id, 'deadline': '2020-02-01'},
        ])
        results = self.env['project.task'].get_all_deadlines("2020-01-01", "2020-01-31")
        self.assertIsInstance(results, dict)
        self.assertIn('project_id', results)
        project_id_results = results['project_id']
        self.assertEqual(len(project_id_results), 2)
        project_pigs_result_expected = {
            'id': self.project_pigs.id,
            'name': self.project_pigs.name,
            'date': self.project_pigs.date,
            'date_start': self.project_pigs.date_start,
        }
        project_goats_result_expected = {
            'id': self.project_goats.id,
            'name': self.project_goats.name,
            'date': self.project_goats.date,
            'date_start': self.project_goats.date_start,
        }
        for project_result in project_id_results:
            self.assertIn('id', project_result)
            if project_result['id'] == self.project_pigs.id:
                self.assertDictEqual(project_result, project_pigs_result_expected)
            else:
                self.assertDictEqual(project_result, project_goats_result_expected)
        self.assertIn('milestone_id', results)
        milestone_id_results = results['milestone_id']
        self.assertEqual(len(milestone_id_results), 3)
        project_pigs_milestone_1_expected = {
            'id': project_pigs_milestone_1.id,
            'name': project_pigs_milestone_1.name,
            'deadline': project_pigs_milestone_1.deadline,
            'is_deadline_exceeded': True,
            'is_reached': False,
            'project_id': (self.project_pigs.id, self.project_pigs.name),
        }
        project_pigs_milestone_2_expected = {
            'id': project_pigs_milestone_2.id,
            'name': project_pigs_milestone_2.name,
            'deadline': project_pigs_milestone_2.deadline,
            'is_deadline_exceeded': False,
            'is_reached': False,
            'project_id': (self.project_pigs.id, self.project_pigs.name),
        }
        project_goats_milestone_1_expected = {
            'id': project_goats_milestone_1.id,
            'name': project_goats_milestone_1.name,
            'deadline': project_goats_milestone_1.deadline,
            'is_deadline_exceeded': False,
            'is_reached': False,
            'project_id': (self.project_goats.id, self.project_goats.name),
        }
        for milestone_result in milestone_id_results:
            if milestone_result['id'] == project_pigs_milestone_1.id:
                self.assertDictEqual(milestone_result, project_pigs_milestone_1_expected)
            elif milestone_result['id'] == project_pigs_milestone_2.id:
                self.assertDictEqual(milestone_result, project_pigs_milestone_2_expected)
            else:
                self.assertDictEqual(milestone_result, project_goats_milestone_1_expected)

        results = self.env['project.task'].with_context(default_project_id=self.project_pigs.id).get_all_deadlines("2020-01-01", "2020-01-31")
        self.assertIn('project_id', results)
        project_id_results = results['project_id']
        self.assertEqual(len(project_id_results), 1)
        self.assertDictEqual(project_id_results[0], project_pigs_result_expected)
        self.assertIn('milestone_id', results)
        milestone_id_results = results['milestone_id']
        self.assertEqual(len(milestone_id_results), 2)
        for milestone_result in milestone_id_results:
            if milestone_result['id'] == project_pigs_milestone_1.id:
                self.assertDictEqual(milestone_result, project_pigs_milestone_1_expected)
            else:
                self.assertDictEqual(milestone_result, project_pigs_milestone_2_expected)

    def test_plan_tasks_no_assignee_allocated_hours(self):
        self.tasks.write({
            'planned_date_begin': '2024-03-07 00:00:00',
            'date_deadline': '2024-03-08 23:59:59',
        })  # capacity of 16h
        self.assertEqual(self.tasks.mapped('allocated_hours'), [16.0, 16.0], 'The allocated hours should be 16.0 both')

    def test_capacity_split_allocated_hours(self):
        self.tasks.write({
            'user_ids': [self.project_gantt_test_1.user_id.id],
            'planned_date_begin': '2024-03-07 00:00:00',
            'date_deadline': '2024-03-08 23:59:59',
        })  # capacity of 16h, should be split in two (8h for both tasks)
        self.assertEqual(self.tasks.mapped('allocated_hours'), [8.0, 8.0], 'The allocated hours should be 8.0 both')

    def test_capacity_split_allocated_hours_substitute(self):
        self.tasks |= self.env['project.task'].create({
            'name': 'Test gantt',
            'project_id': self.project_gantt_test_1.id,
            'allocated_hours': 12.0,
        })
        self.tasks.write({
            'user_ids': [self.project_gantt_test_1.user_id.id],
            'planned_date_begin': '2024-03-07 00:00:00',
            'date_deadline': '2024-03-08 23:59:59',
        })  # capacity of 16h
        self.assertEqual(self.tasks.mapped('allocated_hours'), [2.0, 2.0, 12.0], 'The capacity should be 4h since a task with 12h allocated hours is in the recordset')

    def test_no_recompute_allocated_hours_present(self):
        self.tasks.write({
            'allocated_hours': 12.0,  # set allocated hours to 12
            'planned_date_begin': '2024-03-07 00:00:00',
            'date_deadline': '2024-03-08 23:59:59',
        })
        self.assertEqual(self.tasks.mapped('allocated_hours'), [12.0, 12.0], 'The tasks\'s allocated hours shouldn\'t have been recomputed since the allocated hours are being/already set')

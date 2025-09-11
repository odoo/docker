from freezegun import freeze_time

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale_commission.tests.test_sale_commission_common import TestSaleCommissionCommon


@tagged('post_install', '-at_install')
class TestSaleCommissionManager(TestSaleCommissionCommon):

    @freeze_time('2024-02-02')
    def test_commission_manager_achievement(self):
        self.commission_plan_manager.write({
            'periodicity': 'month',
            'type': 'achieve',
            'user_type': 'team',
        })
        self.commission_plan_manager.action_approve()
        (self.commission_user_1 + self.commission_user_2 + self.commission_manager).sale_team_id = self.team_commission

        self.commission_plan_manager.achievement_ids = self.env['sale.commission.plan.achievement'].create([{
            'type': 'amount_sold',
            'rate': 0.04,
            'plan_id': self.commission_plan_user.id,
        }, {
            'type': 'amount_invoiced',
            'rate': 0.06,
            'plan_id': self.commission_plan_user.id,
        }, {
            'type': 'amount_sold',
            'rate': 0.1,
            'product_id': self.commission_product_2.id,
            'plan_id': self.commission_plan_user.id,
        }])

        SO = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'user_id': self.commission_user_1.id,
            'order_line': [Command.create({
                'product_id': self.commission_product_1.id,
                'product_uom_qty': 10,
                'price_unit': 200,
            })],
            'team_id': self.commission_user_1.sale_team_id.id,
        })

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_manager.id)])
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_manager.id)])

        self.assertFalse(achievements, 'SO has not been confirmed yet, there should be no achievement.')
        self.assertEqual(len(commissions), 12, "SO has not been confirmed, we only have forecast")
        self.assertFalse(sum(commissions.mapped('target_amount')), 'SO has not been confirmed yet, there should be no commission.')

        SO.action_confirm()
        self.env.invalidate_all()

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_manager.id)])
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_manager.id)])

        self.assertEqual(len(achievements), 1, 'The one line should count as an achievement')
        self.assertEqual(achievements.user_id.id, self.commission_manager.id)
        self.assertEqual(sum(achievements.mapped('achieved')), 80, '0.04 * 2000 = 80')
        self.assertEqual(achievements.related_res_id, SO.id)
        self.assertEqual(sum(commissions.mapped('commission')), 80)

        AM = SO._create_invoices()
        self.env.invalidate_all()

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_manager.id)]).\
            filtered(lambda x: x.related_res_id == AM.id and x.related_res_model == 'account.move')
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_manager.id)])

        self.assertEqual(len(achievements), 1, 'There should be one new achievement')
        self.assertEqual(achievements.user_id.id, self.commission_manager.id)
        self.assertEqual(sum(achievements.mapped('achieved')), 120, '0.06 * 2000 = 120')
        self.assertEqual(len(commissions), 12)
        self.assertEqual(sum(commissions.mapped('commission')), 200)

        SO2 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'user_id': self.commission_user_2.id,
            'order_line': [Command.create({
                'product_id': self.commission_product_2.id,
                'product_uom_qty': 10,
                'price_unit': 200,
            })],
            'team_id': self.commission_user_1.sale_team_id.id,
        })
        SO2.action_confirm()
        self.env.invalidate_all()

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_manager.id)]).\
            filtered(lambda x: x.related_res_id == SO2.id and x.related_res_model == 'sale.order')
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_manager.id)])

        self.assertEqual(len(achievements), 1)
        self.assertEqual(achievements.user_id.id, self.commission_manager.id)
        self.assertEqual(sum(achievements.mapped('achieved')), 280, '0.04 * 2000 + 0.1 * 2000 = 280')
        self.assertEqual(len(commissions), 12)
        self.assertEqual(sum(commissions.mapped('commission')), 480, '200 + 280')

        AM2 = SO2._create_invoices()
        self.env.invalidate_all()

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_manager.id)]).\
            filtered(lambda x: x.related_res_id == AM2.id and x.related_res_model == 'account.move')
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_manager.id)])

        self.assertEqual(len(achievements), 1, 'There should be one new achievement')
        self.assertEqual(achievements.user_id.id, self.commission_manager.id)
        self.assertEqual(sum(achievements.mapped('achieved')), 120, '0.06 * 2000 = 120')
        self.assertEqual(len(commissions), 12)
        self.assertEqual(sum(commissions.mapped('commission')), 600)

    @freeze_time('2024-02-02')
    def test_commission_user_target(self):
        self.commission_plan_manager.write({
            'periodicity': 'month',
            'type': 'target',
            'user_type': 'team',
            'commission_amount': 2500,
        })
        (self.commission_user_1 + self.commission_user_2 + self.commission_manager).sale_team_id = self.team_commission

        self.commission_plan_manager.achievement_ids = self.env['sale.commission.plan.achievement'].create([{
            'type': 'amount_sold',
            'rate': 0.4,
            'plan_id': self.commission_plan_manager.id,
        }, {
            'type': 'amount_invoiced',
            'rate': 0.6,
            'plan_id': self.commission_plan_manager.id,
        }, {
            'type': 'amount_sold',
            'rate': 1,
            'product_id': self.commission_product_2.id,
            'plan_id': self.commission_plan_manager.id,
        }])

        self.commission_plan_manager.target_ids.amount = 2000

        # There is already a level 0 at 0$, level 0.5 at 0$ and level 1 at 2500$ by default
        self.commission_plan_manager.target_commission_ids += self.env['sale.commission.plan.target.commission'].create([{
            'target_rate': 2,
            'amount': 3500,
            'plan_id': self.commission_plan_manager.id,
        }, {
            'target_rate': 3,
            'amount': 4000,
            'plan_id': self.commission_plan_manager.id,
        }])
        self.commission_plan_manager.action_approve()

        SO = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'user_id': self.commission_user_1.id,
            'order_line': [Command.create({
                'product_id': self.commission_product_1.id,
                'product_uom_qty': 10,
                'price_unit': 200,
            })],
            'team_id': self.commission_user_1.sale_team_id.id,
        })

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_manager.id)])
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_manager.id)])

        self.assertFalse(achievements, 'SO has not been confirmed yet, there should be no achievement.')
        self.assertEqual(len(commissions), 12, 'SO has not been confirmed yet, there should be no commission but we have forecast.')

        SO.action_confirm()
        self.env.invalidate_all()

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_manager.id)])
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_manager.id)])

        self.assertEqual(len(achievements), 1, 'The one line should count as an achievement')
        self.assertEqual(sum(achievements.mapped('achieved')), 800, '0.4 * 2000 = 800')
        self.assertEqual(len(commissions), 12)
        self.assertEqual(sum(commissions.mapped('achieved')), 800)
        self.assertEqual(sum(commissions.mapped('commission')), 0, 'Achieved Rate(0.4) < 0.5')

        AM = SO._create_invoices()
        self.env.invalidate_all()

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_manager.id)]).\
            filtered(lambda x: x.related_res_id == AM.id and x.related_res_model == 'account.move')
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_manager.id)])

        self.assertEqual(len(achievements), 1, 'There should be one new achievement')
        self.assertEqual(sum(achievements.mapped('achieved')), 1200, '0.06 * 2000 = 120')
        self.assertEqual(len(commissions), 12)
        self.assertEqual(sum(commissions.mapped('achieved')), 2000)
        self.assertEqual(sum(commissions.mapped('commission')), 2500, 'We reached the 1st level Tier 1 Achieved Rate(1) * 2500')

        SO2 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'user_id': self.commission_user_1.id,
            'order_line': [Command.create({
                'product_id': self.commission_product_2.id,
                'product_uom_qty': 10,
                'price_unit': 200,
            })],
            'team_id': self.commission_user_1.sale_team_id.id,
        })
        SO2.action_confirm()
        self.env.invalidate_all()

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_manager.id)]).\
            filtered(lambda x: x.related_res_id == SO2.id and x.related_res_model == 'sale.order')
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_manager.id)])

        self.assertEqual(len(achievements), 1)
        self.assertEqual(sum(achievements.mapped('achieved')), 2800, '0.4 * 2000 + 1 * 2000 = 4800')
        self.assertEqual(len(commissions), 12)
        self.assertEqual(sum(commissions.mapped('achieved')), 4800)
        self.assertEqual(sum(commissions.mapped('commission')), 3700, 'We have reached the 2nd level,'
                                                       'Achieved Rate = 2.4'
                                                       'Amount = 3500 (AR = 2) + 200 (AR-2 * 500)')
        AM2 = SO2._create_invoices()
        self.env.invalidate_all()

        achievements = self.env['sale.commission.achievement.report'].search([('plan_id', '=', self.commission_plan_manager.id)]).\
            filtered(lambda x: x.related_res_id == AM2.id and x.related_res_model == 'account.move')
        commissions = self.env['sale.commission.report'].search([('plan_id', '=', self.commission_plan_manager.id)])

        self.assertEqual(len(achievements), 1, 'There should be one new achievement')
        self.assertEqual(sum(achievements.mapped('achieved')), 1200, '0.6 * 2000 = 1200')
        self.assertEqual(len(commissions), 12)
        self.assertEqual(sum(commissions.mapped('achieved')), 6000)
        self.assertEqual(sum(commissions.mapped('commission')), 4000, 'We have reached the 3rd level')

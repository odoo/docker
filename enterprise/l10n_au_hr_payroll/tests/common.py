# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta
from itertools import zip_longest as izip_longest

from odoo import Command
from odoo.tests.common import TransactionCase

import logging

_logger = logging.getLogger(__name__)


class TestPayrollCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestPayrollCommon, cls).setUpClass()

        today = date.today()
        cls.australian_company = cls.env["res.company"].create({
            "name": "Australian Company ( test )",
            "country_id": cls.env.ref("base.au").id,
            "currency_id": cls.env.ref("base.AUD").id,
            "resource_calendar_id": cls.env.ref("l10n_au_hr_payroll.resource_calendar_au_38").id,
            "l10n_au_registered_for_whm": True,
            "l10n_au_registered_for_palm": True,
        })
        cls.env.user.company_ids |= cls.australian_company
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.australian_company.ids))
        cls.resource_calendar = cls.env.ref("l10n_au_hr_payroll.resource_calendar_au_38")
        cls.resource_calendar.company_id = cls.australian_company

        cls.employee_id = cls.env["hr.employee"].create({
            "name": "Mel",
            "resource_calendar_id": cls.resource_calendar.id,
            "company_id": cls.australian_company.id,
            "private_street": "1 Test Street",
            "private_city": "Sydney",
            "private_country_id": cls.env.ref("base.au").id,
            "work_phone": "123456789",
            "birthday": today - relativedelta(years=22),
            # fields modified in the tests
            "marital": "single",
            "l10n_au_tfn_declaration": "provided",
            "l10n_au_tfn": "12345678",
            "l10n_au_tax_free_threshold": True,
            "is_non_resident": False,
            "l10n_au_training_loan": False,
            "l10n_au_nat_3093_amount": 0,
            "l10n_au_child_support_garnishee_amount": 0,
            "l10n_au_medicare_exemption": "X",
            "l10n_au_medicare_surcharge": "X",
            "l10n_au_medicare_reduction": "X",
            "l10n_au_child_support_deduction": 0,
            "l10n_au_withholding_variation": 'none',
            "l10n_au_withholding_variation_amount": 0,
        })

        first_contract_id = cls.env["hr.contract"].create({
            "name": "Mel's contract",
            "employee_id": cls.employee_id.id,
            "resource_calendar_id": cls.resource_calendar.id,
            "company_id": cls.australian_company.id,
            "date_start": date(2023, 1, 1),
            "date_end": False,
            "wage_type": "monthly",
            "wage": 5000.0,
            "l10n_au_casual_loading": 0.0,
            "structure_type_id": cls.env.ref("l10n_au_hr_payroll.structure_type_schedule_1").id,
            # fields modified in the tests
            "schedule_pay": "monthly",
            "l10n_au_workplace_giving": 0,
        })

        cls.contract_ids = first_contract_id
        cls.contract_ids.write({"state": "open"})

        cls.schedule_1_withholding_sample_data = {
            # earnings, schedule 1, schedule 2, schedule 3, schedule 5, schedule 6
            "weekly": [
                (87, 17.00, 0.00, 28.00, 0.00, 0.00),
                (88, 17.00, 0.00, 29.00, 0.00, 0.00),
                (116, 24.00, 0.00, 38.00, 0.00, 0.00),
                (117, 24.00, 0.00, 38.00, 0.00, 0.00),
                (249, 55.00, 0.00, 81.00, 0.00, 0.00),
                (250, 55.00, 0.00, 81.00, 0.00, 0.00),
                (358, 80.00, 0.00, 116.00, 0.00, 0.00),
                (359, 81.00, 0.00, 117.00, 0.00, 0.00),
                (370, 83.00, 2.00, 120.00, 2.00, 2.00),
                (371, 83.00, 2.00, 121.00, 2.00, 2.00),
                (437, 98.00, 15.00, 142.00, 15.00, 15.00),
                (438, 98.00, 15.00, 142.00, 15.00, 15.00),
                (514, 115.00, 37.00, 167.00, 30.00, 30.00),
                (515, 115.00, 37.00, 167.00, 30.00, 30.00),
                (547, 126.00, 47.00, 178.00, 36.00, 36.00),
                (548, 126.00, 47.00, 178.00, 36.00, 36.00),
                (720, 186.00, 83.00, 234.00, 69.00, 69.00),
                (721, 187.00, 83.00, 234.00, 69.00, 69.00),
                (738, 193.00, 87.00, 240.00, 72.00, 72.00),
                (739, 193.00, 87.00, 240.00, 72.00, 72.00),
                (864, 236.00, 115.00, 281.00, 97.00, 104.00),
                (865, 237.00, 115.00, 281.00, 98.00, 104.00),
                (923, 257.00, 135.00, 300.00, 117.00, 126.00),
                (924, 257.00, 135.00, 300.00, 117.00, 126.00),
                (931, 260.00, 138.00, 303.00, 119.00, 129.00),
                (932, 260.00, 138.00, 303.00, 120.00, 129.00),
                (1281, 380.00, 260.00, 416.00, 234.00, 247.00),
                (1282, 381.00, 260.00, 417.00, 234.00, 247.00),
                (1844, 575.00, 454.00, 599.00, 417.00, 435.00),
                (1845, 575.00, 454.00, 600.00, 417.00, 436.00),
                (1956, 613.00, 492.00, 636.00, 453.00, 473.00),
                (1957, 614.00, 493.00, 636.00, 454.00, 473.00),
                (2119, 677.00, 549.00, 689.00, 506.00, 527.00),
                (2120, 677.00, 549.00, 689.00, 507.00, 528.00),
                (2306, 750.00, 613.00, 749.00, 567.00, 590.00),
                (2307, 750.00, 614.00, 750.00, 567.00, 590.00),
                (2490, 821.00, 685.00, 818.00, 635.00, 660.00),
                (2491, 822.00, 685.00, 818.00, 635.00, 660.00),
                (2652, 885.00, 748.00, 878.00, 695.00, 722.00),
                (2653, 885.00, 748.00, 878.00, 695.00, 722.00),
                (2736, 917.00, 781.00, 909.00, 726.00, 753.00),
                (2737, 918.00, 781.00, 909.00, 726.00, 754.00),
                (2898, 981.00, 844.00, 969.00, 786.00, 815.00),
                (2899, 981.00, 844.00, 969.00, 786.00, 815.00),
                (2913, 986.00, 850.00, 974.00, 792.00, 821.00),
                (2914, 987.00, 850.00, 975.00, 792.00, 821.00),
                (3111, 1064.00, 927.00, 1048.00, 865.00, 896.00),
                (3461, 1228.00, 1064.00, 1177.00, 994.00, 1029.00),
            ],
            "bi-weekly": [
                (174, 34.00, 0.00, 56.00, 0.00, 0.00),
                (176, 34.00, 0.00, 58.00, 0.00, 0.00),
                (232, 48.00, 0.00, 76.00, 0.00, 0.00),
                (234, 48.00, 0.00, 76.00, 0.00, 0.00),
                (498, 110.00, 0.00, 162.00, 0.00, 0.00),
                (500, 110.00, 0.00, 162.00, 0.00, 0.00),
                (716, 160.00, 0.00, 232.00, 0.00, 0.00),
                (718, 162.00, 0.00, 234.00, 0.00, 0.00),
                (740, 166.00, 4.00, 240.00, 4.00, 4.00),
                (742, 166.00, 4.00, 242.00, 4.00, 4.00),
                (874, 196.00, 30.00, 284.00, 30.00, 30.00),
                (876, 196.00, 30.00, 284.00, 30.00, 30.00),
                (1028, 230.00, 74.00, 334.00, 60.00, 60.00),
                (1030, 230.00, 74.00, 334.00, 60.00, 60.00),
                (1094, 252.00, 94.00, 356.00, 72.00, 72.00),
                (1096, 252.00, 94.00, 356.00, 72.00, 72.00),
                (1440, 372.00, 166.00, 468.00, 138.00, 138.00),
                (1442, 374.00, 166.00, 468.00, 138.00, 138.00),
                (1476, 386.00, 174.00, 480.00, 144.00, 144.00),
                (1478, 386.00, 174.00, 480.00, 144.00, 144.00),
                (1728, 472.00, 230.00, 562.00, 194.00, 208.00),
                (1730, 474.00, 230.00, 562.00, 196.00, 208.00),
                (1846, 514.00, 270.00, 600.00, 234.00, 252.00),
                (1848, 514.00, 270.00, 600.00, 234.00, 252.00),
                (1862, 520.00, 276.00, 606.00, 238.00, 258.00),
                (1864, 520.00, 276.00, 606.00, 240.00, 258.00),
                (2562, 760.00, 520.00, 832.00, 468.00, 494.00),
                (2564, 762.00, 520.00, 834.00, 468.00, 494.00),
                (3688, 1150.00, 908.00, 1198.00, 834.00, 870.00),
                (3690, 1150.00, 908.00, 1200.00, 834.00, 872.00),
                (3912, 1226.00, 984.00, 1272.00, 906.00, 946.00),
                (3914, 1228.00, 986.00, 1272.00, 908.00, 946.00),
                (4238, 1354.00, 1098.00, 1378.00, 1012.00, 1054.00),
                (4240, 1354.00, 1098.00, 1378.00, 1014.00, 1056.00),
                (4612, 1500.00, 1226.00, 1498.00, 1134.00, 1180.00),
                (4614, 1500.00, 1228.00, 1500.00, 1134.00, 1180.00),
                (4980, 1642.00, 1370.00, 1636.00, 1270.00, 1320.00),
                (4982, 1644.00, 1370.00, 1636.00, 1270.00, 1320.00),
                (5304, 1770.00, 1496.00, 1756.00, 1390.00, 1444.00),
                (5306, 1770.00, 1496.00, 1756.00, 1390.00, 1444.00),
                (5472, 1834.00, 1562.00, 1818.00, 1452.00, 1506.00),
                (5474, 1836.00, 1562.00, 1818.00, 1452.00, 1508.00),
                (5796, 1962.00, 1688.00, 1938.00, 1572.00, 1630.00),
                (5798, 1962.00, 1688.00, 1938.00, 1572.00, 1630.00),
                (5826, 1972.00, 1700.00, 1948.00, 1584.00, 1642.00),
                (5828, 1974.00, 1700.00, 1950.00, 1584.00, 1642.00),
                (6222, 2128.00, 1854.00, 2096.00, 1730.00, 1792.00),
                (6922, 2456.00, 2128.00, 2354.00, 1988.00, 2058.00),
            ],
            "monthly": [
                (377.00, 74.00, 0.00, 121.00, 0.00, 0.00),
                (381.33, 74.00, 0.00, 126.00, 0.00, 0.00),
                (502.67, 104.00, 0.00, 165.00, 0.00, 0.00),
                (507.00, 104.00, 0.00, 165.00, 0.00, 0.00),
                (1079.00, 238.00, 0.00, 351.00, 0.00, 0.00),
                (1083.33, 238.00, 0.00, 351.00, 0.00, 0.00),
                (1551.33, 347.00, 0.00, 503.00, 0.00, 0.00),
                (1555.67, 351.00, 0.00, 507.00, 0.00, 0.00),
                (1603.33, 360.00, 9.00, 520.00, 9.00, 9.00),
                (1607.67, 360.00, 9.00, 524.00, 9.00, 9.00),
                (1893.67, 425.00, 65.00, 615.00, 65.00, 65.00),
                (1898.00, 425.00, 65.00, 615.00, 65.00, 65.00),
                (2227.33, 498.00, 160.00, 724.00, 130.00, 130.00),
                (2231.67, 498.00, 160.00, 724.00, 130.00, 130.00),
                (2370.33, 546.00, 204.00, 771.00, 156.00, 156.00),
                (2374.67, 546.00, 204.00, 771.00, 156.00, 156.00),
                (3120.00, 806.00, 360.00, 1014.00, 299.00, 299.00),
                (3124.33, 810.00, 360.00, 1014.00, 299.00, 299.00),
                (3198.00, 836.00, 377.00, 1040.00, 312.00, 312.00),
                (3202.33, 836.00, 377.00, 1040.00, 312.00, 312.00),
                (3744.00, 1023.00, 498.00, 1218.00, 420.00, 451.00),
                (3748.33, 1027.00, 498.00, 1218.00, 425.00, 451.00),
                (3999.67, 1114.00, 585.00, 1300.00, 507.00, 546.00),
                (4004.00, 1114.00, 585.00, 1300.00, 507.00, 546.00),
                (4034.33, 1127.00, 598.00, 1313.00, 516.00, 559.00),
                (4038.67, 1127.00, 598.00, 1313.00, 520.00, 559.00),
                (5551.00, 1647.00, 1127.00, 1803.00, 1014.00, 1070.00),
                (5555.33, 1651.00, 1127.00, 1807.00, 1014.00, 1070.00),
                (7990.67, 2492.00, 1967.00, 2596.00, 1807.00, 1885.00),
                (7995.00, 2492.00, 1967.00, 2600.00, 1807.00, 1889.00),
                (8476.00, 2656.00, 2132.00, 2756.00, 1963.00, 2050.00),
                (8480.33, 2661.00, 2136.00, 2756.00, 1967.00, 2050.00),
                (9182.33, 2934.00, 2379.00, 2986.00, 2193.00, 2284.00),
                (9186.67, 2934.00, 2379.00, 2986.00, 2197.00, 2288.00),
                (9992.67, 3250.00, 2656.00, 3246.00, 2457.00, 2557.00),
                (9997.00, 3250.00, 2661.00, 3250.00, 2457.00, 2557.00),
                (10790.00, 3558.00, 2968.00, 3545.00, 2752.00, 2860.00),
                (10794.33, 3562.00, 2968.00, 3545.00, 2752.00, 2860.00),
                (11492.00, 3835.00, 3241.00, 3805.00, 3012.00, 3129.00),
                (11496.33, 3835.00, 3241.00, 3805.00, 3012.00, 3129.00),
                (11856.00, 3974.00, 3384.00, 3939.00, 3146.00, 3263.00),
                (11860.33, 3978.00, 3384.00, 3939.00, 3146.00, 3267.00),
                (12558.00, 4251.00, 3657.00, 4199.00, 3406.00, 3532.00),
                (12562.33, 4251.00, 3657.00, 4199.00, 3406.00, 3532.00),
                (12623.00, 4273.00, 3683.00, 4221.00, 3432.00, 3558.00),
                (12627.33, 4277.00, 3683.00, 4225.00, 3432.00, 3558.00),
                (13481.00, 4611.00, 4017.00, 4541.00, 3748.00, 3883.00),
                (14997.67, 5321.00, 4611.00, 5100.00, 4307.00, 4459.00),
            ],
        }

        cls.medicare_adjustment_sample_data = {
            # earnings, spouse only, 1 child, 2 children, 3 children, 4 children, 5 children
            "weekly": [
                (492, 5.00, 5.00, 5.00, 5.00, 5.00, 5.00),
                (493, 6.00, 6.00, 6.00, 6.00, 6.00, 6.00),
                (547, 11.00, 11.00, 11.00, 11.00, 11.00, 11.00),
                (548, 11.00, 11.00, 11.00, 11.00, 11.00, 11.00),
                (575, 12.00, 12.00, 12.00, 12.00, 12.00, 12.00),
                (576, 12.00, 12.00, 12.00, 12.00, 12.00, 12.00),
                (603, 12.00, 12.00, 12.00, 12.00, 12.00, 12.00),
                (604, 12.00, 12.00, 12.00, 12.00, 12.00, 12.00),
                (631, 13.00, 13.00, 13.00, 13.00, 13.00, 13.00),
                (632, 13.00, 13.00, 13.00, 13.00, 13.00, 13.00),
                (659, 13.00, 13.00, 13.00, 13.00, 13.00, 13.00),
                (660, 13.00, 13.00, 13.00, 13.00, 13.00, 13.00),
                (687, 14.00, 14.00, 14.00, 14.00, 14.00, 14.00),
                (688, 14.00, 14.00, 14.00, 14.00, 14.00, 14.00),
                (715, 14.00, 14.00, 14.00, 14.00, 14.00, 14.00),
                (716, 14.00, 14.00, 14.00, 14.00, 14.00, 14.00),
                (743, 14.00, 15.00, 15.00, 15.00, 15.00, 15.00),
                (744, 14.00, 15.00, 15.00, 15.00, 15.00, 15.00),
                (771, 12.00, 15.00, 15.00, 15.00, 15.00, 15.00),
                (772, 12.00, 15.00, 15.00, 15.00, 15.00, 15.00),
                (799, 10.00, 16.00, 16.00, 16.00, 16.00, 16.00),
                (800, 10.00, 16.00, 16.00, 16.00, 16.00, 16.00),
                (827, 8.00, 15.00, 17.00, 17.00, 17.00, 17.00),
                (828, 8.00, 14.00, 17.00, 17.00, 17.00, 17.00),
                (855, 6.00, 12.00, 17.00, 17.00, 17.00, 17.00),
                (856, 5.00, 12.00, 17.00, 17.00, 17.00, 17.00),
                (883, 3.00, 10.00, 17.00, 18.00, 18.00, 18.00),
                (884, 3.00, 10.00, 17.00, 18.00, 18.00, 18.00),
                (911, 1.00, 8.00, 15.00, 18.00, 18.00, 18.00),
                (912, 1.00, 8.00, 15.00, 18.00, 18.00, 18.00),
                (939, 0.00, 6.00, 12.00, 19.00, 19.00, 19.00),
                (940, 0.00, 6.00, 12.00, 19.00, 19.00, 19.00),
                (967, 0.00, 3.00, 10.00, 17.00, 19.00, 19.00),
                (968, 0.00, 3.00, 10.00, 17.00, 19.00, 19.00),
                (995, 0.00, 1.00, 8.00, 15.00, 20.00, 20.00),
                (996, 0.00, 1.00, 8.00, 15.00, 20.00, 20.00),
                (1023, 0.00, 0.00, 6.00, 12.00, 19.00, 20.00),
                (1024, 0.00, 0.00, 6.00, 12.00, 19.00, 20.00),
                (1051, 0.00, 0.00, 3.00, 10.00, 17.00, 21.00),
                (1052, 0.00, 0.00, 3.00, 10.00, 17.00, 21.00),
                (1079, 0.00, 0.00, 1.00, 8.00, 15.00, 22.00),
                (1080, 0.00, 0.00, 1.00, 8.00, 15.00, 21.00),
                (1263, 0.00, 0.00, 0.00, 0.00, 0.00, 7.00),
                (1264, 0.00, 0.00, 0.00, 0.00, 0.00, 7.00),
                (1348, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00),
                (1349, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00),
            ],
            "bi-weekly": [
                (874, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00),
                (876, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00),
                (984, 10.00, 10.00, 10.00, 10.00, 10.00, 10.00),
                (986, 12.00, 12.00, 12.00, 12.00, 12.00, 12.00),
                (1094, 22.00, 22.00, 22.00, 22.00, 22.00, 22.00),
                (1096, 22.00, 22.00, 22.00, 22.00, 22.00, 22.00),
                (1150, 24.00, 24.00, 24.00, 24.00, 24.00, 24.00),
                (1152, 24.00, 24.00, 24.00, 24.00, 24.00, 24.00),
                (1206, 24.00, 24.00, 24.00, 24.00, 24.00, 24.00),
                (1208, 24.00, 24.00, 24.00, 24.00, 24.00, 24.00),
                (1262, 26.00, 26.00, 26.00, 26.00, 26.00, 26.00),
                (1264, 26.00, 26.00, 26.00, 26.00, 26.00, 26.00),
                (1318, 26.00, 26.00, 26.00, 26.00, 26.00, 26.00),
                (1320, 26.00, 26.00, 26.00, 26.00, 26.00, 26.00),
                (1374, 28.00, 28.00, 28.00, 28.00, 28.00, 28.00),
                (1376, 28.00, 28.00, 28.00, 28.00, 28.00, 28.00),
                (1430, 28.00, 28.00, 28.00, 28.00, 28.00, 28.00),
                (1432, 28.00, 28.00, 28.00, 28.00, 28.00, 28.00),
                (1486, 28.00, 30.00, 30.00, 30.00, 30.00, 30.00),
                (1488, 28.00, 30.00, 30.00, 30.00, 30.00, 30.00),
                (1542, 24.00, 30.00, 30.00, 30.00, 30.00, 30.00),
                (1544, 24.00, 30.00, 30.00, 30.00, 30.00, 30.00),
                (1598, 20.00, 32.00, 32.00, 32.00, 32.00, 32.00),
                (1600, 20.00, 32.00, 32.00, 32.00, 32.00, 32.00),
                (1654, 16.00, 30.00, 34.00, 34.00, 34.00, 34.00),
                (1656, 16.00, 28.00, 34.00, 34.00, 34.00, 34.00),
                (1710, 12.00, 24.00, 34.00, 34.00, 34.00, 34.00),
                (1712, 10.00, 24.00, 34.00, 34.00, 34.00, 34.00),
                (1766, 6.00, 20.00, 34.00, 36.00, 36.00, 36.00),
                (1768, 6.00, 20.00, 34.00, 36.00, 36.00, 36.00),
                (1822, 2.00, 16.00, 30.00, 36.00, 36.00, 36.00),
                (1824, 2.00, 16.00, 30.00, 36.00, 36.00, 36.00),
                (1878, 0.00, 12.00, 24.00, 38.00, 38.00, 38.00),
                (1880, 0.00, 12.00, 24.00, 38.00, 38.00, 38.00),
                (1934, 0.00, 6.00, 20.00, 34.00, 38.00, 38.00),
                (1936, 0.00, 6.00, 20.00, 34.00, 38.00, 38.00),
                (1990, 0.00, 2.00, 16.00, 30.00, 40.00, 40.00),
                (1992, 0.00, 2.00, 16.00, 30.00, 40.00, 40.00),
                (2046, 0.00, 0.00, 12.00, 24.00, 38.00, 40.00),
                (2048, 0.00, 0.00, 12.00, 24.00, 38.00, 40.00),
                (2102, 0.00, 0.00, 6.00, 20.00, 34.00, 42.00),
                (2104, 0.00, 0.00, 6.00, 20.00, 34.00, 42.00),
                (2158, 0.00, 0.00, 2.00, 16.00, 30.00, 44.00),
                (2160, 0.00, 0.00, 2.00, 16.00, 30.00, 42.00),
                (2526, 0.00, 0.00, 0.00, 0.00, 0.00, 14.00),
                (2528, 0.00, 0.00, 0.00, 0.00, 0.00, 14.00),
                (2696, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00),
                (2698, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00),
            ],
            "monthly": [
                (1893.67, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00),
                (1898.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00),
                (2132.00, 22.00, 22.00, 22.00, 22.00, 22.00, 22.00),
                (2136.33, 26.00, 26.00, 26.00, 26.00, 26.00, 26.00),
                (2370.33, 48.00, 48.00, 48.00, 48.00, 48.00, 48.00),
                (2374.67, 48.00, 48.00, 48.00, 48.00, 48.00, 48.00),
                (2491.67, 52.00, 52.00, 52.00, 52.00, 52.00, 52.00),
                (2496.00, 52.00, 52.00, 52.00, 52.00, 52.00, 52.00),
                (2613.00, 52.00, 52.00, 52.00, 52.00, 52.00, 52.00),
                (2617.33, 52.00, 52.00, 52.00, 52.00, 52.00, 52.00),
                (2734.33, 56.00, 56.00, 56.00, 56.00, 56.00, 56.00),
                (2738.67, 56.00, 56.00, 56.00, 56.00, 56.00, 56.00),
                (2855.67, 56.00, 56.00, 56.00, 56.00, 56.00, 56.00),
                (2860.00, 56.00, 56.00, 56.00, 56.00, 56.00, 56.00),
                (2977.00, 61.00, 61.00, 61.00, 61.00, 61.00, 61.00),
                (2981.33, 61.00, 61.00, 61.00, 61.00, 61.00, 61.00),
                (3098.33, 61.00, 61.00, 61.00, 61.00, 61.00, 61.00),
                (3102.67, 61.00, 61.00, 61.00, 61.00, 61.00, 61.00),
                (3219.67, 61.00, 65.00, 65.00, 65.00, 65.00, 65.00),
                (3224.00, 61.00, 65.00, 65.00, 65.00, 65.00, 65.00),
                (3341.00, 52.00, 65.00, 65.00, 65.00, 65.00, 65.00),
                (3345.33, 52.00, 65.00, 65.00, 65.00, 65.00, 65.00),
                (3462.33, 43.00, 69.00, 69.00, 69.00, 69.00, 69.00),
                (3466.67, 43.00, 69.00, 69.00, 69.00, 69.00, 69.00),
                (3583.67, 35.00, 65.00, 74.00, 74.00, 74.00, 74.00),
                (3588.00, 35.00, 61.00, 74.00, 74.00, 74.00, 74.00),
                (3705.00, 26.00, 52.00, 74.00, 74.00, 74.00, 74.00),
                (3709.33, 22.00, 52.00, 74.00, 74.00, 74.00, 74.00),
                (3826.33, 13.00, 43.00, 74.00, 78.00, 78.00, 78.00),
                (3830.67, 13.00, 43.00, 74.00, 78.00, 78.00, 78.00),
                (3947.67, 4.00, 35.00, 65.00, 78.00, 78.00, 78.00),
                (3952.00, 4.00, 35.00, 65.00, 78.00, 78.00, 78.00),
                (4069.00, 0.00, 26.00, 52.00, 82.00, 82.00, 82.00),
                (4073.33, 0.00, 26.00, 52.00, 82.00, 82.00, 82.00),
                (4190.33, 0.00, 13.00, 43.00, 74.00, 82.00, 82.00),
                (4194.67, 0.00, 13.00, 43.00, 74.00, 82.00, 82.00),
                (4311.67, 0.00, 4.00, 35.00, 65.00, 87.00, 87.00),
                (4316.00, 0.00, 4.00, 35.00, 65.00, 87.00, 87.00),
                (4433.00, 0.00, 0.00, 26.00, 52.00, 82.00, 87.00),
                (4437.33, 0.00, 0.00, 26.00, 52.00, 82.00, 87.00),
                (4554.33, 0.00, 0.00, 13.00, 43.00, 74.00, 91.00),
                (4558.67, 0.00, 0.00, 13.00, 43.00, 74.00, 91.00),
                (4675.67, 0.00, 0.00, 4.00, 35.00, 65.00, 95.00),
                (4680.00, 0.00, 0.00, 4.00, 35.00, 65.00, 91.00),
                (5473.00, 0.00, 0.00, 0.00, 0.00, 0.00, 30.00),
                (5477.33, 0.00, 0.00, 0.00, 0.00, 0.00, 30.00),
                (5841.33, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00),
                (5845.67, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00),
            ]
        }

        cls.loan_withhold_sample_data = {
            "weekly": [
                (641, 0, 6),
                (649, 0, 6),
                (650, 0, 7),
                (749, 0, 7),
                (750, 0, 8),
                (793, 0, 8),
                (794, 0, 16),
                (824, 0, 16),
                (825, 0, 17),
                (862, 0, 17),
                (863, 0, 22),
                (899, 0, 22),
                (900, 0, 23),
                (935, 0, 23),
                (936, 0, 28),
            ],
            "monthly": [
                (5000, 100, 199),
            ]
        }

        # Used in a few tests. Can be overriden.
        cls.default_payroll_structure = cls.env.ref('l10n_au_hr_payroll.hr_payroll_structure_au_regular')

        cls.default_input_lines = [
            {
                'input_type_id': cls.env.ref('l10n_au_hr_payroll.input_bonus_commissions').id,
                'amount': 200,
            },
            # RTW
            {
                'input_type_id': cls.env.ref('l10n_au_hr_payroll.input_b2work').id,
                'amount': 300,
            },
            # Work related non expense
            {
                'input_type_id': cls.env.ref('l10n_au_hr_payroll.input_work_related_non_expense').id,
                'amount': 550,
            },
        ]

        # Will be useful for easy access to the ID when testing
        cls.work_entry_types = {
            entry_type.code: entry_type
            for entry_type in cls.env['hr.work.entry.type'].search([])
        }

        cls.annual_leave_type = cls.env['hr.leave.type'].create({
            'name': 'Annual Leave',
            'company_id': cls.australian_company.id,
            'l10n_au_leave_type': 'annual',
            'leave_validation_type': 'no_validation',
            'work_entry_type_id': cls.env.ref('l10n_au_hr_payroll.l10n_au_work_entry_paid_time_off').id,
        })

    def create_employee_and_contract(self, wage, contract_info=False):
        if not contract_info:
            contract_info = {}
        employee_id = self.env["hr.employee"].create({
            "name": contract_info.get('employee', 'Mel'),
            "resource_calendar_id": self.resource_calendar.id,
            "company_id": self.australian_company.id,
            "private_street": "1 Test Street",
            "private_city": "Sydney",
            "private_country_id": contract_info.get('private_country_id', self.env.ref("base.au").id),
            "country_id": contract_info.get('country_id', self.env.ref("base.au").id),
            "work_phone": "123456789",
            "private_phone": "123456789",
            "private_email": "test@odoo.com",
            "birthday": contract_info.get('birthday', date.today() - relativedelta(years=22)),
            # fields modified in the tests
            "marital": "single",
            "l10n_au_tfn_declaration": contract_info.get('tfn_declaration', 'provided'),
            "l10n_au_tfn": contract_info.get('tfn', '12345678'),
            "is_non_resident": contract_info.get('non_resident', False),
            "l10n_au_nat_3093_amount": 0,
            "l10n_au_child_support_garnishee_amount": 0,
            "l10n_au_medicare_exemption": contract_info.get('medicare_exemption', 'X'),
            "l10n_au_medicare_surcharge": contract_info.get('medicare_surcharge', 'X'),
            "l10n_au_medicare_reduction": contract_info.get('medicare_reduction', 'X'),
            "l10n_au_child_support_deduction": 0,
            "l10n_au_extra_pay": contract_info.get('extra_pay', False),
            "l10n_au_training_loan": contract_info.get('l10n_au_training_loan', True),
            "l10n_au_tax_free_threshold": contract_info.get('l10n_au_tax_free_threshold', False),
            "l10n_au_employment_basis_code": contract_info.get('employment_basis_code', 'F'),
            "l10n_au_withholding_variation": 'none',
            "l10n_au_withholding_variation_amount": 0,
            "l10n_au_tax_treatment_category": self.tax_treatment_category,
            "l10n_au_tax_treatment_option_actor": contract_info.get('tax_treatment_option_actor', False),
            "l10n_au_tax_treatment_option_voluntary": contract_info.get('tax_treatment_option_voluntary', False),
            "l10n_au_tax_treatment_option_seniors": contract_info.get('tax_treatment_option_seniors', False),
            "l10n_au_less_than_3_performance": contract_info.get('less_than_3_performance', False),
            "l10n_au_income_stream_type": contract_info.get('income_stream_type', 'SAW'),
            "l10n_au_comissioners_installment_rate": contract_info.get('comissioners_installment_rate', 0),
        })

        contract_id = self.env["hr.contract"].create({
            "name": f"{contract_info.get('employee', 'Mel')}'s contract",
            "employee_id": employee_id.id,
            "resource_calendar_id": self.resource_calendar.id,
            "company_id": self.australian_company.id,
            "date_start": contract_info.get('contract_date_start', date(2023, 7, 1)),
            "date_end": contract_info.get('contract_date_end', False),
            "wage_type": contract_info.get('wage_type', 'monthly'),
            "wage": contract_info.get('wage', wage),
            "l10n_au_casual_loading": contract_info.get('casual_loading', 0),
            "structure_type_id": self.default_payroll_structure.type_id.id,
            # fields modified in the tests
            "schedule_pay": contract_info.get("schedule_pay", "monthly"),
            "l10n_au_leave_loading": contract_info.get('leave_loading', False),
            "l10n_au_leave_loading_rate": contract_info.get('leave_loading_rate', 0),
            "l10n_au_workplace_giving": contract_info.get('workplace_giving_employee', 0),
            "l10n_au_workplace_giving_employer": contract_info.get('workplace_giving_employer', 0),
            "l10n_au_salary_sacrifice_superannuation": contract_info.get('salary_sacrifice_superannuation', 0),
            "l10n_au_salary_sacrifice_other": contract_info.get('salary_sacrifice_other', 0),
            "l10n_au_performances_per_week": contract_info.get('performances_per_week', 0),
            "state": 'open'
        })
        if contract_info.get('wage_type') == 'hourly':
            contract_id.write({'hourly_wage': contract_info.get('hourly_wage')})
        employee_id.contract_id = contract_id
        return employee_id, contract_id

    def _create_employee(self, contract_info):
        employee, contract = self.create_employee_and_contract(5000, contract_info)
        return employee, contract

    def _test_payslip(self, employee, contract, expected_lines, expected_worked_days=False, input_lines=False, payslip_date_from=False, payslip_date_to=False, termination_type=False, **kwargs):
        """ This method is to be called in order to test a payslip.
        It will be using the default_payroll_structure field and _prepare_payslip method to set things up, so these
        are expected to be overriden for each class testing a specific structure.

        It will test the workdays and line on their content, but also their order.
        """
        # 1) Create the payslip if not given
        payslip = kwargs.get('payslip', False)
        if not payslip:
            payslip = self.env["hr.payslip"].create({
                "name": "payslip",
                "employee_id": employee.id,
                "contract_id": contract.id,
                "struct_id": self.default_payroll_structure.id,
                "date_from": payslip_date_from or date(2023, 7, 1),
                "date_to": payslip_date_to or date(2023, 7, 31),
                "input_line_ids": [Command.create(input_line) for input_line in input_lines] if input_lines else [],
                "l10n_au_termination_type": termination_type,
            })
            # 2) Recompute the payslip.
            payslip.action_refresh_from_work_entries()

        # 2) Verify the workdays
        if self.default_payroll_structure.use_worked_day_lines:
            for expected_worked_day, payslip_workday in izip_longest(expected_worked_days, payslip.worked_days_line_ids):
                assert expected_worked_day and payslip_workday, (
                        "%s worked day lines expected in the test, but %s were found in the payslip."
                        % (len(expected_worked_days), len(payslip.worked_days_line_ids)))

                expected_entry_type_id, expected_day, expected_hour, expected_amount = expected_worked_day
                self.assertEqual(expected_entry_type_id, payslip_workday.work_entry_type_id.id)
                self.assertAlmostEqual(expected_day, payslip_workday.number_of_days, 0)
                self.assertAlmostEqual(expected_hour, payslip_workday.number_of_hours, 0)
                self.assertAlmostEqual(expected_amount, payslip_workday.amount, 0)

        # 3) Verify the lines
        for expected_line, payslip_line in izip_longest(expected_lines, payslip.line_ids.sorted()):
            assert expected_line and payslip_line, (
                    "%s payslip lines expected by the test, but %s were found in the payslip."
                    % (len(expected_lines), len(payslip.line_ids)))

            expected_code, expected_total = expected_line
            self.assertEqual(expected_code, payslip_line.code)
            # compare with whole numbers
            self.assertAlmostEqual(
                expected_total,
                payslip_line.total,
                places=0,
                msg=f"Unexpected value for code {expected_code}"
            )

        # 4) Validate the payslip. Mostly useful for testing on a period. Doesn't use action_payslip_done as it would fail
        # if the account payroll module is there (no journal)
        payslip.state = 'done'

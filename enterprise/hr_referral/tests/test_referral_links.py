# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_join

from .common import TestHrReferralBase


class TestReferralLinks(TestHrReferralBase):

    def test_search_or_create_referral_links(self):
        '''
        Test the search_or_create_referral_links method of the hr.job model

        This method will test the uniqueness of each link between users and
        between channel. Finally, it will test if no new link have
        been created after the second call of the method.
        '''

        users = self.env['res.users'].search([])
        job = self.env['hr.job'].create({
            'name': 'test_search_or_create_referral_links',
            'no_of_recruitment': '5',
            'is_published': True,
            'department_id': self.dep_rd.id,
            'company_id': self.company_1.id,
        })

        links_by_user_by_channel = {}
        links = []
        for channel in ['direct', 'facebook', 'twitter', 'linkedin']:
            # check the uniqueness of the links between users
            channel_links = job.search_or_create_referral_links(users, channel)
            set_links = set(channel_links.values())
            self.assertEqual(len(channel_links), len(set_links), 'There are duplicated links between users')
            check_already_created = job.search_or_create_referral_links(users, channel)
            # check the consistency of the links
            for user, link in channel_links.items():
                self.assertEqual(
                    link, check_already_created[user],
                    'The link is not the same')
            links_by_user_by_channel[channel] = channel_links
            links += links_by_user_by_channel[channel].values()
        # check the uniqueness of the links between channel
        all_links_set = set(links)
        self.assertEqual(len(links), len(all_links_set), 'There are duplicated links between channel')
        # check if no new link have been created
        job_url = url_join(job.get_base_url(), (job.website_url or '/jobs'))
        trackers = self.env['link.tracker'].search(
            [('url', '=', job_url), ('campaign_id', '=', job.utm_campaign_id.id)])
        self.assertEqual(len(trackers), len(all_links_set), 'There are new links created')

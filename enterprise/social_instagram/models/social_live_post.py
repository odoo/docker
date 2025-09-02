# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import requests

from odoo import models, fields
from werkzeug.urls import url_join


class SocialLivePostInstagram(models.Model):
    _inherit = 'social.live.post'

    instagram_post_id = fields.Char('Instagram Post ID', readonly=True)

    def _compute_live_post_link(self):
        instagram_live_posts = self._filter_by_media_types(['instagram']).filtered(lambda post: post.state == 'posted')
        super(SocialLivePostInstagram, (self - instagram_live_posts))._compute_live_post_link()

        for post in instagram_live_posts:
            post.live_post_link = f'https://www.instagram.com/{post.account_id.social_account_handle}'

    def _refresh_statistics(self):
        super(SocialLivePostInstagram, self)._refresh_statistics()
        accounts = self.env['social.account'].search([('media_type', '=', 'instagram')])

        for account in accounts:
            posts_endpoint = url_join(
                self.env['social.media']._INSTAGRAM_ENDPOINT,
                f'{account.instagram_account_id}/media')

            response = requests.get(posts_endpoint,
                params={
                    'access_token': account.instagram_access_token,
                    'fields': 'id,comments_count,like_count'
                },
                timeout=5
            ).json()

            if 'data' not in response:
                self.account_id._action_disconnect_accounts(response)
                return False

            instagram_post_ids = [post.get('id') for post in response['data']]
            existing_live_posts = self.env['social.live.post'].sudo().search([
                ('instagram_post_id', 'in', instagram_post_ids)
            ])

            existing_live_posts_by_instagram_post_id = {
                live_post.instagram_post_id: live_post for live_post in existing_live_posts
            }

            for post in response['data']:
                existing_live_post = existing_live_posts_by_instagram_post_id.get(post.get('id'))
                if existing_live_post:
                    existing_live_post.write({
                        'engagement': post.get('comments_count', 0) + post.get('like_count', 0)
                    })

    def _post(self):
        instagram_live_posts = self._filter_by_media_types(['instagram'])
        super(SocialLivePostInstagram, (self - instagram_live_posts))._post()

        for live_post in instagram_live_posts:
            live_post._post_instagram()

    def _post_instagram(self):
        """
        Handles the process of posting images to Instagram, supporting both single and multiple (carousel) posts.

        Steps for Posting Image(s):
        1. Create Media Container(s):
            - Upload image(s) and associated data using an initial HTTP request to create media container(s).

        2. Create Carousel Container (if multiple images):
            - For carousel posts, group the individual media containers into a single carousel container using an additional HTTP request.

        3. Publish the Container:
            - Mark the media or carousel container as published using the ID returned from the previous request(s).

        More information & examples:
        - https://developers.facebook.com/docs/instagram-api/reference/ig-user/media
        - https://developers.facebook.com/docs/instagram-api/reference/ig-user/media_publish
        """

        self.ensure_one()
        account = self.account_id
        post = self.post_id

        base_url = self.get_base_url()
        endpoint = self.env['social.media']._INSTAGRAM_ENDPOINT
        media_url = url_join(endpoint, f"/{account.instagram_account_id}/media")
        media_publish_url = url_join(endpoint, f"/{account.instagram_account_id}/media_publish")

        media_container_ids = []
        session = requests.Session()
        # Step 1: Create Media Container(s)
        for image in self.image_ids:
            data = {
                'access_token': account.instagram_access_token,
                'image_url': url_join(
                    base_url,
                    f'/social_instagram/{post.instagram_access_token}/get_image/{image.id}'
                )
            }

            if len(self.image_ids) == 1:
                data['caption'] = self.message
            else:
                data['is_carousel_item'] = True

            media_response = session.post(media_url, data, timeout=10)
            if not media_response.ok or not media_response.json().get('id'):
                self.write({
                    'state': 'failed',
                    'failure_reason': json.loads(media_response.text or '{}').get('error', {}).get('message', '')
                })
                return

            media_container_ids.append(media_response.json().get('id'))

        if len(media_container_ids) == 1:
            # Step 3: Publish the Container (single post)
            publish_response = session.post(
                media_publish_url,
                data={
                    'access_token': account.instagram_access_token,
                    'creation_id': media_container_ids[0],
                },
                timeout=10,
            )
        else:
            # Step 2: Create Carousel Container (if multiple images)
            media_response = session.post(
                media_url,
                json={
                    'caption': self.message,
                    'access_token': account.instagram_access_token,
                    'media_type': 'CAROUSEL',
                    'children': media_container_ids
                },
                timeout=10,
            )
            if not media_response.ok or not media_response.json().get('id'):
                self.write({
                    'state': 'failed',
                    'failure_reason': json.loads(media_response.text or '{}').get('error', {}).get('message', '')
                })
                return
            # Step 3: Publish the Container (multi post)
            publish_response = session.post(
                media_publish_url,
                data={
                    'access_token': account.instagram_access_token,
                    'creation_id': media_response.json()['id'],
                },
                timeout=10,
            )

        if publish_response.ok:
            self.instagram_post_id = publish_response.json().get('id', False)
            values = {
                'state': 'posted',
                'failure_reason': False
            }
        else:
            values = {
                'state': 'failed',
                'failure_reason': json.loads(publish_response.text or '{}').get('error', {}).get('message', '')
            }
        self.write(values)

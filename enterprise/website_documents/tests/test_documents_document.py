# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestDocumentsShare(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Document = cls.env['documents.document']
        Company = cls.env['res.company']
        Website = cls.env['website']
        cls.website_2 = Website.create({'name': 'Test no company', 'domain': 'https://website_2.com'})
        cls.website_company_1 = Website.create({'name': 'Test company 1', 'domain': 'https://company_1.com'})
        cls.website_company_3 = Website.create({'name': 'Test company 3', 'domain': 'https://company_3.com'})
        cls.website_main_company = cls.env.ref('base.main_company').website_id
        cls.website_main_company.domain = 'https://main.company.com'

        cls.company_1 = Company.create({'name': 'Company 1 with website', 'website_id': cls.website_company_1.id})
        cls.company_3 = Company.create({'name': 'Company 3 with website', 'website_id': cls.website_company_3.id})
        cls.company_without_website = Company.create({'name': 'Company without website'})
        cls.folder = Document.create({'name': 'Folder no company', 'type': 'folder'})

        cls.default_domain = cls.company_without_website.get_base_url()  # Company without website -> default domain

    def test_share_url_domain(self):
        """ Test the default share domain URL and website in various setup.

        It also tests that the website can be changed manually and that the
        share domain is adjusted accordingly.
        """
        # Test URL domain when sharing documents without a company.
        self.assertEqual(self.folder.website_id, self.website_main_company)
        self.assertSequenceEqual(self.folder.access_url[:24], 'https://main.company.com')

        # Test URL domain when sharing documents with a company with a website.
        self.folder.company_id = self.company_1
        self.assertSequenceEqual(self.folder.access_url[:21], 'https://company_1.com')

        # Test share URL domain when sharing documents/folder with a company without a website.
        self.folder.company_id = self.company_without_website
        self.assertEqual(self.folder.website_id, self.website_main_company)
        self.assertTrue(self.folder.access_url.startswith('https://main.company.com'))

        # Test documents/folder sharing with a company without a website and a main website without domain.
        self.website_main_company.domain = ''
        self.folder.company_id = self.company_without_website
        self.assertEqual(self.folder.website_id, self.website_main_company)
        self.assertTrue(self.folder.access_url.startswith(self.default_domain))

        # Test that the URL is updated when changing the website manually
        self.folder.website_id = self.website_2
        self.assertTrue(self.folder.access_url.startswith('https://website_2.com'))

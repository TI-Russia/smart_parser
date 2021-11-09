from office_db.web_site_list import  TDeclarationWebSiteList
from common.logging_wrapper import setup_logging

from django.test import TestCase


class RedirectsTestCase(TestCase):
    def test_office_website_valid(self):
        logger = setup_logging("test_office_website_valid")
        web_sites = TDeclarationWebSiteList(logger)
        self.assertEqual(True, web_sites.check_valid(logger, fail_fast=True))
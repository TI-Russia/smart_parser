import json
import os.path

from common.decl_title_parser import  TDeclarationTitleParser

from django.test import TestCase, tag


class ParseTitleTestCase(TestCase):
    @tag('central')
    def test_office_website_valid(self):
        path = os.path.join(os.path.dirname(__file__), "examples.json")
        with open(path) as inp:
            cnt = 0
            for j in json.load(inp):
                cnt += 1
                canon = TDeclarationTitleParser.from_json(j)
                test = TDeclarationTitleParser(canon.input_title)
                self.assertTrue(test.parse(raise_exception=True), canon.input_title)
                self.assertEqual(canon.type, test.type)
                self.assertEqual(canon.org_name, test.org_name)
                self.assertEqual(canon.decl_time, test.decl_time)
                self.assertListEqual(canon.decl_objects, test.decl_objects)
        print("number of tested declaration titles={}".format(cnt))
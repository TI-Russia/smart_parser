import os

from common.content_types import file_extension_by_file_contents
from unittest import TestCase


class TestFileExtensionByFileContent(TestCase):

    def test_lib_magic(self):
        def check(file_path):
            file_path = os.path.join(os.path.dirname(__file__), file_path)
            predicted_extension = file_extension_by_file_contents(file_path)
            _, file_extension = os.path.splitext(file_path)
            self.assertEqual(file_extension, predicted_extension)

        check('web_sites/pdf/sved.pdf')
        check('web_sites/admkrsk2/clerk/incomes/Lists/supreme/Attachments/92/Одинцов2020.docx')
        check('web_sites/unrar/file.rar')
        check('web_sites/archives/sved.docx.zip')
        check('../../DeclDocRecognizer/regression_tests/3223.doc')
        check('web_sites/archives/sved.docx.7z')
        check('../../DeclDocRecognizer/regression_tests/simple_minus.rtf')
        check('../../DeclDocRecognizer/regression_tests/3384_0.xls')
        check('../../DeclDocRecognizer/regression_tests/35078_3.xlsx')
        check('web_sites/khabkrai/sved.html')

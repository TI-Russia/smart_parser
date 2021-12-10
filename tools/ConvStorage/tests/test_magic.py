import os.path
import magic
from unittest import TestCase


class TLibMagic(TestCase):
    def test_lib_magic(self):
        path = os.path.join(os.path.dirname(__file__), "files", "1501.pdf")
        assert os.path.exists(path)
        mime_type = magic.from_file(path, mime=True)
        self.assertEqual('application/pdf', mime_type)
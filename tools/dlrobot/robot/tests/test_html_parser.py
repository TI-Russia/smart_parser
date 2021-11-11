from unittest import TestCase
from common.html_parser import THtmlParser, get_html_title
from common.download import get_original_encoding

LONG_HTML =  """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Title</title>
</head>
<body>

<div>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>

    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>

    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>

    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>

    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>

    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>

    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>
    <code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code><code>

    Code in here
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>

            </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>

            </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>

            </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>

            </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>

            </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>

            </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>
    </code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code></code>


    </div>


</body>
</html>
"""


class TestHtmlParser(TestCase):
    def test_recusion(self):
        # without sys.setrecursionlimit(10000) file a.html cannot be processed by BeautifulSoup
        html_parser = THtmlParser(LONG_HTML)
        html_len = len(html_parser.html_with_markup)
        self.assertGreater(html_len, 20000)

    def test_get_title(self):
        html = "<html><head><title> test </title></head><body></body></html>"
        title = get_html_title(html)
        self.assertEqual("test", title)

    def test_html_data_in_ascii(self):
        html = b'<html><head><meta http-equiv="Refresh" content="0; URL=http://sosnogorsk.org/administration_mr_sosnogorsk/structure/?attempt=1"></head><body></body></html>'
        encoding = get_original_encoding(None, html)
        self.assertEqual("ascii", encoding)

    def test_html_data_in_utf8(self):
        html = b'<html lang="ru"><head><meta charset="UTF-8"></html>'
        encoding = get_original_encoding(None, html)
        self.assertEqual("utf-8", encoding)

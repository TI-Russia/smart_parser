from unittest import TestCase
from common.html_parser import THtmlParser

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

class TestRecursion(TestCase):
    def test_recusion(self):
        # without sys.setrecursionlimit(10000) file a.html cannot be processed by BeautifulSoup
        html_parser = THtmlParser(LONG_HTML)
        html_len = len(html_parser.html_with_markup)
        self.assertGreater(html_len, 20000)




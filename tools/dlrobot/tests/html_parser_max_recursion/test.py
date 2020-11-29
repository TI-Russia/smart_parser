from common.html_parser import THtmlParser
# without sys.setrecursionlimit(10000) file a.html cannot be processed by BeautifulSoup
with open("a.html", "r") as inp:
    file_data = inp.read()
html_parser = THtmlParser(file_data)
print ("html len={}".format(len(html_parser.html_text)))

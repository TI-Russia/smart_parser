from bs4 import BeautifulSoup

#see https://stackoverflow.com/questions/31528600/beautifulsoup-runtimeerror-maximum-recursion-depth-exceeded
import sys
sys.setrecursionlimit(10000)


class THtmlParser:
    def __init__(self, file_data):
        self.file_data = file_data
        self.soup = BeautifulSoup(self.file_data, "html.parser")
        self.html_text = str(self.soup)
        self.page_title = self.soup.title.string if self.soup.title is not None else ""

    def get_text(self):
        return self.soup.get_text()


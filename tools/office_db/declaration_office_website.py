from common.web_site_status import TWebSiteReachStatus


class TDeclarationWebSite:
    def __init__(self, url=None, parent_office=None):
        self.url = url
        self.reach_status = TWebSiteReachStatus.normal
        self.comments = None
        self.redirect_to = None
        self.title = None
        self.corruption_keyword_in_html = None

        # not serialized items
        self.parent_office = parent_office

    def read_from_json(self, js):
        self.url = js.get('url')
        self.reach_status = js.get('status', TWebSiteReachStatus.normal)
        self.comments = js.get('comments')
        self.redirect_to = js.get('redirect_to')
        self.corruption_keyword_in_html = js.get('corruption_keyword_in_html')
        if self.redirect_to is not None:
            self.ban()
        self.title = js.get('title')
        return self

    def write_to_json(self):
        rec = {
            'url': self.url,
        }
        if self.reach_status != TWebSiteReachStatus.normal:
            rec['status'] = self.reach_status
        if self.comments is not None:
            rec['comments'] = self.comments
        if self.redirect_to is not None:
            rec['redirect_to'] = self.redirect_to
        if self.title is not None:
            rec['title'] = self.title
        if self.corruption_keyword_in_html is not None:
            rec['corruption_keyword_in_html'] = self.corruption_keyword_in_html
        return rec

    def set_redirect(self, to_url):
        self.redirect_to = to_url
        self.ban()

    def ban(self):
        self.reach_status = TWebSiteReachStatus.abandoned

    def set_title(self, title):
        self.title = title

    def can_communicate(self):
        return TWebSiteReachStatus.can_communicate(self.reach_status)

    def set_parent(self, office):
        self.parent_office = office

    def get_parent_source_id(self):
        return self.parent_office.source_id
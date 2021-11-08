from web_site_db.web_site_status import TWebSiteReachStatus


class TDeclarationWebSite:
    def __init__(self):
        self.url = None
        self.reach_status = TWebSiteReachStatus.normal
        self.dlrobot_max_time_coeff = 1.0
        self.comments = None
        self.redirect_to = None
        self.title = None

    def read_from_json(self, js):
        self.url = js.get('url')
        self.reach_status = js.get('status', TWebSiteReachStatus.normal)
        self.dlrobot_max_time_coeff = js.get('dlrobot_max_time_coeff', 1.0)
        self.comments = js.get('comments')
        self.redirect_to = js.get('redirect_to')
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
        if self.dlrobot_max_time_coeff != 1.0:
            rec['dlrobot_max_time_coeff'] = self.dlrobot_max_time_coeff
        if self.comments is not None:
            rec['comments'] = self.comments
        if self.redirect_to is not None:
            rec['redirect_to'] = self.redirect_to
        if self.title is not None:
            rec['title'] = self.title
        return rec

    def set_redirect(self, to_url):
        self.redirect_to = to_url
        self.ban()

    def ban(self):
        self.reach_status = TWebSiteReachStatus.abandoned

    def set_title(self, title):
        self.title = title

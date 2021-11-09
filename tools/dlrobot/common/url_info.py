from common.link_info import TLinkInfo


class TUrlInfo:
    def __init__(self, title=None, step_name=None, depth=0, parent_node=None):
        self.step_name = step_name
        self.html_title = title
        self.depth = depth
        self.parent_nodes = set()
        if parent_node is not None:
            self.add_parent_node(parent_node)
        self.linked_nodes = dict()
        self.downloaded_files = list()

    def from_json(self, init_json):
        self.step_name = init_json['step']
        self.html_title = init_json['title']
        self.parent_nodes = set(init_json.get('parents', list()))
        self.linked_nodes = init_json.get('links', dict())
        self.depth = init_json.get('depth', 0)
        self.downloaded_files = list()
        for rec in init_json.get('downloaded_files', list()):
            self.downloaded_files.append(TLinkInfo(None, None, None).from_json(rec))
        return self

    def to_json(self):
        record = {
            'step': self.step_name,
            'title': self.html_title,
            'parents': list(self.parent_nodes),
            'links': self.linked_nodes,
            'depth': self.depth,
        }
        if len(self.downloaded_files) > 0:
            record['downloaded_files'] = list(x.to_json() for x in self.downloaded_files)
        return record

    def add_downloaded_file(self, link_info: TLinkInfo):
        self.downloaded_files.append(link_info)

    def add_child_link(self, href, record):
        self.linked_nodes[href] = record

    def update_depth(self, depth):
        if depth < self.depth:
            self.depth = depth

    def add_parent_node(self, parent_node):
        self.parent_nodes.add(parent_node)

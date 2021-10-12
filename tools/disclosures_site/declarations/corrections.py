import json
import os


class TSectionCorrections:

    def __init__(self):
        self.old_sections_to_new = dict()
        filepath = os.path.join(os.path.dirname(__file__), "../data/corrections.json")
        with open(filepath) as inp:
            for k,v in json.load(inp).items():
                self.old_sections_to_new[int(k)] = int(v)

    def get_corrected_section_id(self, section_id):
        return self.old_sections_to_new.get(section_id)


SECTION_CORRECTIONS = TSectionCorrections()
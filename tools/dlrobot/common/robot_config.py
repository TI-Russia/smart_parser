import json


class TRobotConfig:
    def __init__(self, config_json=None):
        self.config_json = config_json

    @staticmethod
    def read_from_file(file_path):
        c = TRobotConfig()
        with open(file_path) as inp:
            c.config_json = json.load(inp)
        return c

    def get_step_passports(self):
        return self.config_json['robot_steps']

    def get_step_index_by_name(self, name):
        if name is None:
            return -1
        for i, r in enumerate(self.get_step_passports()):
            if name == r['step_name']:
                return i
        raise Exception("cannot find step {}".format(name))

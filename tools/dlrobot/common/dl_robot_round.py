import datetime
import json
import os


class BadFormat(Exception):

    def __init__(self, message="bad format"):
        """Initializer."""
        self.message = message
    def __str__(self):
        return self.message


class TDeclarationRounds:
    default_dlrobot_round_path = os.path.join(os.path.dirname(__file__), "../central/data/dlrobot_rounds.json")

    def __init__(self, file_name=None):
        self.rounds = list()
        self.start_time_stamp = None
        if file_name is None:
            self.file_name = TDeclarationRounds.default_dlrobot_round_path
        else:
            self.file_name = file_name
        if not os.path.exists(self.file_name):
            raise BadFormat("File {} does not exist".format(self.file_name))
        with open(self.file_name, "r") as inp:
            self.rounds = json.load(inp)
        for r in self.rounds:
            t = datetime.datetime.strptime(r['start_time'], '%Y-%m-%d %H:%M')
            self.start_time_stamp = t.timestamp()
        if len(self.rounds) == 0:
            raise BadFormat("no dlrobot information in {}".format(self.file_name))
        if self.rounds[-1].get('finished', False):
            raise BadFormat("no current round found, please add a new record to {} in order to create to a new round".format(self.file_name))

    @staticmethod
    def build_an_example(date):
        return [
              {"start_time": date.strftime('%Y-%m-%d %H:%M'), "finished": False}
        ]
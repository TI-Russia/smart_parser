from declarations.input_json import TIntersectionStatus, TDlrobotHumanFile

import json
import sys

if __name__ == '__main__':
    dlrobot_human = TDlrobotHumanFile(sys.argv[1])
    print(json.dumps(dlrobot_human.get_stats(), indent=4))

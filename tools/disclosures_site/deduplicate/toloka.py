import sys
import os

DEDUPLICATE_ROOT = os.path.dirname(os.path.realpath(__file__))


class TToloka:
    TASKS_PATH = os.path.join(DEDUPLICATE_ROOT, 'tasks')
    ASSIGNMENTS_PATH = os.path.join(DEDUPLICATE_ROOT, 'assignments')
    RESULT_POOLS_PATH = os.path.join(DEDUPLICATE_ROOT, 'pools')
    # columns id Toloka tsv files
    ID_LEFT = 'INPUT:id_left'
    ID_RIGHT = 'INPUT:id_right'
    JSON_LEFT = 'INPUT:json_left'
    JSON_RIGHT = 'INPUT:json_right'
    RESULT = 'OUTPUT:result'
    GOLDEN = 'GOLDEN:result'

    @staticmethod
    def read_toloka_golden_pool(filename, convert_unk_to_no=True):
        test_data = {}
        with open(filename, 'r', encoding="utf-8") as tsv:
            header = []
            line_no = 0
            for x in tsv:
                if line_no == 0:
                    if x.find('INPUT:') != -1:
                        header = list(x.strip().split("\t"))
                        line_no += 1
                        continue
                    else:
                        assert x.find('GOLDEN:') == -1
                        assert x.find('OUTPUT:') == -1
                        header = list('INPUT:id_left\tINPUT:id_right\tGOLDEN:result'.strip().split("\t"))

                line_no += 1
                values = x.strip().split("\t")

                if len(values) == 0:
                    continue  # skip empty lines
                if len(values) != len(header):
                    print("bad at line {}".format(line_no), file=sys.stderr)
                    # assert (len(values) != len(header))
                    continue

                task = dict(zip(header, values))
                id1 = task['INPUT:id_left']
                id2 = task['INPUT:id_right']
                if not task.get('GOLDEN:result'):
                    print("no GOLDEN:result at line {}".format(line_no), file=sys.stderr)
                    continue

                mark = task['GOLDEN:result']
                if mark == "UNK" and convert_unk_to_no:
                    mark = "NO"
                if (id1 > id2):
                    id1, id2 = id2, id1
                test_data[(id1, id2)] = mark
        return test_data

    @staticmethod
    def calc_metrics(pairs, testData):
        truePositive = 0
        falsePositive = 0
        foundPairs = set()
        results = []

        for id1, id2, score1, score2 in pairs:
            if (id1 > id2):
                id1, id2 = id2, id1
            if (id1, id2) in foundPairs:
                continue
            foundPairs.add((id1, id2))

            markup = testData.get((id1, id2))
            if markup == None:
                # no toloker has seen this pair -> no information
                pass
            elif markup == "YES":
                truePositive += 1
                results.append((id1, id2, score1, score2, "TP"))
            elif markup == "NO":
                falsePositive += 1
                results.append((id1, id2, score1, score2, "FP"))
            elif markup == "UNK":
                # tolokers have said there is no enough information, but we have not convereted to NO (convert_unk_to_no=False)
                pass

        falseNegative = 0
        for ((id1, id2), mark) in testData.items():
            if mark == "YES":
                if (id1, id2) not in foundPairs:
                    results.append((id1, id2, str(-1), str(-1), "FN"))
                    falseNegative += 1

        if truePositive == 0:
            metrics = {"F1": 0.0, "P": 0.0, "R": 0.0}
        else:
            precision = float(truePositive) / float(truePositive + falsePositive)
            recall = float(truePositive) / float(truePositive + falseNegative)
            f1 = 2.0 * precision * recall / (precision + recall)
            metrics = {
                "P": round(precision, 4),
                "R": round(recall, 4),
                "F1": round(f1, 4)
            }
        return metrics, results

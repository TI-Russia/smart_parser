import operator

from disclosures_site.predict_office.prediction_case import TPredictionCase

import json
import random
from sklearn.model_selection import train_test_split
import csv


class TOfficePool:
    UNKNOWN_OFFICE_ID = 1234567890

    def __init__(self, logger, office_index=None):
        self.pool = list()
        self.logger = logger
        self.office_index = office_index

    def read_cases(self, file_name: str, row_count=None, make_uniq=False):
        cnt = 0
        already = set()
        with open(file_name, "r") as inp:
            for line in inp:
                try:
                    if make_uniq:
                        if hash(line) in already:
                            self.logger.debug("skip {} (a copy found)".format(sha256))
                            continue
                        already.add(hash(line))

                    sha256, web_domain, office_id, office_strings = line.strip().split("\t")
                    if int(office_id) == self.UNKNOWN_OFFICE_ID:
                        self.logger.debug("skip {} (unknown office id)".format(sha256))
                        continue

                    case = TPredictionCase(self.office_index, sha256, web_domain, int(office_id), office_strings)
                    if len(case.text) == 0:
                        self.logger.debug("skip {} (empty text)".format(sha256))
                        continue
                    if len(case.web_domain) == 0:
                        self.logger.debug("skip {} (empty web domain)".format(sha256))
                        continue

                    self.pool.append(case)
                    cnt += 1
                    if row_count is not None and cnt >= row_count:
                        break
                except ValueError as err:
                    self.logger.debug("cannot parse line {}, skip it".format(line.strip()))
                    pass
        self.logger.info("read {} cases from {}".format(cnt, file_name))

    @staticmethod
    def write_pool(cases, output_path):
        c: TPredictionCase
        with open(output_path, "w") as outp:
            for c in cases:
                outp.write("{}\n".format("\t".join([c.sha256, c.web_domain,  str(c.true_office_id), c.office_strings])))

    def split(self, train_pool_path, test_pool_path, test_size=0.2):
        random.shuffle(self.pool)
        if test_pool_path is not None:
            train, test = train_test_split(self.pool, test_size=test_size)
            self.write_pool(train, train_pool_path)
            self.write_pool(test, test_pool_path)
            self.logger.info("train size = {}, test size = {}".format(len(train), len(test)))
        else:
            self.write_pool(self.pool, train_pool_path)
            self.logger.info("train size = {}".format(len(self.pool)))

    def build_toloka_pool(self,  test_y_pred, output_path):
        assert len(self.pool) == len(test_y_pred)

        with open(output_path, "w") as outp:
            case: TPredictionCase
            cnt = 0
            tsv_writer = csv.writer(outp, delimiter="\t")
            for case, pred_proba_y in zip(self.pool, test_y_pred):
                hypots = dict()
                if case.true_office_id is not None:
                    hypots[case.true_office_id] = 1

                learn_target, weight = max(enumerate(pred_proba_y), key=operator.itemgetter(1))
                max_office_id = self.office_index.get_office_id_by_ml_office_id(learn_target)
                hypots[max_office_id] = float(weight)

                if case.true_office_id != max_office_id:
                    for o in self.office_index.get_offices_by_web_domain(case.web_domain):
                        hypots[o] = 0
                    for ml_office_id, weight in enumerate(pred_proba_y):
                        if weight > 0.8:
                            office_id = self.office_index.get_office_id_by_ml_office_id(ml_office_id)
                            hypots[office_id] = weight

                office_infos = list()
                for office_id, weight in sorted(hypots.items(), key=operator.itemgetter(1), reverse=True):
                    rec =  {
                        'hypot_office_id': int(office_id),
                        'hypot_office_name': self.office_index.get_office_name(office_id),
                        "weight": round(float(weight), 4),
                    }
                    if len(hypots) == 1:
                        rec['status'] = "true_positive"
                    office_infos.append(rec)
                office_strings = json.loads(case.office_strings)
                rec = {
                    "INPUT:sha256":  case.sha256,
                    "INPUT:web_domain": case.web_domain,
                    "INPUT:web_domain_title": self.office_index.web_sites.get_title_by_web_domain(case.web_domain),
                    'INPUT:doc_title': office_strings.get('title', ''),
                    'INPUT:doc_roles': ";".join(office_strings.get('roles', [])),
                    'INPUT:doc_departments': ";".join(office_strings.get('departments', [])),
                    'INPUT:office_hypots': json.dumps(office_infos, ensure_ascii=False)
                }
                if cnt == 0:
                    tsv_writer.writerow(list(rec.keys()))
                tsv_writer.writerow(list(rec.values()))
                cnt += 1

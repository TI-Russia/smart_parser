from disclosures_site.predict_office.prediction_case import TPredictionCase

import json
import random
from sklearn.model_selection import train_test_split
import csv


class TOfficePool:
    UNKNOWN_OFFICE_ID = 1234567890

    def __init__(self, ml_model, file_name: str, row_count=None):
        self.pool = list()
        self.ml_model = ml_model
        self.logger = ml_model.logger
        self.read_cases(file_name, row_count)
        self.logger.info("read from {} {} cases".format(file_name, len(self.pool)))

    def read_cases(self, file_name: str, row_count=None):
        cnt = 0
        with open(file_name, "r") as inp:
            for line in inp:
                try:
                    sha256, web_domain, office_id, office_strings = line.strip().split("\t")
                    if int(office_id) == self.UNKNOWN_OFFICE_ID:
                        self.logger.debug("skip {} (unknown office id)".format(sha256))
                        continue

                    case = TPredictionCase(self.ml_model, sha256, web_domain, int(office_id), office_strings)
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

    def split(self, train_pool_path, test_pool_path):
        random.shuffle(self.pool)
        train, test = train_test_split(self.pool, test_size=0.2)
        self.write_pool(train, train_pool_path)
        self.write_pool(test, test_pool_path)
        self.ml_model.logger.info("train size = {}, test size = {}".format(len(train), len(test)))

    def build_toloka_pool(self, test_y_pred, output_path, write_tsv=True):
        assert len(self.pool) == len(test_y_pred)

        with open(output_path, "w") as outp:
            case: TPredictionCase
            cnt = 0
            if write_tsv:
                tsv_writer = csv.writer(outp, delimiter="\t")
            for case, (office_id, pred_proba) in zip(self.pool, test_y_pred):
                if case.true_office_id == office_id:
                    continue

                office_hypots = list()
                hypots = set([office_id])
                office_hypots.append({
                    'hypot_office_id': office_id,
                    'hypot_office_name': self.ml_model.office_index.get_office_name(office_id),
                    "weight": round(float(pred_proba), 4),
                    }
                )

                if case.true_office_id is not None:
                    hypots.add(case.true_office_id)
                    office_hypots.append( {
                        "hypot_office_id":  case.true_office_id,
                        "hypot_office_name": self.ml_model.office_index.get_office_name(case.true_office_id),
                        "weight": 1,
                        }
                    )

                for o in self.ml_model.office_index.get_offices_by_web_domain(case.web_domain):
                    if o not in hypots:
                        office_hypots.append({
                            "hypot_office_id": o,
                            "hypot_office_name": self.ml_model.office_index.get_office_name(o),
                            "weight": 0,
                        })

                office_strings = json.loads(case.office_strings)
                rec = {
                    "INPUT:sha256":  case.sha256,
                    "INPUT:web_domain": case.web_domain,
                    "INPUT:web_domain_title": self.ml_model.office_index.web_sites.get_title_by_web_domain(case.web_domain),
                    'INPUT:doc_title': office_strings.get('title', ''),
                    'INPUT:doc_roles': ";".join(office_strings.get('roles', [])),
                    'INPUT:doc_departments': ";".join(office_strings.get('departments', [])),
                    'INPUT:office_hypots': json.dumps(  office_hypots, ensure_ascii=False)
                }
                if not write_tsv:
                    outp.write("{}\n".format(json.dumps(rec, ensure_ascii=False)))
                else:
                    if cnt == 0:
                        tsv_writer.writerow(list(rec.keys()))
                    tsv_writer.writerow(list(rec.values()))
                    cnt += 1

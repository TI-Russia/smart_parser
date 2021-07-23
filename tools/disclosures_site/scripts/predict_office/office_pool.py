import json


class TPredictionCase:
    def __init__(self, ml_model=None, sha256=None, web_domain=None, true_office_id=None, office_strings=None):
        self.ml_model = ml_model
        self.sha256 = sha256
        self.office_strings = office_strings
        self.web_domain = web_domain
        self.true_office_id = true_office_id

        self.text = self.get_text_from_office_strings()
        self.true_region_id = ml_model.office_index.get_office_region(self.true_office_id)

    def get_text_from_office_strings(self):
        if self.office_strings is None or len(self.office_strings) == 0:
            return ""
        office_strings = json.loads(self.office_strings)
        text = ""
        title = office_strings['title']
        if title is not None and len(title) > 0:
             text += office_strings['title'] + " "
        for t in office_strings['roles']:
            if len(t) > 0:
                text += t + " "
        for t in office_strings['departments']:
            if len(t) > 0:
                text += t + " "
        return text.strip()

    def from_json(self, js):
        js = json.loads(js)
        self.sha256 = js['sha256']
        self.web_domain = js['web_domain']
        self.true_office_id = js['true_office_id']
        self.office_strings = js['office_strings']
        self.true_region_id = self.ml_model.office_index.get_office_region(self.true_office_id)
        self.text = self.get_text_from_office_strings()

    def to_json(self, js):
        js = {
            'sha256': self.sha256,
            'web_domain': self.web_domain,
            'true_office_id': self.true_office_id,
            'office_strings': self.office_strings
        }
        return json.dumps(js, ensure_ascii=False)

    def get_learn_target(self):
        if self.ml_model.learn_target_is_office:
            return self.true_office_id
        else:
            assert self.ml_model.learn_target_is_region
            return self.true_region_id

#select d.sha256, f.web_domain, d.office_id from declarations_declarator_file_reference f join declarations_source_document d on d.id = f.source_document_id  into  outfile "/tmp/docs.txt";
#mv "/tmp/docs.txt" ~/tmp/docs_and_titles
#cd ~/tmp/docs_and_titles
#cut -f 1  docs.txt >docs.txt.id
#python3 ~/smart_parser/tools/smart_parser_http/smart_parser_client.py --action office_strings --sha256-list docs.txt.id > docs_office_strings.txt
#paste docs.txt docs_office_strings.txt >office_declarator_pool.txt

class TOfficePool:
    def __init__(self, ml_model, file_name: str, row_count=None):
        self.pool = list()
        self.ml_model = ml_model
        self.logger = ml_model.logger
        self.read_cases(file_name, row_count)
        self.delete_deterministic_web_domains()
        self.logger.info("read from {} {} cases".format(file_name, len(self.pool)))

    def check_uniq_trigram_heuristic(self):
        tp = 0
        fp = 0
        case: TPredictionCase
        for case in self.pool:
            heuristic_office_id = case.check_uniq_trigram()
            if heuristic_office_id is not None:
                if case.true_office_id == heuristic_office_id:
                    tp += 1
                else:
                    heuristic_office_id = case.check_uniq_trigram()
                    self.logger.debug("error uniq trigram doc {} true_office={} ( id = {} ) "
                                      "predicted={} (id = {} )".format(
                        case.sha256,
                        self.ml_model.office_index.get_office_name(case.true_office_id), case.true_office_id,
                        self.ml_model.office_index.get_office_name(heuristic_office_id), heuristic_office_id))
                    fp += 1
        self.logger.info("check_uniq_trigram_heuristic tp={}, fp={}, prec = {}".format(tp, fp, tp/(tp+fp+0.0000000001)))

    def read_cases(self, file_name: str, row_count=None):
        cnt = 0
        with open(file_name, "r") as inp:
            for line in inp:
                try:
                    sha256, web_domain, office_id, office_strings = line.strip().split("\t")
                    case = TPredictionCase(self.ml_model, sha256, web_domain, int(office_id), office_strings)
                    if len(case.text) == 0:
                        self.logger.debug("skip {} (empty text)".format(sha256))
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

    def delete_deterministic_web_domains(self):
        new_pool = list()
        for c in self.pool:
            if c.web_domain in self.ml_model.office_index.deterministic_web_domains:
                continue
            new_pool.append(c)
        self.pool = new_pool
        self.logger.info("leave only {} after deterministic web domain filtering".format(len(self.pool)))

    def build_toloka_pool(self, test_y_pred, output_path):
        assert len(self.pool) == len(test_y_pred)

        with open(output_path, "w") as outp:
            case: TPredictionCase
            for case, (pred_target, pred_proba) in zip(self.pool, test_y_pred):
                rec = {
                    "status": ("positive" if case.get_learn_target() == pred_target else "negative"),
                    "true_office_id": case.true_office_id,
                    "true_office_name": self.ml_model.office_index.get_office_name(case.true_office_id),
                    "true_region_id": case.true_region_id,
                    "doc_title": case.text,
                    "sha256": case.sha256,
                    "web_domain": case.web_domain,
                    "pred_proba": float(pred_proba)
                }
                if self.ml_model.learn_target_is_office:
                    rec['pred_office_name'] = self.ml_model.office_index.get_office_name(pred_target)
                    rec['pred_office_id'] = pred_target
                else:
                    rec['pred_region_id'] = pred_target
                outp.write("{}\n".format(json.dumps(rec, ensure_ascii=False)))

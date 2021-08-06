from scripts.predict_office.office_index import TOfficeIndex
from scripts.predict_office.office_pool import TOfficePool, TPredictionCase
from sklearn.metrics import accuracy_score


class TPredictionModelBase:
    def __init__(self, args):
        self.args = args
        self.logger = args.logger
        self.office_index = TOfficeIndex(args)
        self.office_index.read()
        self.learn_target_is_office = self.args.learn_target == "office"
        self.learn_target_is_region = self.args.learn_target.startswith("region")
        self.train_pool = None

    def read_train(self):
        self.train_pool = TOfficePool(self, self.args.train_pool, row_count=self.args.row_count)
        assert len(self.train_pool.pool) > 0

    def read_test(self):
        self.test_pool = TOfficePool(self, self.args.test_pool, row_count=self.args.row_count)
        assert len(self.test_pool.pool) > 0

    def build_handmade_regions(self, pool: TOfficePool):
        regions = TRussianRegions()
        y_true = list()
        y_pred = list()
        y_pred_proba = list()
        c: TPredictionCase
        for c in pool.pool:
            pred_region_id = regions.get_region_all_forms(c.text)
            if pred_region_id is None:
                pred_region_id = -1
            y_pred_proba.append((pred_region_id, 1))
            y_pred.append(pred_region_id)
            y_true.append(c.true_region_id)
        self.logger.info("accuracy = {} pool size = {}".format(accuracy_score(y_true, y_pred), len(y_true)))
        return y_pred_proba

    def get_learn_target_count(self):
        if self.learn_target_is_office:
            return len(self.office_index.ml_office_id_2_office_id)
        else:
            assert self.learn_target_is_region
            return 111

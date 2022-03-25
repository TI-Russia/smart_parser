from predict_office.office_index import TOfficePredictIndex
from predict_office.office_pool import TOfficePool
from predict_office.prediction_case import TPredictionCase

from sklearn.metrics import accuracy_score


class TPredictionModelBase:
    def __init__(self, logger, office_index_path, model_path, create_model: bool, work_pool_path=None, row_count=None):
        self.logger = logger
        self.model_path = model_path
        self.office_index = TOfficePredictIndex(logger, office_index_path)
        self.office_index.read()
        self.inner_ml_model = None
        self.create_model = create_model
        if not create_model:
            self.inner_ml_model = self.load_model()
        if work_pool_path is None:
            self.work_pool = None
        else:
            self.work_pool = TOfficePool(self.logger, office_index=self.office_index)
            self.work_pool.read_cases(work_pool_path, row_count=row_count)
            assert len(self.work_pool.pool) > 0


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
        return len(self.office_index.ml_office_id_2_office_id)

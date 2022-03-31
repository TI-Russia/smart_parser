from predict_office.office_pool import TOfficePool
from predict_office.prediction_case import TPredictionCase
from common.logging_wrapper import setup_logging
from predict_office.read_office_from_title import TOfficeFromTitle, TTitleParseResult
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-pool', dest="input_pool")
    parser.add_argument('--output-toloka-file', dest="output_toloka_file")
    parser.add_argument('--output-automatic-file', dest="output_automatic_file")
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    logger = setup_logging("manage_pool")
    pool = TOfficePool(logger)
    pool.read_cases(args.input_pool)
    case: TPredictionCase
    cnt = 0
    toloka_pool = list()
    automatic_pool = list()
    parser = TOfficeFromTitle(logger)
    for case in pool.pool:
        cnt += 1
        w: TTitleParseResult
        w = parser.parse_title(case)
        if w is None:
            logger.debug("cannot parse {}".format(case.sha256))
        else:
            #print ("{}".format(json.dumps(parser.to_json(), indent=4, ensure_ascii=False)))
            #print(parser.org_name)
            if w.weight > 0.5:
                automatic_pool.append(case)
                case.true_office_id = w.office.office_id
            else:
                toloka_pool.append(case)
            logger.debug("{}\t{}\t{}\t=>{}:{}".format(w.office.office_id, w.office.name, w.org_name,
                                          w.weight, ",".join(w.common_words)))

    TOfficePool.write_pool(toloka_pool, args.output_toloka_file)
    TOfficePool.write_pool(automatic_pool, args.output_automatic_file   )


if __name__ == '__main__':
    main()

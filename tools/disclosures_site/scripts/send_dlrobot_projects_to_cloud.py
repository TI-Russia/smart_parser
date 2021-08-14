import shutil
import os
import argparse
import logging


def setup_logging(logfilename):
    logger = logging.getLogger("backuper")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = logging.FileHandler(logfilename, "a+", encoding="utf8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)
    return logger


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-ctime", dest='max_ctime', required=True, type=int, help="max ctime of an input folder")
    parser.add_argument("--processed-projects-folder", dest='processed_projects_folder', required=True)
    parser.add_argument("--update-folder", dest='update_folder', required=True)
    parser.add_argument("--output-cloud-folder", dest='output_cloud_folder', required=True)
    return parser.parse_args()


def create_tar_file(logger, processed_projects_folder, max_ctime):
    tmp_folder = "dlrobot.{}".format(max_ctime)
    os.mkdir(tmp_folder)
    with os.scandir(processed_projects_folder) as it:
        for entry in it:
            if entry.is_dir() and entry.stat().st_ctime < max_ctime:
                result_folder = os.path.join(processed_projects_folder, entry.name, "result")
                logger.info("rm folder {} ".format(result_folder))
                shutil.rmtree(result_folder, ignore_errors=True)

                logger.info("move {} {}".format(entry.name, tmp_folder))
                shutil.move(os.path.join(processed_projects_folder, entry.name), tmp_folder)
    tar_file = "processed_projects.tar.gz"
    cmd = "tar cfz {} {}".format(tar_file, tmp_folder)
    logger.info(cmd)
    os.system(cmd)

    logger.info("remove {}".format(tmp_folder))
    shutil.rmtree(tmp_folder, ignore_errors=True)
    return tar_file


def main(args):
    logger = setup_logging("backuper.log")
    assert (os.path.exists(args.output_cloud_folder))
    output_folder = os.path.join(args.output_cloud_folder, str(args.max_ctime))
    logger.info("create folder {}".format(output_folder))
    os.mkdir(output_folder)

    os.chdir(args.update_folder)
    logger.info("copy dlrobot_human.dbm to {}".format(output_folder))
    os.system("cat dlrobot_human.dbm | gzip -c >dlrobot_human.dbm.gz")
    shutil.move("dlrobot_human.dbm.gz", output_folder)

    central_log_base_name = "dlrobot_central.log"
    central_log = os.path.join(args.processed_projects_folder, "..", central_log_base_name)
    logger.info("copy {} to {}".format(central_log, output_folder))
    shutil.copy2(central_log, output_folder)
    os.system("gzip {}".format(os.path.join(output_folder, central_log_base_name)))

    tar_file = create_tar_file(logger, args.processed_projects_folder, args.max_ctime)
    logger.info("move {} to {}".format(tar_file, output_folder))
    shutil.move(tar_file, output_folder)

    logger.info("all done")


if __name__ == '__main__':
    args = parse_args()
    main(args)

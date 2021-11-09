class DLROBOT_HTTP_CODE:
    NO_MORE_JOBS = 530
    TOO_BUSY = 531


class DLROBOT_HEADER_KEYS:
    WORKER_HOST_NAME = "worker_host_name"
    EXIT_CODE= "exitcode"
    PROJECT_FILE = "dlrobot_project_file_name"
    CRAWLING_TIMEOUT = "dlrobot_project_crawling_timeout"


class TTimeouts:
    # must have "_TIMEOUT" postfix for testing purposes
    MAIN_CRAWLING_TIMEOUT = 3 * 60 * 60  # 3h
    WAIT_CONVERSION_TIMEOUT = 30 * 60  # 30m
    EXPORT_FILES_TIMEOUT = 30 * 60  # 30m to export files
    TAR_AND_TRANSFER_TIMEOUT = 20 * 60  # 20 minutes to send data back to central
    DELETE_ABANDONED_FOLDER_TIMEOUT = 60 * 60

    @staticmethod
    def save_timeouts():
        return dict((x, TTimeouts.__dict__[x]) for x in dir(TTimeouts) if x.endswith("TIMEOUT"))

    @staticmethod
    def set_timeouts(timeout):
        for x in dir(TTimeouts):
            if x.endswith("TIMEOUT"):
                setattr(TTimeouts, x, timeout)

    @staticmethod
    def restore_timeouts(timeouts):
        for k,v in timeouts.items():
            setattr(TTimeouts, k, v)

    @staticmethod
    def get_kill_timeout_in_worker(crawling_timeout):
        return crawling_timeout + TTimeouts.WAIT_CONVERSION_TIMEOUT + TTimeouts.EXPORT_FILES_TIMEOUT

    @staticmethod
    def get_kill_timeout_in_central(crawling_timeout):
        return TTimeouts.get_kill_timeout_in_worker(crawling_timeout) + \
               TTimeouts.TAR_AND_TRANSFER_TIMEOUT

    @staticmethod
    def get_timeout_to_delete_files_in_worker(crawling_timeout):
        return TTimeouts.get_kill_timeout_in_central(crawling_timeout) + TTimeouts.DELETE_ABANDONED_FOLDER_TIMEOUT




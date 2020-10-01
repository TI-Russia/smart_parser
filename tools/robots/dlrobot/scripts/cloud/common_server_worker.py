class DLROBOT_HTTP_CODE:
    NO_MORE_JOBS = 530
    TOO_BUSY = 531


class  TTimeouts:
    MAIN_CRAWLING_TIMEOUT = 3*60*60  # 3h
    WAIT_CONVERSION_TIMEOUT = 30*60  # 30m

    # 30m # may be additional 30 min to export files, it makes 4h
    MAX_EXPORT_ESTIMATION_TIME = 30 * 60

    # after this timeout(4h) dlrobot.py must be stopped and the results are not considered
    OVERALL_HARD_TIMEOUT_IN_WORKER =  MAIN_CRAWLING_TIMEOUT + WAIT_CONVERSION_TIMEOUT + MAX_EXPORT_ESTIMATION_TIME

    #add 20 minutes to send data back to central
    OVERALL_HARD_TIMEOUT_IN_CENTRAL = OVERALL_HARD_TIMEOUT_IN_WORKER + 20*60
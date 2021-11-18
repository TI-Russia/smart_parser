import urllib.request
import urllib.parse
import os
import time
import telegram_send
import logging
import logging.handlers
import datetime
import pytz
import ssl

# see smart_parser/tools/disclosures_site/scripts/etc/systemd/system/check_disclosures_health.service
# for installing this script as a unix service
MOSCOW_TIME_ZONE = pytz.timezone("Europe/Moscow")


def setup_logging(logfilename="health_chk.log"):
    logger = logging.getLogger("health_chk")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = logging.handlers.RotatingFileHandler(logfilename, "a+", encoding="utf8", maxBytes=1024*1024)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger


LOGGER = setup_logging()


LAST_MESSAGES = dict()


def send_message(event_id, message):
    LOGGER.debug("{} {}".format(event_id, message))
    global LAST_MESSAGES
    last_send_time, last_send_message = LAST_MESSAGES.get(event_id, (0, ""))
    if last_send_message == message:
        if time.time() - last_send_time < 60 * 60: # the same message was sent within an hour
            return
    if event_id == "alive":
        for (last_send_time, _) in LAST_MESSAGES.values():
            if time.time() - last_send_time < 60 * 60 * 24:  # the was a message within 24 hours
                return

    LAST_MESSAGES[event_id] = (time.time(), message)

    try:
        telegram_send.send(messages=[message])
    except Exception as e:
        LOGGER.error("cannot send to telegram")


def check_ping(hostname):
    response = os.system("ping -c 1 {} >/dev/null".format(hostname))
    # and then check the response...
    return response == 0


def read_morda(url):
    try:
        f = urllib.request.urlopen(url, timeout=30, context=ssl.SSLContext())
        s = f.read().decode('utf-8')
        return len(s) > 100
    except Exception as exp:
        return False


def check_pdf_converter_server():
    try:
        f = urllib.request.urlopen('http://c.disclosures.ru:8091/ping', timeout=30)
        s = f.read().decode('utf-8')
        return s == "yes"
    except Exception as exp:
        return False


def main():
    url = 'http://disclosures.ru'
    ping_flag = True
    morda_flag = True
    pdf_conv_srv_flag = True
    last_time_check_morda = 0
    last_time_check_pdf_conv_src = 0
    last_time_alive = 0
    send_message("start", "disclosures checker start")

    ping_period = 60 * 5
    http_read_period = 60 * 30
    alive_period = 60 * 60 * 24
    #ping_period = 10
    #http_read_period = 20

    while True:
        time.sleep(ping_period)
        if not check_ping('google.com'):
            LOGGER.error("cannot access google, internet is down, I am helpless")
            continue

        if not check_ping('disclosures.ru'):
            send_message("ping", "disclosures.ru is not reached, ping failed")
            ping_flag = False
        else:
            if not ping_flag:
                send_message("ping",  "disclosures.ru ping succeeded")
                ping_flag = True

            if not morda_flag or time.time() - last_time_check_morda  >= http_read_period:
                last_time_check_morda = time.time()
                if read_morda(url):
                    if not morda_flag:
                        send_message("morda",  "disclosures.ru main page access restored")
                    morda_flag = True
                else:
                    send_message("morda", "disclosures.ru main page access failed")
                    morda_flag = False

            if not pdf_conv_srv_flag or time.time() - last_time_check_pdf_conv_src >= http_read_period:
                last_time_check_pdf_conv_src = time.time()
                if check_pdf_converter_server():
                    if not pdf_conv_srv_flag:
                        send_message("pdf_conv_srv", "pdf conversion server access restored")
                    pdf_conv_srv_flag = True
                else:
                    send_message("pdf_conv_srv", "pdf conversion server access failed")
                    pdf_conv_srv_flag = False

            if time.time() - last_time_alive >= alive_period:
                dt_time = datetime.datetime.now(tz=MOSCOW_TIME_ZONE)
                if 22 > dt_time.hour > 8:
                    # do not send at nights "alive" message
                    send_message("alive", "check_disclosures_health.py is alive")


if __name__ == "__main__":
    main()


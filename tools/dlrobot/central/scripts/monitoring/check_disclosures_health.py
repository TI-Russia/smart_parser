from common.logging_wrapper import setup_logging

import urllib.request
import urllib.parse
import os
import time
import telegram_send
import datetime
import pytz
import ssl
import argparse
import json

# see smart_parser/tools/disclosures_site/scripts/etc/systemd/system/check_disclosures_health.service
# for installing this script as a unix service
MOSCOW_TIME_ZONE = pytz.timezone("Europe/Moscow")


def check_ping(url):
    response = os.system("ping -c 1 {} >/dev/null".format(url))
    # and then check the response...
    return response == 0


def make_http_get(url, must_contain_substring=None):
    f = urllib.request.urlopen(url, timeout=30, context=ssl.SSLContext())
    s = f.read().decode('utf-8')
    if must_contain_substring is not None:
        return s.find(must_contain_substring) != -1
    return len(s) > 100


def check_backend_service(url):
    url = os.path.join(url, "ping").replace('\\', '/')
    f = urllib.request.urlopen(url, timeout=30)
    s = f.read().decode('utf-8').strip()
    return s == "yes" or s == "pong"


def is_day_time():
    dt_time = datetime.datetime.now(tz=MOSCOW_TIME_ZONE)
    return 8 < dt_time.hour < 22


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--heart-beat", dest="heart_beat", type=int, default=60*5, help="common timeout in seconds")
    parser.add_argument("--monitoring-name", dest="monitoring_name")
    parser.add_argument("--message-repeat-rate", dest="repeat_rate", type=int, default=60 * 60)
    parser.add_argument("--config", dest="config",
                        default=os.path.join(os.path.dirname(__file__), 'check_disclosures_heath.json'),
                        help="path to json config" )
    args = parser.parse_args()
    return args


class TCheckState:
    def __init__(self):
        self.name = None
        self.typ = None
        self.state = None
        self.last_checked_time = None
        self.parent = None
        self.url = None
        self.timeout = None
        self.check_method =  None
        self.must_contain_substring = None

    @staticmethod
    def read_from_json(parent, js):
        c = TCheckState()
        c.typ = js['type']
        if c.typ == "ping":
            c.check_method =  check_ping
        elif c.typ == "http_get":
            c.check_method = make_http_get
        elif c.typ == "ping_backend":
            c.check_method = check_backend_service
        elif c.typ == "alive":
            c.check_method = None
        else:
            raise Exception("unknown method {}".format(c.typ))
        c.url = js['url']
        c.timeout = js['timeout']
        c.parent = parent
        c.name = js.get('name')
        c.must_contain_substring = js.get('must_contain_substring')
        return c

    def check_timeout(self):
        return self.last_checked_time is None or time.time() - self.last_checked_time >= self.timeout

    def check_state(self):
        if self.typ == "alive" and not is_day_time():
            # do not send "alive" message at nights
            return

        if not self.check_timeout():
            return self.state
        self.last_checked_time = time.time()
        if self.typ == "alive":
            self.parent.send_alert_message(self.name, self.typ, self.url, True)
        else:
            try:
                if self.must_contain_substring is not None:
                    new_state = self.check_method(self.url, self.must_contain_substring)
                else:
                    new_state = self.check_method(self.url)
            except Exception as exp:
                self.parent.logger.error("failed {} {}, exception={}".format(self.typ, self.url, exp))
                return
            if not new_state or new_state != self.state:
                self.parent.send_alert_message(self.name, self.typ , self.url, new_state)
            self.state = new_state


class TMonitoring:
    def __init__(self):
        self.args = parse_args()
        self.logger = setup_logging("check_disclosures_heath")
        self.last_messages = dict()
        self.checks = list()
        with open(self.args.config) as inp:
            for c in json.load(inp):
                self.checks.append( TCheckState.read_from_json(self, c))

    def send_alert_message(self, name, method_name, url, state):
        if name is None:
            name = self.args.monitoring_name
        message = "{} {} {} {}".format(name, url, method_name,  state)
        event_id = "{} {}".format(method_name, url)
        self.logger.debug(message)
        last_send_time, last_send_alert_message = self.last_messages.get(event_id, (0, ""))
        if last_send_alert_message == message:
            if time.time() - last_send_time < self.args.repeat_rate: # the same message was sent within an hour
                return
        self.last_messages[event_id] = (time.time(), message)
        try:
            telegram_send.send(messages=[message])
        except Exception as e:
            self.logger.error("cannot send to telegram")

    def check_all(self):
        if not check_ping('google.com'):
            self.logger.error("cannot access google, internet is down, I am helpless")
            return
        for c in self.checks:
            c.check_state()

    def main(self):
        self.send_alert_message(None, "start", "", True)
        while True:
            self.check_all()
            time.sleep(self.args.heart_beat)


if __name__ == "__main__":
    m = TMonitoring()
    m.main()



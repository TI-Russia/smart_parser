import smtplib, ssl
import urllib.request
import urllib.parse
import os
import time
import telegram_send

LAST_MESSAGES = dict()
def send_email (event_id, to_addr, message):
    global LAST_MESSAGES
    last_send_time, last_send_message = LAST_MESSAGES.get(event_id, (0,""))
    if last_send_message == message:
        if time.time() - last_send_time < 60*60: # the same message was sent within an hour
            return
    LAST_MESSAGES[event_id] = (time.time(), message)
    print("send email {}:{}".format(event_id, message))
    smtp_server = "smtp.gmail.com"
    port = 587  # For starttls
    sender_email = "disclosures.ru@gmail.com"
    with open("example.txt", "r") as inp:
        text_cut = inp.read()[1024:1034]

    context = ssl.create_default_context()

    try:
        server = smtplib.SMTP(smtp_server, port)
        server.starttls(context=context) # Secure the connection
        server.login(sender_email, text_cut)
        server.sendmail(sender_email, to_addr, message)
    except Exception as e:
        print(e)
    finally:
        server.quit()

    try:
        telegram_send.send(messages=[message])
    except Exception as e:
        print(e)


def check_ping(hostname):
    response = os.system("ping -c 1 " + hostname)
    # and then check the response...
    return response == 0


def read_morda(url):
    try:
        f = urllib.request.urlopen(url, timeout=30)
        s = f.read().decode('utf-8')
        return len(s) > 100
    except Exception as exp:
        return False

def check_pdf_converter_server():
    try:
        f = urllib.request.urlopen('http://disclosures.ru:8091/ping', timeout=30)
        s = f.read().decode('utf-8')
        return s == "yes"
    except Exception as exp:
        return False


def main():
    url = 'http://disclosures.ru'
    admin_email = "alexey.sokirko@gmail.com"
    ping_flag = True
    morda_flag = True
    pdf_conv_srv_flag = True
    last_time_check_morda = 0
    last_time_check_pdf_conv_src = 0
    send_email("start", admin_email, "disclosures checker start")
    #assert read_morda(url)
    #assert check_pdf_converter_server()

    ping_period = 60*5
    http_read_period = 60 * 30
    #ping_period = 10
    #http_read_period = 20
    while True:
        time.sleep(ping_period)
        if not check_ping('google.com'):
            continue

        if not check_ping('disclosures.ru'):
            send_email("ping", admin_email, "disclosures.ru is not reached, ping failed")
            ping_flag = False
        else:
            if not ping_flag:
                send_email("ping", admin_email, "disclosures.ru ping succeeded")
                ping_flag = True

            if not morda_flag or time.time() - last_time_check_morda  >= http_read_period:
                last_time_check_morda = time.time()
                if read_morda(url):
                    if not morda_flag:
                        send_email("morda", admin_email, "disclosures.ru main page access restored")
                    morda_flag = True
                else:
                    send_email("morda", admin_email, "disclosures.ru main page access failed")
                    morda_flag = False

            if not pdf_conv_srv_flag or time.time() - last_time_check_pdf_conv_src >= http_read_period:
                last_time_check_pdf_conv_src = time.time()
                if check_pdf_converter_server():
                    if not pdf_conv_srv_flag:
                        send_email("pdf_conv_srv", admin_email, "pdf conversion server access restored")
                    pdf_conv_srv_flag = True
                else:
                    send_email("pdf_conv_srv", admin_email, "pdf conversion server access failed")
                    pdf_conv_srv_flag = False


if __name__ == "__main__":
    main()


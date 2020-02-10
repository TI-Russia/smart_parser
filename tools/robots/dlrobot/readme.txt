1. download https://github.com/mozilla/geckodriver/releases/tag/v0.26.0 (linux or windows)
2. copy geckodriver to  PATH
3. install Firefox
4. run "python check_selenium.py" to test selenium (firefox)
5. site:ozerny.ru  inanchor:доходах filter=0

============
0. bagaev  
  ушел документ с 15 примерами (три раза?)
1. проверить mil.txt
2. проверить тульсткий суды (там  одна и та жа страница), имееет разный сksum
3. удалить кэш под линуксом.
4. сделать stats json
===
1. mos.ru уменьшился сильно, проверяем более слабый check_download_text_not_html
==
1. почему скачут smart (4-5) ?
2. суд ушел (сравниться с олдтаймером)
===
b/tools/robots/dlrobot/tests/minprom.txt.clicks.stats
@@ -1,121 +1,56 @@
 [
     {
-        "people_count_sum": 4376,
-        "files_count": 23
+        "people_count_sum": 0,
+        "files_count": 10
     },
====

--- a/tools/robots/dlrobot/tests/mos.txt.clicks.stats
+++ b/tools/robots/dlrobot/tests/mos.txt.clicks.stats
@@ -1,231 +1,56 @@
 [
     {
-        "people_count_sum": 1276,
-        "files_count": 45
+        "people_count_sum": 0,
+        "files_count": 10
     },

===
2020-02-02 11:54:08,284 - dlrobot_logger - DEBUG - find_links_with_selenium url=https://www.mos.ru/mka/anticorruption/svedeniya-o-dokhodakh-raskhodakh-ob-imushestve-i-obyazatelstvakh-imushestvennogo-kharaktera/ , function=check_documents
    2020-02-02 11:54:08,296 - dlrobot_logger - ERROR - cannot download page url=https://www.mos.ru/mka/anticorruption/svedeniya-o-dokhodakh-raskhodakh-ob-imushestve-i-obyazatelstvakh-imushestvennogo-kharaktera/ while find_links, exception=Message: Tried to run command without establishing a connection


===
Опять вылетел mos.txt (без сообщений об ошибок)

==
1. Зависло на 
/usr/lib/libreoffice/program/soffice.bin --headless --convert-to docx:MS Word 2007 XML result/adminkr.ru/89.tmp.html

2. === download all declarations =========
found 53 files, exported 27 files to result/sibay.bashkortostan.ru
Error: source file could not be loaded

3.  cannot query (HEAD) url=http://admuni.ru/2018/03/  exception=too many times to get headers that caused exceptions
    просто включить в тесты?

5. tambov.gov.ru
   cannot download /assets/files/komprofcor/tablica-svedeniya-ob-uchastnikah-na-1-iyulya-2019-goda.docx: [Errno 13] Permission denied: '/assets'
    base="/"

===
C:\…arser\smart_parser\tools\robots\dlrobot>curl -I http://admuni.ru/statistics.html
HTTP/1.1 403 Forbidden
Server: nginx/ihead.ru
Date: Mon, 03 Feb 2020 19:22:46 GMT
Content-Type: text/html; charset=UTF-8
Connection: keep-alive
Keep-Alive: timeout=20

===
-rw-rw-r-- 1 sokirko sokirko      71 Feb  3 01:13 ksl.spb.sudrf.ru.txt.clicks.stats
-rw-rw-r-- 1 sokirko sokirko      71 Feb  3 01:24 pfrf.ru.txt.clicks.stats
-rw-rw-r-- 1 sokirko sokirko      71 Feb  3 01:25 service.nalog.ru.txt.clicks.stats
-rw-rw-r-- 1 sokirko sokirko      71 Feb  3 01:44 svost.gosnadzor.ru.txt.clicks.stats

===
1. Запустить тесты
2.  запустил all.b/bruhoveckaya.ru.txt.log
   Возникате 503 через 40 минут (dlrobot.log.ddos4)
3. Мид сломался? Изучить mid.log

===
Compile smart_parser on oldtimer
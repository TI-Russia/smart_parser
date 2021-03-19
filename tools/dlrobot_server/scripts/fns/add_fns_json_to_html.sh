cd ~/tmp
#download nalog_12_15.zip from dropbox
unzip nalog_12_15.zip
find nalog -name '*.html' | xargs -P 4 -n 1 python3 ~/smart_parser/tools/dlrobot_server/scripts/fns/add_fns_json_to_html.py
find nalog -name '*.json' | xargs rm -rf
zip -r nalog_html.zip nalog
python3 ~/smart_parser/tools/dlrobot_server/scripts/fns/unzip_archive.py --archive nalog_html.zip --web-domain service.nalog.ru

server {
    server_name disclosures.ru;

    location = /favicon.ico { access_log off; log_not_found off; }
    location /static/ {
        alias /home/sokirko/smart_parser/tools/disclosures_site/disclosures/static/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
    } 

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/disclosures.ru/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/disclosures.ru/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot


}

server {
    if ($host = disclosures.ru) {
        return 301 https://$host$request_uri;
    } # managed by Certbot


    server_name disclosures.ru;


    listen 80;
    return 404; # managed by Certbot


}

# remove 'www'
server {
    listen 443 ssl;
    listen 80;
    server_name www.disclosures.ru;
    return 301 $scheme://disclosures.ru$request_uri;

}


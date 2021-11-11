SITE_URL=$1
MAX_DEPTH=5
#SITE_URL=https://voronezh-city.ru/
date
nonhtml='mp4,rar,docx,doc,jpg,JPG,png,PNG,css,js,pdf,xls,xlsx,zip,7z,bmp,gif,rtf,pptx,PPTX,avi'
wget --force-html --recursive  --level $MAX_DEPTH  --no-remove-listing --timestamping --force-directories  --adjust-extension --reject $nonhtml -e robots=off $SITE_URL
date

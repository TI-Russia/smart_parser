START_YEAR=2011
LAST_YEAR=2019
for year in `seq $START_YEAR $LAST_YEAR`; do
  python3 manage.py car_brand_report --settings disclosures.settings.prod --year $year >car_brand_$year.txt
done

python3 make_html.py  --start-year $START_YEAR --last-year $LAST_YEAR


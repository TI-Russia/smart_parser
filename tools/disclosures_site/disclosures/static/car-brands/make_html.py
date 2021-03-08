from collections import defaultdict
from declarations.car_brands import CAR_BRANDS
import sys
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year",  dest="start_year", type=int, default=2011)
    parser.add_argument("--last-year", dest="last_year", type=int, default=2019)
    return parser.parse_args()


def build_freq_dict_by_years(args):
    freq_dict_by_years = defaultdict(list)

    for year in range(args.start_year, args.last_year + 1):
        with open("car_brand_{}.txt".format(year)) as inp:
            freq_dict = defaultdict()
            cnt = 0
            for x in inp:
                items = x.strip().split("\t")
                if len(items) == 0:
                    print("bad format: {}".format(x))
                    assert False
                v2 = items[1]
                if v2 not in freq_dict:
                    freq_dict[v2] = 1
                else:
                    freq_dict[v2] += 1
                cnt += 1
            for brand_id in CAR_BRANDS.brand_dict.keys():
                name = CAR_BRANDS.get_brand_name(brand_id)
                freq = freq_dict.get(name, 0)
                freq_perc = round(100.0 * freq /cnt, 2)
                freq_dict_by_years[brand_id].append(freq)
                freq_dict_by_years[brand_id].append(freq_perc)
    freq_dict_by_years_wo_empty = dict((k,v) for k,v in freq_dict_by_years.items() if sum(v) > 0)
    sys.stderr.write("found {} car brands\n".format(len(freq_dict_by_years_wo_empty.keys())))
    return freq_dict_by_years_wo_empty


def build_html(args, freq_dict_by_years):
    def th_wrapper(s):
        return "<th><div class=\"clickable\">{}↑↓</div></th>\n".format(s)

    with open("car-brands-by-years.html", "w") as outp:

        outp.write("""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <title>Статистика автомобильных брендов по декларациям о доходах (2011-2019)</title>
            <link rel="stylesheet" type="text/css" href="/static/style.css">
        </head>
        <body>
        <h1>Статистика автомобильных брендов по декларациям о доходах (2011-2019)</h1>
        <a href="report.html"> Описание колонок </a> <br/><br/>
        """)
        outp.write("<table id=\"statstable\" class=\"solid_table\"><tr><th>Марка</th>\n")
        for year in range(args.start_year, args.last_year + 1):
            outp.write(th_wrapper("{}<br/>(кол-во)".format(year)))
            outp.write(th_wrapper("{}<br/>(%)".format(year)))
        outp.write("</tr>\n")

        for brand_id, values in freq_dict_by_years.items():
            name = "<a href=/section?car_brands={}&sort_by=income_year&order=desc>{}</a>".format(
                brand_id, CAR_BRANDS.get_brand_name(brand_id) )
            tds = map((lambda x: "<td>{}</td>\n".format(x)),  ([name] + values))
            outp.write("<tr>{}</tr>\n".format(" ".join(tds)))
        outp.write("""
        </table></body>
        <script src="/static/sorttable.js"></script>
        <script>
            var table = document.getElementById("statstable");
            table.querySelectorAll(`th`).forEach((th, position) => {{
                th.addEventListener(`click`, evt => sortTable(position + 1));
            }});
        </script>
        </html>
        """)


def main():
    args = parse_args()
    freq_dict_by_years = build_freq_dict_by_years(args)
    build_html(args, freq_dict_by_years)


if __name__ == "__main__":
    main()

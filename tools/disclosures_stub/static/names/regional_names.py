from collections import defaultdict


if __name__ == '__main__':
    regions = defaultdict(list)
    with open("names.region.txt", "r") as inp:
        for line in inp:
            items = line.strip().split("\t")
            name, region, level, region_size,  name_freq, region_ratio = items
            regions[region].append( (float(region_ratio), name, level, int(region_size),  int(name_freq)) )
    with open("names_region.html", "w") as outp:
        outp.write("<html><table class=\"solid_table\">\n")
        outp.write("<tr><th>Регион</th><th>Региональные имена</th></tr>\n")
        for region in regions.keys():
            #print(regions[region][1])
            top_names = sorted(regions[region], reverse=True)[:50]
            regional_names = list()
            for region_ratio, name, level, region_size,  name_freq in top_names:
                if name_freq < 10:
                    break
                if level != "country-level":
                    regional_names.append(name.title())
            if len(regional_names) > 0:
                outp.write("<tr><td>{}</th><td>{}</td></tr>\n".format(
                    region,
                    ", ".join(regional_names)
                ))
        outp.write("</table></html>\n")


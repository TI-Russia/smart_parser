from usp.tree import sitemap_tree_for_homepage
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", dest="output_path", required=False, default="downloaded_sitemap_urls.txt")
    parser.add_argument("urls", nargs="*")
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()
    if len(args.urls) > 0:
        url = args.urls[0]
    else:
        url = "http://sokirko.info"
    print ("download all sitemaps from {}".format(url))
    tree = sitemap_tree_for_homepage(url)
    urls = list(tree.all_pages())
    print("write {} urls to {}".format(len(urls), args.output_path))
    with open (args.output_path, "w") as outp:
        for u in urls:\
            outp.write ("{}\n".format(u.url))



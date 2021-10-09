from common.logging_wrapper import setup_logging

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-id", dest='parent_id')
    parser.add_argument("--input-file", dest='input_file', required=True)
    parser.add_argument("--output-file", dest='output_file', required=True)
    parser.add_argument("--url-list", dest='url_list', required=False)
    parser.add_argument("--take-all-web-sites", dest='take_all_web_sites', required=False, action="store_true", default=False,
                        help="by default we skip all abandoned web sites")
    parser.add_argument("--filter-regex", dest='filter_regex', required=False)
    parser.add_argument("--replace-substring", dest='replace_substring', required=False,
                        help="for example, --action move --filter-regex '.mvd.ru$'  --replace-substring .мвд.рф")
    return parser.parse_args()

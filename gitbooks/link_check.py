import os, argparse, fnmatch, re, urllib2
from tqdm import tqdm

SIMPLE_URL_REGEX = 'http[s]?://[^)]+'
MARKDOWN_LINK_REGEX = '\[([^]]+)]\((.*?)\)'
RELATIVE_PATH_REGEX = '^(.+)/([^/]+)$'

HTTP_LINK_COUNT = 0
HTTP_LINK_ERRORS = []
RELATIVE_LINK_COUNT = 0
RELATIVE_LINK_ERRORS = []

VERBOSE = False

def setup_arg_parser():
    parser = argparse.ArgumentParser(prog='markdown link checker', description='traverse a directory structure for markdown files and validate links contained within')
    parser.add_argument('directory', help='directory to containing files to validate')
    parser.add_argument('--include-hidden', action='store_true', default=False, help='include hidden (files and dirs that start with \'.\') to search')
    parser.add_argument('--match', default='*.md', help='re pattern to find files to validate, defaults to *.md')
    parser.add_argument('--validate-website', action='store_true', default=False, help='whether to validate that an http url is alive')
    parser.add_argument('-v', action='store_true', default=False, help='enable verbose output')
    return parser

def log(msg):
    if VERBOSE:
        print(msg)

def file_list(root, include_hidden, match):
    found = []

    for path, subdirs, files in os.walk(root):
        # ignore hidden files and directories, .git gets pretty big
        if not include_hidden:
            files = [f for f in files if not f[0] == '.']
            subdirs[:] = [d for d in subdirs if not d[0] == '.']
        found.extend([os.path.join(path, f) for f in fnmatch.filter(files, match)])
    return found

def get_path(abs_path):
    return '/'.join(abs_path.split('/')[:-1]) #yuck

def validate_links(abs_file_path, validate_website):
    global HTTP_LINK_COUNT
    global HTTP_LINK_ERRORS
    global RELATIVE_LINK_COUNT
    global RELATIVE_LINK_ERRORS
    line_number = 1
    with open(abs_file_path) as f:
        for line in f:
            for match in re.findall(MARKDOWN_LINK_REGEX, line):
                log('found a link in {} line {}: {}'.format(abs_file_path, line_number, match[1]))
                if re.match(SIMPLE_URL_REGEX, match[1]):
                    HTTP_LINK_COUNT += 1
                    if validate_website:
                        req = urllib2.Request(match[1], headers={'User-Agent' : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A"})
                        con = urllib2.urlopen(req)
                        con.read()
                        status = con.getcode()
                        if status is 200:
                            log(match[1] + ' 200 OK')
                        else:
                            HTTP_LINK_ERRORS.append(match[1] + ' ' + str(status))
                elif re.match(RELATIVE_PATH_REGEX, match[1]):
                    RELATIVE_LINK_COUNT += 1
                    abs_path = os.path.abspath(os.path.join(get_path(abs_file_path), match[1]))
                    log('relative path {} converted to absolute path {}'.format(match[1], abs_path))
                    if not os.path.isfile(abs_path):
                        RELATIVE_LINK_ERRORS.append(abs_path + ' doesnt exist')
            line_number += 1

if __name__ == '__main__':
    arg_parser = setup_arg_parser()
    args = arg_parser.parse_args()
    VERBOSE = args.v
    for f in tqdm(file_list(args.directory, args.include_hidden, args.match)):
        validate_links(f, args.validate_website)

    print 'Total Links Found: {}'.format(HTTP_LINK_COUNT + RELATIVE_LINK_COUNT)
    print 'External Web Links: {}'.format(HTTP_LINK_COUNT)
    if args.validate_website:
        print 'Broken External Web Links: {}'.format(len(HTTP_LINK_ERRORS))
        for l in HTTP_LINK_ERRORS:
            print l
    else:
        print 'Broken External Web Links: SKIPPED'
    print 'Internal Links: {}'.format(RELATIVE_LINK_COUNT)
    print 'Broken Internal Links: {}'.format(len(RELATIVE_LINK_ERRORS))
    for l in RELATIVE_LINK_ERRORS:
        print l

import lxml.html
from urllib import parse
from urllib.request import urlopen
import os, logging, hashlib, dryscrape

class Network:
    def __init__(self):
        #dryscrape.start_xvfb()
        self.sessions = dict()

    @staticmethod
    def clean_url(url):
        url = parse.urlsplit(url)
        url = list(url)
        url[2] = parse.quote(url[2])
        url = parse.urlunsplit(url)

        return url

    @staticmethod
    def cache_filename(cache_dir, url):
        return os.path.join(cache_dir, hashlib.md5(url.encode('utf-8')).hexdigest()+'.html')

    def get_session(self, url):
        if url not in self.sessions:
            session = dryscrape.Session(base_url = url)
            session.set_attribute('auto_load_images', False)
            self.sessions[url] = session

        return self.sessions[url]


    def load_and_cache_html(self, url, cache_filename):

        if not os.path.isfile(cache_filename):
            logging.getLogger().debug('Cache miss - Downloading ' + url + ' to ' + cache_filename)

            session = self.get_session(url)
            session.visit(url)
            content = session.body()

            with open(cache_filename, 'w') as f:
                f.write(content)

        logging.getLogger().debug('Loading html dom from ' + cache_filename)

        with open(cache_filename, 'r') as f:
            return lxml.html.fromstring(f.read())

    def load_html(self, url):
        session = self.get_session(url)
        session.visit(url)
        content = session.body()
        return lxml.html.fromstring(content)

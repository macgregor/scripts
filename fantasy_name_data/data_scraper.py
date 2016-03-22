from lxml.cssselect import CSSSelector
from lxml.etree import tostring
from network import Network
from queue import Queue
from threading import Thread
import logging, yaml, sys, optparse

class Page:
    def __init__(self, network, url, selector, filename):
        self.url = Network.clean_url(url)
        self.network = network
        self.selector = selector
        self.filename = filename
        self.names = []

    def generate_list(self):
        collisions = -1
        while collisions < self.collision_threshold:
            names = self.fetch_names()
            collisions = self.update_names(names)
            logging.getLogger().debug('collisions: ' + str(collisions))
        self.save_names()


    def fetch_names(self):
        logging.getLogger().debug('Fetching names from ' + self.url + ' using ' + self.selector)
        matcher = CSSSelector(self.selector)
        matches = matcher(self.network.load_html(self.url))

        names = []
        if len(matches) > 0:
            for element in matches[0].getchildren():
                name = tostring(element, encoding='unicode')
                name = name.replace('<br/>', '')

                if name != '':
                    names.append(name)

        return names

    def update_names(self, names):
        collisions = 0
        for name in names:
            if name in self.names:
                collisions += 1
            else:
                self.names.append(name)
        return collisions

    def save_names(self):
        logging.getLogger().debug('Saving names list to ' + self.filename)
        with open(self.filename, 'a') as output:
            for name in self.names:
                output.write("%s\n" % name)

class Worker(Thread):
   def __init__(self, queue, collision_threshold = 1):
       Thread.__init__(self)
       self.queue = queue
       self.collision_threshold = collision_threshold

   def id(self):
       return str(threading.currentThread().ident)

   def run(self):
       while True:
           page = self.queue.get()
           collisions = -1
           try:
               names = page.fetch_names()
               collisions = page.update_names(names)
               logging.getLogger().debug(str(self.ident) + ' name collisions: ' + str(collisions))
               if collisions >= self.collision_threshold:
                  logging.getLogger().debug(str(self.ident) + ' Thread finished')
                  self.queue.task_done()
                  page.save_names()
               else:
                  self.queue.put(page)
           except Exception as e:
               logging.getLogger().exception("[" + str(self.ident) + "] Error fetching names from web page ")
               self.queue.put(page)

class Conf:
    @staticmethod
    def yaml(filename, debug=False):
        logging.getLogger().debug('Loading yaml config ' + filename)

        conf = dict()
        conf['debug'] = debug
        with open(filename, 'r') as ymlfile:
            conf['pages'] = yaml.load(ymlfile)

        logging.getLogger().debug(conf)

        return conf

    # sets up logger to go to stdout and enables debug logging when appropriate
    @staticmethod
    def setup_logger(debug):
        root = logging.getLogger()
        ch = logging.StreamHandler(sys.stdout)

        if debug:
            root.setLevel(logging.DEBUG)
            ch.setLevel(logging.DEBUG)
        else:
            root.setLevel(logging.INFO)
            ch.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        root.addHandler(ch)

    @staticmethod
    def parse_options():
        parser = optparse.OptionParser()
        parser.add_option('--config', dest='config', help='yaml config file')
        parser.add_option('-d', '--debug', dest='debug', default=False, action='store_true', help='enable debug output')

        (options, args) = parser.parse_args()

        if not options.config:
            parser.error('No config file specified')

        return options

if __name__ == '__main__':
    options = Conf.parse_options()

    Conf.setup_logger(options.debug)
    conf = Conf.yaml(options.config, options.debug)
    network = Network()
    queue = Queue()

    for x in range(4):
        worker = Worker(queue)
        # Setting daemon to True will let the main thread exit even though the workers are blocking
        worker.daemon = True
        worker.start()

    for page in conf['pages']:
        p = Page(network, page['url'], page['selector'], page['filename'])
        queue.put(p)

    queue.join()

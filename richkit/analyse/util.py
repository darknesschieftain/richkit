from os import path
import requests
import tempfile
import logging
logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)
temp_directory = tempfile.mkdtemp()


class WordMatcher(object):
    # use class vars for lazy loading
    MASTERURL = "http://www.greenteapress.com/thinkpython/code/words.txt"
    MASTERFILE = temp_directory + "/words.txt"
    WORDS = None

    @classmethod
    def fetch_words(cls, url=None):
        url = url or cls.MASTERURL

        logger.info('Fetching word list from server ...')
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(cls.MASTERFILE, 'wb') as file:
                file.write(response.content)
        else:
            logger.error('Error while downloading the word list response code %s ',str(response.status_code))

    @classmethod
    def load_words(cls):
        f = open(cls.MASTERFILE, 'r', encoding="utf8")
        lines = f.readlines()
        f.close()

        # strip whitespaces
        # only words with more than three letters are considered
        lines = [ln for ln in (ln.strip() for ln in lines) if len(ln) > 3]
        cls.WORDS = {}
        for item in lines:
            cls.WORDS[item] = None
        # cls.WORDS = set(lines)

    def __init__(self):

        if path.exists(WordMatcher.MASTERFILE):
            WordMatcher.load_words()

        if WordMatcher.WORDS is None:
            WordMatcher.fetch_words()
            WordMatcher.load_words()

    def get_num_of_words(self, domain):
        num = 0
        for word in WordMatcher.WORDS:
            if word in domain:
                num += 1
        return num

def load_alexa(limit=None):
    """
    Reads top @limit number of popular domains based on alexa.com

    """
    alexa_domains = set()
    path = "top-1m.csv"
    with open(path) as f:
        for line in f:
            line = line.strip()
            sline = line.split(',')

            if limit and int(sline[0]) > limit:
                break

            """
            sometimes the Alexa list contains full URLs, e.g.
            example.com/path; need to get rid of that for later matching
            """
            domain = (sline[1].split('/'))[0]

            """
            we want only the 2LD+TLD, else we do not know later against what we
            need to match
            """
            sld_domain = get_2ld(domain)
            alexa_domains.add(sld_domain)
            alexa_domains.add(domain)
    alexa_slds = set([get_2ld(el) for el in alexa_domains])

    return alexa_slds

def load_words(path_to_data="data/top-1m.csv"):
    TOP_1M_URL="https://github.com/mozilla/cipherscan/blob/master/top1m/top-1m.csv?raw=true"
    if path.exists(path_to_data):
        f = open(path_to_data, 'r', encoding="utf8")
        lines = f.readlines()
        f.close()
    else:
        response = requests.get(TOP_1M_URL, stream=True)
        if response.status_code == 200:
            with open(path_to_data, 'wb') as file:
                file.write(response.content)
        else:
            logger.error('Error while downloading the TOP 1M URL list status code : %s',str(response.status_code))
    # strip whitespaces
    # only words with more than three letters are considered
    lines = [ln for ln in (ln.strip() for ln in lines) if len(ln) > 3]
    words = set(lines)
    return words

class TldMatcher(object):
    # use class vars for lazy loading
    MASTERURL = "https://publicsuffix.org/list/effective_tld_names.dat"
    MASTERFILE = temp_directory +"/effective_tld_names.dat"

    TLDS = None
    No_TLDS = None

    @classmethod
    def fetch_tlds(cls, url=None):
        url = url or cls.MASTERURL

        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(cls.MASTERFILE, 'wb') as file:
                file.write(response.content)
        else:

            logger.error('Error while downloading the Public Suffix List status code %s ',str(response.status_code))


    @classmethod
    def load_tlds(cls):
        try:
            f = open(cls.MASTERFILE, 'r', encoding="utf8")
            lines = f.readlines()
        except FileNotFoundError as e:
            logger.exception('File not readable, not found %s', e)
            f.close()
        f.close()

        # strip comments and blank lines
        stripped_lines = [ln for ln in (ln.strip() for ln in lines) if len(ln) and ln[:2] != '//']

        excluded_lines = [ln.strip('!') for ln in (ln.strip() for ln in lines) if len(ln) and ln[:1] == '!']

        cls.TLDS = set(stripped_lines)
        cls.No_TLDS = set(excluded_lines)

    def __init__(self):

        if path.exists(TldMatcher.MASTERFILE):
            TldMatcher.load_tlds()

        if TldMatcher.TLDS is None:
            TldMatcher.fetch_tlds()
            TldMatcher.load_tlds()

    def get_tld(self, url):
        best_match = None
        chunks = url.split('.')

        for start in range(len(chunks) - 1, -1, -1):
            test = '.'.join(chunks[start:])
            startest = '.'.join(['*'] + chunks[start + 1:])

            if test in TldMatcher.TLDS or startest in TldMatcher.TLDS:
                best_match = test

        #return an Error since is not clear on the PS List which is the TLD of the domain marked with '!'
        if best_match in TldMatcher.No_TLDS:
            raise NotImplementedError()

        return best_match

    def get_2ld(self, url):
        urls = url.split('.')
        tlds = self.get_tld(url).split('.')
        return urls[-1 - len(tlds)]

    def get_nld(self, url, n):
        urls = url.split('.')
        tlds = self.get_tld(url).split('.')
        return urls[-n - len(tlds)]


tldmatch = TldMatcher()


def get_2ld(domain):
    """
    Finds 2LD for given FQDN
    """
    sdomain = domain.split('.')

    tld = tldmatch.get_tld(domain)
    index = 2

    if tld:
        num_tld_Levels = len(tld.split('.'))
        index = num_tld_Levels + 1

    if len(sdomain) < index:
        return domain
    else:
        return '.'.join(sdomain[-index:])


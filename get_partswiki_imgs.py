# Python library imports
import os
import logging
import time

# Imports from requirements.txt
import requests
from bs4 import BeautifulSoup


__author__ = "Hillary Jeffrey"
__copyright__ = "Copyright 2019"
__credits__ = ["Hillary Jeffrey"]
__license__ = "GPL"
__version__ = "1.0"
__maintainer__ = "Hillary Jeffrey"
__email__ = "hillaryaj@gmail.com"
__status__ = "Development"

# Global variables
DEFAULT_OUTPUT_PATH = "~/manuals"
PARTSWIKI_BASE_URL = "http://gmpartswiki.com"
BROWSE_PAGE = "/browse"
BIG_PAGE_QUERY = "/getbigpage?pageid={}"
PARTSWIKI_DEFAULT_QUERY = PARTSWIKI_BASE_URL + BIG_PAGE_QUERY

# Keywords for parsing manuals' listings
INDEX_KEY = "/bookindex"
TITLE_KEY = "/getpage"

# User agent
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
SLEEP_TIME = 0.1

# Debug settings
LOG_LEVEL = logging.INFO
SAVE_DEBUG_FILES = False
USE_CACHED_FILES = False
DEBUG_SOUP_FILE = "testoutput_soup.txt"
DEBUG_MANUALS_FILE = "testoutput_manuals.txt"

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=LOG_LEVEL, format='%(levelname)s - %(message)s')


def saveFile(filename, content, writemode='w'):
    """Saves specified string contents to a file with the specified filename.
    Optional parameter writemode (default 'w')"""
    with open(filename, writemode) as f:
        f.write(content)

    return True


def loadPage(source, use_local_cache=False):
    if use_local_cache:
        return loadPageFromFile(source)

    else:
        return loadPageFromURL(source)


def loadPageFromFile(filename):
    """Loads a local cached soup from file and returns BeautifulSoup object"""
    filename = os.path.abspath(os.path.expanduser(filename))
    logging.info("Retrieving cached soup from '{}'".format(filename))

    if not os.path.exists(filename):
        raise IOError("File does not exist: '{}'".format(filename))

    with open(filename) as fp:
        soup = BeautifulSoup(fp, 'html.parser')

    check = soup.title.get_text().strip()
    logging.info("Loaded soup with title '{}'".format(check))

    return soup


def loadPageFromURL(url):
    """Loads a page URL and returns the BeautifulSoup object if
    request is successful"""
    logging.info("Retrieving '{}'".format(url))
    r = requests.get(url, headers=HEADERS)

    if not r.ok:
        logging.warn("Browse page not OK, returned code: {}".format(r.status_code))
        return

    return BeautifulSoup(r.content, 'html.parser')


def extractManualList(soup):
    """Takes a BeautifulSoup page object and extracts information from
    table of manuals"""

    manuals = {}

    # Find all <table> attributes - the manuals are individual <tr>
    for row in soup.find_all('tr'):

        manual = {}

        # Get title, book id, and start page id from links
        for link in row.find_all('a'):
            link_text = link.text.strip()
            link_href = link.get('href')

            logging.debug("Found link: '{}': '{}'".format(
                link_text,
                link_href)
            )

            if link_href.startswith(INDEX_KEY):
                manual['bookid'] = int(link_href.split("=")[-1])
            elif link_href.startswith(TITLE_KEY):
                manual['title'] = link_text
                try:
                    manual['startid'] = int(link_href.split("=")[-1])
                except ValueError as e:
                    # This record is malformed so don't record it
                    logging.warn("'{}': No page id specified".format(
                        link_text)
                    )
                    manual['startid'] = -1

        # Get Type, Effective Date, Publisher, Covers, and # Pages from text
        # logging.debug('Row text: {}'.format(repr(row.get_text())))
        info = list(row.find_all('td')[1].stripped_strings)
        logging.debug('Second cell: {}'.format(info))

        # Extract label positions
        index_effective_date = info.index(u'Effective:') + 1
        index_publisher = info.index(u'Published By:') + 1
        index_covers = info.index(u'Covers:') + 1
        index_page_total = info.index(u'Pages:') + 1
        index_max = len(info)

        # Extract data from label positions
        # NOTE: Entries can be blank, in which case the next label directly
        #       follows the previous label, so check following label index

        # Effective date (Month YYYY)
        if index_effective_date > 0:
            if index_publisher - index_effective_date > 1:
                logging.debug("Effective date [{}]: {}".format(
                    index_effective_date,
                    info[index_effective_date])
                )
                manual['date'] = info[index_effective_date]
            else:
                logging.debug("Effective date [{}]: N/A".format(index_effective_date))
                manual['date'] = ''
        else:
            logging.warn("Effective date label NOT FOUND in '{}'".format(manual[title]))

        # Publisher
        if index_publisher > 0:
            if index_covers - index_publisher > 1:
                logging.debug("Publisher [{}]: {}".format(
                    index_publisher,
                    info[index_publisher])
                )
                manual['publisher'] = info[index_publisher]
            else:
                logging.debug("Publisher [{}]: N/A".format(index_covers))
                manual['publisher'] = ''
        else:
            logging.warn("Publisher label NOT FOUND in '{}'".format(manual[title]))

        # What models the document covers, if specified
        if index_covers > 0:
            if index_page_total - index_covers > 1:
                logging.debug("Models covered [{}]: {}".format(
                    index_covers,
                    info[index_covers])
                )
                # Check for duplicate dates and insert dashes for date ranges

                manual['covers'] = fixCoveredModelText(info[index_covers])
            else:
                logging.debug("Models covered [{}]: N/A".format(index_covers))
                manual['covers'] = ''
        else:
            logging.warn("Covered models label NOT FOUND in '{}'".format(manual[title]))

        # Total number of pages in the manual
        if index_page_total > 0:
            if index_max - index_page_total > 0:
                logging.debug("Total pages [{}]: {}".format(
                    index_page_total,
                    info[index_page_total])
                )
                manual['pages'] = int(info[index_page_total])
            else:
                logging.debug("Total pages [{}]: N/A".format(index_covers))
                manual['pages'] = 0
        else:
            logging.warn("Page total label NOT FOUND in '{}'".format(manual[title]))

        # Determine the output folder name for the manual
        manual['dest'] = generateFolderName(manual)

        # Add this record, but throw an error if there's already one there
        logging.debug("Parsed record:\n{}".format(manual))
        idnum = manual['bookid']
        if idnum in manuals:
            raise ValueError("Duplicate id found for titles:\n'{}'\n'{}'".format(
                    manuals[idnum]['title'],
                    manual['title'])
                )
        manuals[idnum] = manual

    return manuals


def fixCoveredModelText(raw):
    """
    What models the manual covers is sometimes listed as, e.g.
    "1993 1993 Chevrolet Camaro" -> "1993 Chevrolet Camaro".
    Similarly, dashes should be inserted for date ranges, e.g.
    "1982 1992 Chevrolet Camaro" -> "1982-1992 Chevrolet Camaro"

    Collapse repetitive manufacturer labels like
    "Chevrolet Chevelle, Chevrolet Camaro, Chevrolet Corvair, Chevrolet Chevy II"
    into
    "Chevrolet Chevelle, Camaro, Corvair, Chevy II"
    """

    # Fix date range text
    begin = raw[:4]
    end = raw[5:9]
    rawtext = raw[10:]

    if begin == end:
        date = begin
    else:
        date = "{}-{}".format(begin, end)

    # Collapse repetitive manufacturer labels
    makes = {}
    models = rawtext.split(", ")

    for model in models:
        idx = model.find(" ")
        if idx > 0:
            mfr = model[:idx]
            make = model[idx+1:]

            if mfr in makes:
                makes[mfr].append(make)
            else:
                makes[mfr] = [make]

    # Create string list
    text = ", ".join(["{} {}".format(mfr, ", ".join(makes[mfr])) for mfr in makes])

    return "{} {}".format(date, text)



def generateFolderName(entry):
    """
    Manual dict contains:
    # {'bookid': 1,
    #  'covers': u'1960 Chevrolet Corvair',
    #  'date': u'April 1960',
    #  'pages': 160,
    #  'publisher': u'Chevrolet Motor Division',
    #  'startid': 1,
    #  'title': u'Parts and Accessories Catalog P&A 34'}

    # Covers + Title + Effective:
    1960 Chevrolet Corvair - Parts and Accessories Catalog P&A 34 - April 1960
    # Pub + Title + Effective
    Chevrolet Motor Division - Master Parts List Six Cylinder Models - August 1941
    """

    if entry['covers']:
        folder = " - ".join([entry['covers'], entry['title'], entry['date']])
    else:
        folder = " - ".join([entry['publisher'], entry['title'], entry['date']])

    logging.debug("Output folder name: '{}'".format(folder))

    return folder


def getManual(entry, url=PARTSWIKI_DEFAULT_QUERY, dest=DEFAULT_OUTPUT_PATH):
    """
    Input entry is a dictionary describing a manual, e.g.:
    {'bookid': 1,
     'covers': '1960 Chevrolet Corvair',
     'date': u'April 1960',
     'dest': u'1960 Chevrolet Corvair - Parts and Accessories Catalog P&A 34 - April 1960',
     'pages': 160,
     'publisher': u'Chevrolet Motor Division',
     'startid': 1,
     'title': u'Parts and Accessories Catalog P&A 34'}

    This function determines the number of files and gets each page image into
    the specified output directory inside the specified 'dest' parent directory.
    Returns a list of any IDs that fail.
    """
    bad_ids = []
    successful = 0

    logging.info("Downloading manual ({}): '{}'".format(entry['bookid'], entry['title']))

    start = entry['startid']
    total = entry['pages']

    dest = os.path.join(outputpath, entry['dest'])
    if not os.path.exists(dest):
        os.mkdir(dest)
        logging.info("Created output directory '{}'".format(dest))
        # TODO: May want to ask to overwrite images if a directory already exists?

    logging.info("Loading {} IDs starting from {}".format(total, start))
    kk = total
    idnum = start

    while kk > 0:
        retcode = getPageImg(idnum, url, dest)

        if retcode is not None:
            bad_ids.append(idnum)
        else:
            kk -= 1

        idnum += 1
        time.sleep(SLEEP_TIME)

    logging.info("Manual download complete!")

    return total - kk, bad_ids


def getPageImg(pageid, baseurl=PARTSWIKI_DEFAULT_QUERY, dest=DEFAULT_OUTPUT_PATH):
    # Load the page
    pageurl = baseurl.format(pageid)
    logging.debug("..Getting page: {}".format(pageurl))
    r = requests.get(pageurl, headers=HEADERS)

    if r.status_code == requests.codes.ok:
        # Get image name
        logging.debug("Determining attachment name from {}".format(r.headers['content-disposition']))
        filename = r.headers['content-disposition'].replace('attachment; filename=','')
        logging.debug("Filename: '{}'".format(filename))

        # Save image
        destfile = os.path.join(dest, filename)
        logging.debug("ID {}: Writing to '{}'".format(pageid, filename))
        with open(destfile, 'wb') as f:
            f.write(r.content)

    else:
        logging.warn("ID {}: status not ok - code {} at {}".format(pageid,
            r.status_code,
            pageurl)
        )
        return r.status_code


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description='Downloads images or files from a partswiki into folders for each manual'
    )

    parser.add_argument(
        '-u',
        '--url',
        default=PARTSWIKI_BASE_URL,
        type=str,
        dest='baseurl',
        help='Site URL ' +
             '(Default: "{}")'.format(PARTSWIKI_BASE_URL)
    )

    parser.add_argument(
        '-o',
        '--output',
        default=DEFAULT_OUTPUT_PATH,
        type=str,
        dest='outputpath',
        help='Output path (Default: "{}"")'.format(DEFAULT_OUTPUT_PATH)
    )

    parser.add_argument(
        '-s',
        '--start-with',
        type=int,
        dest='startwithbookid',
        help='Indicate a bookid to start with'
    )

    args = parser.parse_args()

    # Make sure output path exists
    outputpath = os.path.abspath(os.path.expanduser(args.outputpath))
    if not os.path.exists(outputpath):
        logging.debug("Creating output path: {}".format(outputpath))
        os.makedirs(outputpath)

    # Create URLs
    soup_source = args.baseurl + BROWSE_PAGE
    big_img_query = args.baseurl + BIG_PAGE_QUERY

    logging.debug("Browse-page URL: {}".format(soup_source))
    logging.debug("Large-image query string: {}".format(big_img_query))

    # Load browse page and scan to extract manuals
    cached = USE_CACHED_FILES
    if cached:
        filename = os.path.join(outputpath, DEBUG_SOUP_FILE)
        if not os.path.exists(filename):
            logging.error("Specified soup cache '{}' ".format(filename) +
                "DOES NOT EXIST! Reverting to load from URL.")
            cached = False
        else:
            soup_source = filename

    soup = loadPage(soup_source, use_local_cache=cached)

    if not soup:
        logging.error("Load error on '{}'".format(soup_source))
        exit()

    # Save soup for testing (if not loading from cached soup)
    if not cached and SAVE_DEBUG_FILES:
        testoutput = os.path.join(outputpath, "testoutput_soup.txt")
        logging.debug("Saving browse page contents to {}".format(testoutput))
        saveFile(testoutput, soup.prettify())

    # Extract information on available manuals
    manuals = extractManualList(soup)

    logging.info("Extracted listings for {} manuals".format(len(manuals)))

    # Save extracted manuals' info for testing
    if SAVE_DEBUG_FILES:
        testoutput = os.path.join(outputpath, "testoutput_manuals.txt")
        logging.debug("Saving manual contents to {}".format(testoutput))
        from pprint import pformat
        saveFile(testoutput, pformat(manuals))

    # Download each manual
    bad_ids = {}
    for kk in manuals:
        # Skip indicated book ids
        if kk < args.startwithbookid:
            continue

        num_success, failures = getManual(manuals[kk], big_img_query, outputpath)
        bad_ids[manuals[kk]['bookid']] = failures

    logging.info("Downloads complete! Saved in {}".format(outputpath))

    if len(bad_ids) > 0:
        from pprint import pformat
        logging.warn("Failed to download IDs:\n{}".format(bad_ids))

    logging.info("Processing complete! Exiting...")

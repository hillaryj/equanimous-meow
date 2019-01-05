# Python library imports
import os
import requests
import logging


__author__ = "Hillary Jeffrey"
__copyright__ = "Copyright 2018"
__credits__ = ["Hillary Jeffrey"]
__license__ = "GPL"
__version__ = "1.0"
__maintainer__ = "Hillary Jeffrey"
__email__ = "hillaryaj@gmail.com"
__status__ = "Development"


DEFAULT_OUTPUT_PATH = r"C:\Users\Hillary\Downloads\gmpartswiki"
GM_PARTSWIKI_BASE_URL = "http://gmpartswiki.com/getbigpage?pageid={}"


# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')


def getPage(pageid, baseurl=GM_PARTSWIKI_BASE_URL, dest=DEFAULT_OUTPUT_PATH):
    # Initialize variables for scope
    pageurl = baseurl.format(pageid)

    # Load the page
    logging.debug("..Getting page: {}".format(pageurl))
    r = requests.get(pageurl)

    if r.status_code == requests.codes.ok:
        # Get image name
        logging.debug("Determining attachment name from {}".format(r.headers['content-disposition']))
        filename = r.headers['content-disposition'].replace('attachment; filename=','')
        logging.debug("Filename: '{}'".format(filename))

        # Save image
        destfile = os.path.join(dest, filename)
        logging.info("ID {}: Writing to '{}'".format(pageid, filename))
        with open(destfile, 'wb') as f:
            f.write(r.content)

    else:
        logging.warn("ID {}: status not ok - code {}".format(pageid, r.status_code))
        return r.status_code

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description='Downloads a series of images or files by ID and a base url'
    )

    parser.add_argument(
        type=int,
        dest='startid',
        help='ID number to start from'
    )

    parser.add_argument(
        type=int,
        dest='stopid',
        help='ID number to stop at (inclusive)'
    )

    parser.add_argument(
        '-url',
        '--base-url',
        default=GM_PARTSWIKI_BASE_URL,
        type=str,
        dest='baseurl',
        help='URL of page URL pattern' +
             '(Default: "http://gmpartswiki.com/getbigpage?pageid={}")'
    )

    parser.add_argument(
        '-path',
        '--output-path',
        default=DEFAULT_OUTPUT_PATH,
        type=str,
        dest='outputpath',
        help='Output path (Default: current directory)'
    )

    args = parser.parse_args()

    start = args.startid
    stop = args.stopid + 1

    bad_ids = {}

    logging.info("Loading IDs from {} to {}".format(start, stop))
    for idnum in range(start, stop):
        retcode = getPage(idnum, baseurl=args.baseurl, dest=args.outputpath)

        if retcode is not None:
            bad_ids[idnum] = retcode

    logging.info("Downloads complete!")
    logging.info("Downloads saved in {}".format(args.outputpath))

    if len(bad_ids) > 0:
        from pprint import pformat
        logging.warn("IDs and failure codes:\n{}".format(pformat(bad_ids)))

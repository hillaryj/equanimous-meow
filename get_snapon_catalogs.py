# Python library imports
import os
import logging
import requests
import time


__author__ = "Hillary Jeffrey"
__copyright__ = "Copyright 2018"
__credits__ = ["Hillary Jeffrey"]
__license__ = "GPL"
__version__ = "1.0"
__maintainer__ = "Hillary Jeffrey"
__email__ = "hillaryaj@gmail.com"
__status__ = "Development"


DEFAULT_OUTPUT_PATH = "~/snapon"
SLEEP_TIME = 0.1

YEAR = "1958"
LETTER = "W"
BASE_CATALOG = "http://www.collectingsnapon.com/catalogs/catalogs-large/{0}_Industrial_Catalog_{1}/{0}-Industrial-Catalog-{1}-"
BASE_PAGE = "p{:02d}.jpg"
BASE_URL = BASE_CATALOG.format(YEAR, LETTER) + BASE_PAGE
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
}


# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")


def getPage(pageid, baseurl=BASE_URL, dest=DEFAULT_OUTPUT_PATH):
    # Initialize variables for scope
    url = baseurl.format(pageid)

    # Get image name
    filename = url.split("/")[-1]
    destfile = os.path.join(dest, filename)

    logging.info("Retrieving '{}'".format(filename))
    # Retrieve the image
    r = requests.get(url, headers=HEADERS)

    if not r.ok:
        logging.info("Not OK: {}".format(r.status_code))
        return r.status_code

    logging.debug("Saving filename: '{}'".format(filename))
    with open(destfile, "wb") as f:
        f.write(r.content)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Downloads a series of images or files by ID and a base url"
    )

    parser.add_argument(type=int, dest="startid", help="ID number to start from")

    parser.add_argument(
        type=int, dest="stopid", help="ID number to stop at (inclusive)"
    )

    parser.add_argument(
        "-year",
        default=YEAR,
        type=str,
        dest="year",
        help="Catalog year, e.g. {}".format(YEAR),
    )

    parser.add_argument(
        "-letter",
        default=LETTER,
        type=str,
        dest="letter",
        help="Catalog letter, e.g. {}".format(LETTER),
    )

    parser.add_argument(
        "-path",
        "--output-path",
        default=DEFAULT_OUTPUT_PATH,
        type=str,
        dest="outputpath",
        help="Output path (Default: current directory)",
    )

    args = parser.parse_args()

    # Find start and stop IDs
    start = args.startid
    stop = args.stopid + 1

    # Make sure output dirs exist
    outputpath = os.path.abspath(os.path.expanduser(args.outputpath))
    if not os.path.exists(outputpath):
        logging.debug("Creating output path: {}".format(outputpath))
        os.makedirs(outputpath)

    # Create base URL
    base_url = BASE_CATALOG.format(args.year, args.letter) + BASE_PAGE
    logging.info("Base URL: '{}'".format(base_url))

    bad_ids = {}

    logging.info("Loading IDs from {} to {}".format(start, stop - 1))
    for idnum in range(start, stop):
        retcode = getPage(idnum, baseurl=base_url, dest=outputpath)

        if retcode is not None:
            bad_ids[idnum] = retcode

        # if idnum < stop - 1:
        #     time.sleep(SLEEP_TIME)

    logging.info("Downloads complete!")
    logging.info("Downloads saved in {}".format(args.outputpath))

    if len(bad_ids) > 0:
        from pprint import pformat

        logging.warn("IDs and failure codes:\n{}".format(pformat(bad_ids)))

#!/usr/bin/env python
"""
Retrieves a list of custom emoji for a Slack and exports it.

This uses an obsolete authentication method that Slack has deprecated.

"""

# Python library imports
import os
import logging

# Imports from requirements.txt
import requests


__author__ = "Hillary Jeffrey"
__copyright__ = "Copyright 2019"
__credits__ = ["Hillary Jeffrey"]
__license__ = "GPL"
__version__ = "1.0"
__maintainer__ = "Hillary Jeffrey"
__email__ = "hillaryaj@gmail.com"
__status__ = "Development"


# Default save folder if another folder is not specified
DEFAULT_PATH = "~"
DEFAULT_SAVE_FOLDER = "emoji"
DEFAULT_SAVE_PATH = os.path.join(DEFAULT_PATH, DEFAULT_SAVE_FOLDER)
# A 'token.txt' file with Slack API token is expected
# to be located in the root save folder
# i.e at "DEFAULT_PATH/DEFAULT_SAVE_FOLDER/TOKEN_FILENAME"
# Generate token at: https://api.slack.com/web
TOKEN_FILENAME = "slacktoken.txt"

# JSON->dict eval() parsing shortcuts - TEMPORARY
true = True
false = False
null = None

# Slack URLs
# Emoji List:
list_url = "https://slack.com/api/emoji.list"
# Parameters:
# token

# User agent
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
SLEEP_TIME = 0.1

# Set up logging
LOG_LEVEL = logging.INFO
logger = logging.getLogger(__name__)
logging.basicConfig(level=LOG_LEVEL, format='%(levelname)s - %(message)s')


def getRequest(geturl, getparams):
    """Handle GETting a request; returns a dict.

    Checks Slack-specific return verbiage for whether
    retrieval was successful and raises an error if not.

    Arguments:
        geturl {string} -- URL for GET
        getparams {dict} -- dictionary of additional parameters

    Returns:
        dict -- [description]

    Raises:
        e -- [description]
        Exception -- [description]

    """
    req = requests.get(geturl, params=getparams)
    # TODO: Add more fault detection and more elegantly turn the JSON into dict
    # eval() is really NOT the right way to do this
    try:
        ret_dict = eval(req.text)
    except Exception as e:
        pprint(req)
        raise e

    # Check Status
    if not ret_dict["ok"]:
        # Error handling
        raise Exception("Error during request:\n%s" % ret_dict["error"])

    return ret_dict


def getImg(imgurl, dest=DEFAULT_SAVE_PATH):
    """Retrieve an image from a URL.

    Retrieves an image via from the specified URL and saves it to
    the specified destination path. The image name is retrieved as
    part of the Slack imgurl request.

    Arguments:
        imgurl {string} -- [description]

    Keyword Arguments:
        dest {string} -- directory to save to (default: {DEFAULT_SAVE_PATH})

    Returns:
        [type] -- None or failure status code

    """
    r = requests.get(imgurl, headers=HEADERS)

    if r.status_code == requests.codes.ok:
        # Get image name
        logging.debug(
            "Determining attachment name from {}".format(
                r.headers['content-disposition']
            )
        )
        filename = r.headers['content-disposition'].replace(
            'attachment; filename=',
            ''
            )
        logging.debug("Filename: '{}'".format(filename))

        # Save image
        destfile = os.path.join(dest, filename)
        logging.debug("{}: Writing to file".format(filename))
        with open(destfile, 'wb') as f:
            f.write(r.content)

    else:
        logging.warn(
            "{}: status not ok - {}".format(
                r.status_code,
                imgurl
            )
        )
        return r.status_code


def getEmojiList(token, expand_aliases=False):
    """Retrieve the list of emoji and aliases.

    If expand_aliases is True, then aliases will be expanded to their actual
    target URL. Returns a dict of emoji names and URLs

    Arguments:
        token {string} -- Slack authentication token

    Keyword Arguments:
        expand_aliases {bool} -- If True, aliases will be expanded to their
            actual target URL (default: {True})

    Returns:
        dict -- Emoji names and URLs

    """
    emoji_dict = {}
    alias_dict = {}
    # Retrieve list of emoji
    list_payload = {"token": token}

    # TODO: Add error handling for when requests go wrong
    lr_dict = getRequest(list_url, list_payload)

    # Peel off list of emoji name keys and their URLs
    for name in lr_dict["emoji"]:
        url = lr_dict["emoji"][name]

        # Handle aliases
        if url.startswith("alias:") and expand_aliases:
            alias_dict[name] = url.split(":")[-1]
        else:
            emoji_dict[name] = url

    if expand_aliases:
        for name in alias_dict:
            emoji_dict[name] = emoji_dict[alias_dict[name]]

    return emoji_dict


def downloadEmoji(emoji_dict, dest=DEFAULT_SAVE_PATH):
    """Perform emoji download on a list.

    Given a dict of emoji names and URLs, downloads each emoji

    Arguments:
        emoji_dict {dict} -- Contains emoji names and URLs

    Keyword Arguments:
        dest {[type]} -- [description] (default: {DEFAULT_SAVE_PATH})

    """
    for name in emoji_dict:
        getImg()


def loadPaths(path=DEFAULT_PATH, savepath=DEFAULT_SAVE_FOLDER):
    """Load the root path and destination paths and perform path checking.

    [description]

    Keyword Arguments:
        path {[type]} -- [description] (default: {DEFAULT_PATH})
        savepath {[type]} -- [description] (default: {DEFAULT_SAVE_FOLDER})

    Returns:
        [type] -- [description]

    """
    rootpath = os.path.abspath(os.path.expanduser(path))
    destpath = os.path.join(rootpath, savepath)

    try:
        os.makedirs(destpath)
    except OSError:
        # OSError occurs when attempting to makedirs that exist
        # Ignore this exception
        pass

    return rootpath, destpath


def loadTokenFromFile(tokendir):
    """Load the user slack token from the given path.

    Generate Slack API token at: https://api.slack.com/web

    Arguments:
        rootpath {string} -- [description]

    Returns:
        [type] -- [description]

    """
    tokenpath = os.path.join(tokendir, TOKEN_FILENAME)
    if not os.path.exists(tokenpath):
        logging.error(
                "Expected to find token file at: {}\n".format(tokenpath) +
                "Generate Slack API token at: https://api.slack.com/web"
            )
        return None
    else:
        with open(tokenpath, 'r') as f:
            user_token = f.read()

    return user_token


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='Records and manages Slack history.'
    )
    parser.add_argument(
        '-t', '--token', metavar='TOKEN', type=str,
        dest='user_token',
        help='Specify a user token, overrides saved token in root path'
    )
    parser.add_argument(
        '-r', '--root-path', metavar='ROOTPATH', type=str,
        dest='inputroot', default=DEFAULT_PATH,
        help='Specifies root path for Slack token and save folder " + \
        "(default: "$USER/" or "~")'
    )
    parser.add_argument(
        '-d', '--dest-name', metavar="SAVEFOLDER", type=str,
        dest='inputdest', default=DEFAULT_SAVE_FOLDER,
        help='Specifies save folder name inside root folder " + \
        "(default: "emoji")'
    )
    parser.add_argument(
        '-l', '--list-only', action='store_true',
        dest='listonly',
        help='Retrieve and list emoji, no image saving'
    )

    args = parser.parse_args()

    # Load paths
    rootpath, destpath = loadPaths(args.inputroot, args.inputdest)
    logging.info("Output directory set: '{}'".format(destpath))

    # Load token if performing any operation involving the Slack API
    if args.user_token is not None:
        user_token = args.user_token
        logging.info("User token loaded")
    else:
        user_token = loadTokenFromFile(rootpath)
        if user_token is not None:
            logging.info("User token loaded")
        else:
            quit(1)

    # Load emoji list
    logging.info("Loading emoji list...")
    emoji_list = getEmojiList(user_token)

    # Save images if not listonly, otherwise list
    if not args.listonly:
        logging.info("Saving emoji...")
        downloadEmoji(emoji_list)
        logging.info("Complete!")
    else:
        logging.info("Emoji:\n{}".format(emoji_list))

#!/usr/bin/env python
"""
Retrieves Slack history and saves it.

Other future plans:
* Better JSON parsing and output formatting
* Command-line arguments and non-hardcoded paths
"""

# Python library imports
import requests
import os
from datetime import datetime
import time
from pprint import pprint, pformat
import logging


__author__ = "Hillary Jeffrey"
__copyright__ = "Copyright 2015"
__credits__ = ["Hillary Jeffrey"]
__license__ = "GPL"
__version__ = "1.0"
__maintainer__ = "Hillary Jeffrey"
__email__ = "hillaryaj@gmail.com"
__status__ = "Development"


# Default save folder if another folder is not specified
DEFAULT_PATH = "~/Copy"
DEFAULT_SAVE_FOLDER = "SavedHistory"
# A 'token.txt' file with Slack API token is expected
# to be located in the root save directory
# Generate token at: https://api.slack.com/web
TOKEN_FILENAME = "slacktoken.txt"
# Date format for output file name
DATE_FORMAT = "%Y%m%d_%H%M"
# Output file format is "CHAN/DATE_FORMAT_CHAN.txt"
OUTFILE = "%s_%s.txt"
# Saves messages in retrieved or timeline order
PRESERVE_OLDEST_FIRST = True

# JSON->dict eval() parsing shortcuts - TEMPORARY
true = True
false = False
null = None

## Slack URLs
# Channel List:
list_url = "https://slack.com/api/channels.list"
# Parameters:
# token
# exclude_archived = 1

# Channel History:
ch_hist_url = "https://slack.com/api/channels.history"
# Parameters:
# token
# channel
# latest = 10 (timestamp to not re-archive messages)
# count = 100


def getRequest(geturl, getparams):
    """Request get handling; returns a dict.
    Checks Slack-specific return verbiage for whether
    retrieval was successful and raises an error if not."""
    req = requests.get(geturl, params=getparams)
    # TODO: Add more fault detection and more elegantly turn the JSON into dict
    # eval() is really NOT the right way to do this
    try:
        ret_dict = eval(req.text)
    except Exception, e:
        pprint(req)
        raise e

    # Check Status
    if not ret_dict["ok"]:
        # Error handling
        raise Exception("Error during request:\n%s" % ret_dict["error"])

    return ret_dict


def prepForFileOutput(messagelist):
    """Future expansion: Make output files a pretty formatted string"""

    if PRESERVE_OLDEST_FIRST:
        messagelist.reverse()

    return pformat(messagelist)


def getChannels(token):
    """Retrieves the list of channels.
    Returns a dict of Slack IDs and names"""
    channel_list = {}
    # Retrieve list of channels
    list_payload = {"token": token, "exclude_archived": True}

    # TODO: Add error handling for when requests go wrong
    lr_dict = getRequest(list_url, list_payload)

    # Peel off list of channels
    for channel in lr_dict["channels"]:
        channel_list[channel["id"]] = channel["name"]

    return channel_list


def getChannelHistory(chanid, token, latest = 0):
    """For a given channel ID, returns a string JSON object of channel history and time period"""

    ch_payload = {"token": token,
                  "channel": chanid,
                  "latest": latest}
    chan_history = []
    get_more = True

    while get_more:
        # TODO: Add error handling for when requests go wrong
        hist_dict = getRequest(ch_hist_url, ch_payload)
        chan_history.extend(hist_dict["messages"])
        get_more = hist_dict["has_more"]
        if get_more:
            ch_payload["latest"] = chan_history[-1]["ts"]

    return chan_history


def recordHistory(dest, token):
    """Records channel history as a JSON text object in the specified destination folder"""
    # Make sure destination folders exist - parse dest folder
    curtime = datetime.now().strftime(DATE_FORMAT)
    print "Run starting: %s" % curtime

    # Get the list of channels
    channels = getChannels(token=token)
    print "Retrieved %d channels" % len(channels)

    # For each channel, get history and dump into a text file (append if exist)
    for chanid in channels:
        chname = channels[chanid]
        print "Retrieving channel #%s [%s]" % (chname, chanid)
        hist = getChannelHistory(chanid=chanid, token=token)

        if len(hist) == 0:
            # Don't bother doing anything for an empty file
            print "Channel #%s history is empty, skipping" % chname
            continue

        # Create a folder with the friendly channel name
        # Save name format is: CHANNELNAME/DATEOFSAVE_CHANNELNAME.txt
        chdir = os.path.join(dest, chname)
        if not os.path.exists(chdir):
            # print "Creating directory: %s" % chdir
            os.mkdir(chdir)
        outputfile = os.path.join(chdir, "%s_%s.txt"%(curtime, chname))
        print "Saving %d messages in history to: %s" % (len(hist), outputfile)

        with open(outputfile, 'w') as f:
            f.write(prepForFileOutput(hist))

    # Ta da!
    print "History retrieval complete!"


# General program flow
# 0. Load permanent storage for list of channels and their 'latest' read
# 1. Check if "ok" == True (if not, use "error" property)
# 2. Use channels[kk]["id"] item to generate list of channels
# 3. For each channel:
# 3.1. Fetch history per 'latest' of last archive
#      (continue as long as 'has_more' is True;
#       replies["messages][-1]["ts"] entry)
# 3.2. Save history in file area (Dropbox or Copy)
# 3.3. Update permanent storage with new value for 'latest'


if __name__ == '__main__':
    # TODO: Add command-line arguments for default args above

    # Look for token in a file in the destination folder
    rootpath = os.path.abspath(os.path.expanduser(DEFAULT_PATH))
    destpath = os.path.join(rootpath, DEFAULT_SAVE_FOLDER)

    try:
        os.makedirs(destpath)
    except:
        pass
    print "Output directory set: %s" % destpath

    print "Loading token"
    tokenpath = os.path.join(rootpath, TOKEN_FILENAME)
    if not os.path.exists(tokenpath):
        print "Expected to find token file at: %s" % tokenpath
        print "Generate Slack API token at: https://api.slack.com/web"

    else:
        with open(tokenpath, 'r') as f:
            user_token = f.read()

        print "Making history..."
        recordHistory(destpath, token=user_token)

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

# User related globals
USERS_FILENAME = "users.txt"
USE_USERNAME = "name"
USE_REALNAME = "real_name"
BOTS_LIST = ['USLACKBOT']

# History Stitching
OVERALL_HISTORY_FILENAME = "_history.txt"

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

# User names/IDs:
user_info_url = "https://slack.com/api/users.list"
# Parameters:
# token
# presence = 1 (whether to include presence data)


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


def getUserDict(token):
    """Retrieves the list of users and parses it into ID/Name combinations.
    Format is {userid: [username, textname]}
    """

    users = {}

    payload = {"token": token}
    rawusers = getRequest(user_info_url, payload)['members']

    for user in rawusers:
        # Parse users and strip out most of the data
        # if no name set, reuse username
        realname = user['profile']['real_name']
        if len(realname) == 0:
            realname = user['name']

        users[user['id']] = {'name': user['name'],
                             'real_name': realname,
                            }

    return users


def lookupUserID(uid, users, nametype=USE_USERNAME):
    """Retrieves the user name for the specific user ID"""
    if uid not in users:
        if uid not in BOTS_LIST:
            print "User ID not found: '%s'" % uid
        return uid

    # print "User lookup: %s -> %s" % (uid, users[uid])

    return users[uid][nametype]


def recordUsers(dest, token):
    """Records list of current users to file"""
    # Get the list of users & save it (overwrite previous)
    users = getUserDict(token)
    outputfile = os.path.join(dest, "users.txt")
    print "Retrieved %d users; saving to %s" % (len(users), outputfile)
    saveFile(outputfile, pformat(users))

    # Ta da!
    print "User list retrieval complete!"


def loadUsersFromFile(dest):
    """Loads the list of current users from file"""
    userfile = os.path.join(dest, "users.txt")

    if not os.path.exists(userfile):
        raise IOError("User file does not exist: '%s'" % userfile)

    with open(userfile, 'r') as f:
        users = f.read()

    users = eval(users)

    return users

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

        saveFile(outputfile, prepForFileOutput(hist))

    # Ta da!
    print "History retrieval complete!"


def loadPaths(path=DEFAULT_PATH, savepath=DEFAULT_SAVE_FOLDER):
    """Loads the root path and destination paths and performs path checking"""
    # Look for token in a file in the destination folder
    rootpath = os.path.abspath(os.path.expanduser(DEFAULT_PATH))
    destpath = os.path.join(rootpath, DEFAULT_SAVE_FOLDER)

    try:
        os.makedirs(destpath)
    except:
        # Exception occurs when attempting to makedirs that exist
        # Ignore this exception
        # TODO: Parse for specific exception type so we don't ignore
        # unexpected exceptions
        pass

    return rootpath, destpath

def loadToken(rootpath):
    """Loads the user slack token in the expected path.
    Generate Slack API token at: https://api.slack.com/web"""
    tokenpath = os.path.join(rootpath, TOKEN_FILENAME)
    if not os.path.exists(tokenpath):
        print "Expected to find token file at: %s" % tokenpath
        print "Generate Slack API token at: https://api.slack.com/web"
        return None
    else:
        with open(tokenpath, 'r') as f:
            user_token = f.read()

    return user_token


###########################################################
# Pretty Parsing
###########################################################
# Given:
# - A folder full of Slack history files (with time overlap)
# - A dictionary of user IDs & names
# Do:
# 1. Load the history file
# 2. Find the latest time stamp
# 3. Stitch history together
#    - Add attribute to dict of 'username' as looked up from 'user'
# 4. Output formatting:
#    - Format like Slack interface, replace with names
#      (Input flag for real name vs user name)
###########################################################

def loadHistoryFile(filename):
    """Loads a specified saved history file and returns as a python list"""
    if not os.path.exists(filename):
        return []
    if os.path.isdir(filename):
        raise IOError("loadHistoryFile: Specified file is actually a directory '%s'" % (filename))

    # Load history file
    with open(filename, 'r') as f:
        strhist = f.read()

    # Turn saved python object string back into a list
    hist = eval(strhist)
    return hist


def formatHistoryList(hist, users):
    """Parses a history list (of dicts) and adds user names
    from user IDs and turns timestamps into floats.

    Modifies in place; returns the list.
    TODO: Parse for @mentions in the 'text' field"""
    # Parse through history to perform formatting/updates
    for entry in hist:
        # Turn timestamps into floats
        entry['ts'] = float(entry['ts'])
        # If entry has the key 'user', look up and add the name
        if entry.has_key('user'):
            entry['name'] = lookupUserID(entry['user'], users)
        # Parse through reactions and add user names
        if entry.has_key('reactions'):
            for reaction in entry['reactions']:
                reaction['names'] = []
                for user in reaction['users']:
                    reaction['names'].append(lookupUserID(user, users))

    return hist


def getHistoryTimeSpan(historylist):
    """History will be in order (oldest to/from newest).
    This method finds the first and last timestamps.
    Returns tstart, tend"""
    t0 = float(historylist[0]['ts'])
    tn = float(historylist[-1]['ts'])

    return min(t0, tn), max(t0, tn)


def getHistoryTimes(historylist):
    """Returns a list of all time stamps contained in the
    history list.
    """
    times = [entry['ts'] for entry in historylist]
    # Should be sorted already but make sure
    times.sort()

    return times

def saveFile(filename, content, writemode='w'):
    """Saves specified contents to filename.
    Optional parameter writemode (default 'w')"""
    with open(filename, writemode) as f:
        f.write(content)
    return True


def parseChannelHistoryFiles(chdir, users,
                             save_overall_history = True,
                             force_refresh = True,
                             ignore_subdirs = True):
    """Parses all files inside a specified directory and builds the
    stitched history file. Parses through each file to prevent duplicate
    entries from history files that overlap, as well as adding user names
    from the input users dict to the output file for easier human readability.

    Input:
    - chdir: specified directory containing history files
    - users: dictionary of user ids and names
    - save_overall_history: if true, saves to disk; if false does not
    - force_refresh: if true, re-parses all files; false starts with saved file
    - ignore_subdirs: NOT IMPLEMENTED - if false will process subdirectories recursively; only True behavior is currently implemented

    Returns overall history list/array."""
    histdict = {}

    # Get a list of files in the channel directory
    if not os.path.isdir(chdir):
        print "Error: '%s' is not a directory" % chdir
        return history

    filelist = os.listdir(chdir)

    # If we've made a concatenated file before, load it
    # Unless force_refresh is enabled
    if OVERALL_HISTORY_FILENAME in filelist and not force_refresh:
        # Load the previously-made concatenated file first
        hfn = os.path.join(chdir, OVERALL_HISTORY_FILENAME)
        history = formatHistoryList(loadHistoryFile(hfn), users)
        # start, end = getHistoryTimeSpan(history)
        htimes = getHistoryTimes(history)

        histdict.update(dict(htimes, history))

    # Parse each history file
    for hfile in filelist:
        # We've already dealt with the concatenated file, so ignore
        if hfile == OVERALL_HISTORY_FILENAME:
            continue

        # Do the rest of the parsing
        hfn = os.path.join(chdir, hfile)
        # Deal with subdirectories
        if os.path.isdir(hfn):
            if ignore_subdirs:
                print "Ignoring subdirectory %s" % hfile
                continue
            else:
                raise NotImplementedError("Parsing subdirectories is currently NOT IMPLEMENTED")
                continue
        htmp = loadHistoryFile(hfn)

        # Wait to perform the formatting to save processing
        # on files that completely overlap with existing history
        t0, tn = getHistoryTimeSpan(htmp)
        if t0 in histdict and tn in histdict:
            continue

        # Add new history to the overall history
        htmp = formatHistoryList(htmp, users)
        ttmp = getHistoryTimes(htmp)

        tmpdict = dict(zip(ttmp, htmp))

        histdict.update(tmpdict)

    # Turn history dict back into a list
    overall_history = [histdict[key]
                       for key in sorted(histdict.iterkeys())]

    # Save the concatenated file if not empty
    if save_overall_history and len(histdict) > 0:
        saveFile(os.path.join(chdir, OVERALL_HISTORY_FILENAME),
                 pformat(overall_history))

    return overall_history


def stitchHistory(dest):
    """Overall stitching method for performing history
    concatenation and parsing. Processes each subdirectory in the
    specified destination path and outputs a stitched history file
    in each subdirectory."""
    # Get the list of channel folders
    destlist = [os.path.join(dest,entry)
                for entry in os.listdir(dest)
                if os.path.isdir(os.path.join(dest,entry))]
    print "Retrieved %d channels" % len(destlist)

    users = loadUsersFromFile(dest)

    for chdir in destlist:
        print "Stitching channel %s" % chdir
        chhist = parseChannelHistoryFiles(chdir, users, save_overall_history = True, force_refresh = True)

    # Ta da!
    print "History stitching complete!"


###########################################################
# General program flow
###########################################################
# 0. Load permanent storage for list of channels and their 'latest' read
# 1. Check if "ok" == True (if not, use "error" property)
# 2. Use channels[kk]["id"] item to generate list of channels
# 3. For each channel:
# 3.1. Fetch history per 'latest' of last archive
#      (continue as long as 'has_more' is True;
#       replies["messages][-1]["ts"] entry)
# 3.2. Save history in file area (Dropbox or Copy)
# 3.3. Update permanent storage with new value for 'latest'
###########################################################


if __name__ == '__main__':
    # TODO: Add command-line arguments to load args instead of defaults above
    rootpath, destpath = loadPaths()
    print "Output directory set: %s" % destpath

    print "Loading token"
    user_token = loadToken(rootpath)

    # TODO: Add command-line flags to perform each action separately
    if user_token is not None:
        print "Making history..."
        recordHistory(destpath, token=user_token)
        print "Recording user list..."
        recordUsers(destpath, token=user_token)
        # TODO: History stitching probably doesn't require user_token and can be moved out of this if statement
        print "Stitching history..."
        stitchHistory(destpath)

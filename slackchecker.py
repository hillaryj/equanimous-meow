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
from pprint import pprint, pformat


__author__ = "Hillary Jeffrey"
__copyright__ = "Copyright 2016"
__credits__ = ["Hillary Jeffrey"]
__license__ = "GPL"
__version__ = "1.0"
__maintainer__ = "Hillary Jeffrey"
__email__ = "hillaryonline@gmail.com"
__status__ = "Development"


# Default save folder if another folder is not specified
DEFAULT_PATH = "~/"
DEFAULT_SAVE_FOLDER = ""
# A 'token.txt' file with Slack API token is expected
# to be located in the root save directory
# Generate token at: https://api.slack.com/web
TOKEN_FILENAME = "slacktoken.txt"

# JSON->dict eval() parsing shortcuts - TEMPORARY
true = True
false = False
null = None

# Readability searches
# TODO: This is a hack for parsing unicode characters into readable excerpts
READABILITY_REPL = {'\n\n': '\n',
                    '&lt;': '<',
                    '&gt;': '>',
                    '\u2014': '-',
                    '\u2018': "'",
                    '\u2019': "'",
                    '\u201c': '"',
                    '\u201d': '"',
                    '\u2026': '...',
                    '\u00a0': ' ',
                    # '': '',
                    }

# User related globals
USERS_FILENAME = "users.txt"
USE_USERNAME = "name"
USE_REALNAME = "real_name"
BOTS_LIST = ['USLACKBOT']

# History Stitching
OVERALL_HISTORY_FILENAME = "_history.txt"
EXCERPT_FILENAME = "_excerpt.txt"
IGNORE_FILE_LIST = [OVERALL_HISTORY_FILENAME, EXCERPT_FILENAME]

## Slack URLs
# Channel List:
list_url = "https://slack.com/api/channels.list"
# Parameters:
# token
# exclude_archived = 1

# User names/IDs:
user_info_url = "https://slack.com/api/users.list"
# Parameters:
# token
# presence = 1 (whether to include presence data)

# Channel info:
ch_info_url = "https://slack.com/api/channels.info"
# Parameters:
# token
# channel = <channel ID>

def getRequest(geturl, getparams):
    """Request get handling; returns a dict.
    Checks Slack-specific return verbiage for whether
    retrieval was successful and raises an error if not."""
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


def getChannelInfo(token, chanid):
    """For a given channel ID, returns a tuple of: (user is a member, channel name, and a list of all channel members)"""

    ch_payload = {"token": token,
                  "channel": chanid}
    chan_members = []

    chan_dict = getRequest(ch_info_url, ch_payload)

    # TODO: Add error handling for when requests go wrong
    if chan_dict["ok"]:
        return chan_dict["channel"]["is_member"], chan_dict["channel"]["name"], chan_dict["channel"]["members"]
    else:
        return -1, "", []


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


def reverseLookupUID(checkname, users, nametype=USE_USERNAME):
    """Determine user ID from a username and return. If not found, returns None"""
    for uid, names in users:
        if names[nametype].upper() == checkname.upper():
            return uid

    return None


def lookupUserID(uid, users, nametype=USE_USERNAME):
    """Retrieves the user name for the specific user ID"""
    if uid not in users:
        if uid not in BOTS_LIST:
            print "User ID not found: '%s'" % uid
        return uid

    # print "User lookup: %s -> %s" % (uid, users[uid])

    return users[uid][nametype]


def loadPaths(path=DEFAULT_PATH):
    """Loads the root path and destination paths and performs path checking"""
    return loadRootPath(path)

def loadRootPath(path=DEFAULT_PATH):
    rootpath = os.path.abspath(os.path.expanduser(path))

    return rootpath

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


def checkChannels(token, checkname, outputall):
    """Takes a Slack token, a target username, and output of 'all' (True) or just 'shared' (False).
    Returns a list of channel names (not IDs)."""

    target_channels = []

    # Get all the users on this slack
    user_list = getUserDict(token)

    # Reverse lookup the uid of the target user
    # TODO: Allow a list for checkname(s)
    target_uid = reverseLookupUID(checkname, user_list)

    if target_uid is None:
        raise Exception("Target user '%s' not found in channel list" % checkname)

    # Get a list of all channels
    ch_list = getChannels(token)

    # Check each channel for user membership
    for chanid in ch_list:
        is_member, ch_name, all_members = getChannelMembers(token, chanid)

        # Is user in this channel?
        if target_uid not in all_members:
            continue

        if not outputall and is_member:
            target_channels.append(ch_name)
        elif outputall:
            target_channels.append(ch_name)
        else:
            # No reporting
            continue

    return target_channels



###########################################################
# General program flow
###########################################################
# 0. Load permanent storage for list of channels and their 'latest' read
# 1. Check if "ok" == True (if not, use "error" property)
# 2. Reverse lookup userid from specified user name
# 3. Use channels[kk]["id"] item to generate list of channels
# 4. For each channel:
# 4.1. Check whether specified user is a member of that list
# 4.2. Show a list of channels that user is a member of
# 4.3. OR Show a list of channels that both users are a member of
###########################################################


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Checks Slack channels for membership in common with another user.')
    parser.add_argument('-t', '--token', metavar='TOKEN', type=str,
                        dest='user_token',
                        help='Specifies a user token to use, overrides a token in the root path')
    parser.add_argument('-n', '--username', type=str,
                        dest='username',
                        help='Specifies the user name to check against')
    parser.add_argument('-r', '--root-path', metavar='ROOTPATH', type=str,
                        dest='inputroot', default=DEFAULT_PATH,
                        help='Specifies root path for non-specified token and save folder (default: "$USER/")')
    parser.add_argument('-a', '--all-channels', , action='store_true',
                        dest='allchannels',
                        help='Show a list of all public channels that member is part of (default: only shared channels)')

    args = parser.parse_args()
    print "Token '%s'" % args.user_token
    print "Root path '%s'" % args.inputroot
    print "Name to check: ", args.username
    print "Output type: ", ["shared only", "all joined"][args.allchannels]


    # Load paths
    rootpath = loadPaths(args.inputroot)

    # Load token
    if args.user_token is not None:
        user_token = args.user_token
    else:
        user_token = loadToken(rootpath)
    print "User token: '%s'" % user_token

    # Check for co-membership
    if user_token is None:
        print "User token is None - must be set to use Slack API"
    else:
        print "Checking channels..."
        ch_list = checkChannels(user_token, args.username, args.allchannels)
        from pprint import pprint
        if not args.allchannels:
            print "Found shared channels:"
        else:
            print "Member is in the following channels:"

        # Print complete list of channel names
        # TODO: Mark co-channels when all membership is printed?
        for ch in ch_list:
            print ch

    print "Complete!"
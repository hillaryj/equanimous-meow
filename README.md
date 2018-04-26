# equanimous-meow

This repository contains several scripts and other resources for Slack, as described below.

[![Known Vulnerabilities](https://snyk.io/test/github/hillaryj/equanimous-meow/badge.svg)](https://snyk.io/test/github/hillaryj/equanimous-meow)

## Slack API token

# slackarchive.py

This is an archiving tool for Slack that archives all public channels.

*History-stitching* is a feature of this script. Stitching is performed by taking multiple possibly-overlapping history dumps from Slack and organizing them into one continuous history file. This process includes any prior continuous history file as a starting point.

This script is also able to make time-bounded excerpts of specific channels in human-readable text form (without reactji).

## Installation steps

1. Clone the repository locally
1. Generate a Slack API token for Slack you want to archive, if it doesn't already exist (below)

## Slack API token

A token is necessary to be able to use the Slack API.

Generate a Slack token at: https://api.slack.com/web

Without a command-line argument, a `token.txt` file with a Slack API token string is expected to be located in the root save folder at 

`DEFAULT_PATH/DEFAULT_SAVE_FOLDER/TOKEN_FILENAME`

Default path is: `$USER/SavedHistory/slacktoken.txt` or `~/SavedHistory/slacktoken.txt`

## How to run

Run the script with any options as below

`python slackarchive.py <arguments>`

### Arguments

`-t <token>`, `--token <token>`

Specify a (text) user token, overrides any saved token in root path

`-hist`, `--history-only`

Perform history-stitching only, no message retrieval. This can be done offline as it only uses local files.

`-arch`, `--archive-only`

Perform message retrieval/archiving only, skip history stitching. 

`-r <path>`, `--root-path <path>`

Specifies root path for non-specified token and save folder. Default is user home directory; `$USER/` or `~` depending on operating system.

`-d <foldername>`, `--dest-name <foldername>`

Specifies a name for the save folder at the root path. Default is `SavedHistory`.

## Making excerpts

Currently, this is not available from the command line, only by importing the script and running it inside a shell.

    from slackarchive import makeExcerpt
    makeExcerpt(channel, dest, token, tstart=0, tstop=-1, outfile=EXCERPT_FILENAME)

Creates a readable excerpt of a history file from the given start time to the stop time. Does not include reactji. The output generated looks like a chat transcript for easy reading.

### Inputs

Required:

- `channel`: the channel name or ID to excerpt from
- `dest`: destination directory (generally the top-level `SavedHistory` folder)
- `token`: Slack token string

Optional:

+ `tstart`: time to start excerpt (default: `0` = the beginning of time)
+ `tstop`: time to stop excerpt (default: `-1` = present)
+ `outfile`: optional filename (default: `EXCERPT_FILENAME` = `"_excerpt.txt"`)

NOTE: If `outfile` is used, put it in another dest folder or future history stitching will object to invalid formatting

## Future expansion

* Better JSON parsing and output formatting
* Additional command-line arguments for more customizable saving structures without editing code
* Safer input handling and perform proper unicode translation
* Improve message request response fault detection and add error handling to the different types of requests
* When loading directories, parse for specific exception type that occurs when attempting to `os.makedirs(<path>)` a path that exists so we don't ignore unexpected exceptions
* Add `@mention` name lookup when parsing text into user names inside messages
* When excerpting, make history stitching ignore invalid files
* Command-line support for making an excerpt

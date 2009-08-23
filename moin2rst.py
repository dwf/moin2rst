#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

###############################################################################
###############################################################################
# Import

import sys
import re
import os

from optparse import OptionParser, OptionGroup

from MoinMoin.request import RequestCLI
from MoinMoin.Page import Page
from MoinMoin import wikiutil

###############################################################################
###############################################################################
# Variables

"""
@var options: Options given on the command line
@type options: optparse.Values
"""
global options

###############################################################################
###############################################################################
# Functions

def parseOptions():
    """
    Sets options and returns arguments.

    @return: Name of the input page.
    @rtype: ( str, )
    """
    global options
    optionParser = OptionParser(usage="usage: %prog [option]... <page>",
                                description="""Convert a MoinMoin page to reStructuredText syntax.""")

    generalGroup = OptionGroup(optionParser, "General options")
    generalGroup.add_option("-d", "--directory",
                            default=".", dest="directory",
                            help="""Directory where the configuration of the wiki lives.

Defaults to ".".""")
    generalGroup.add_option("-r", "--revision",
                            default=0, type=int, dest="revision",
                            help="""Revision of the page to fetch (1-based).

Defaults to current revision.""")
    generalGroup.add_option("-u", "--url-template",
                            default="", dest="url_template",
                            help="""If the wiki given by -d/--directory is part of a wiki farm then this gives a
template to generate an URL from. The URL must be matched by one of the regular
expressions found in the variable "wikis" in the respective "farmconfig.py".

"url-template" may contain at most one '%'. The '%' is replaced by "page"
to form a valid URL. If '%' is omitted it is assumed at the end.

Defaults to the empty string.""")
    optionParser.add_option_group(generalGroup)

    argumentGroup = OptionGroup(optionParser, "Arguments")
    optionParser.add_option_group(argumentGroup)
    argument1Group = OptionGroup(optionParser, "page", """The page named "page" is used as input. Output is to stdout.""")
    optionParser.add_option_group(argument1Group)

    ( options, args, ) = optionParser.parse_args()

    if len(args) != 1:
        optionParser.error("Exactly one argument required")

    percents = re.findall("%", options.url_template)
    if len(percents) == 0:
        options.url_template += "%"
    elif len(percents) > 1:
        optionParser.error("-u/--url-template must contain at most one '%'")
    if not options.revision:
        options.revision = None

    return args

###############################################################################
###############################################################################
# Now work

if __name__ == '__main__':
    ( pageName, ) = parseOptions()

    # Needed so relative paths in configuration are found
    os.chdir(options.directory)
    # Needed to load configuration
    sys.path = [ os.getcwd(), ] + sys.path
    url = re.sub("%", re.escape(pageName), options.url_template)

    request = RequestCLI(url=url, pagename=pageName)

    Formatter = wikiutil.importPlugin(request.cfg, "formatter",
                                      "text_x-rst", "Formatter")
    formatter = Formatter(request)
    request.formatter = formatter

    page = Page(request, pageName, rev=options.revision, formatter=formatter)
    if not page.exists():
        raise RuntimeError("No page named %r" % ( pageName, ))

    page.send_page(request)

# TODO Extension for reStructuredText parser in MoinMoin:
#
#      * Support for role `macro` for using inline macros such as
#        ``:macro:`Date(...)``` to replace the macro-as-a-link-hack
#
#      * Expansion of @SIG@ and other variables must be done by the formatter
#
#      * Role `smiley` must expand to the respective smiley
#
#      * Otherwise for standard smileys there should be a default list of
#        substitutions
#
#      * Role `icon` must expand to the respective icon
#
#      * All style roles used should be supported
#
#      * Support for "#!" literal blocks would be nice

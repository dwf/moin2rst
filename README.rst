====
NAME
====

**moin2rst** -- convert a MoinMoin Wiki page to reStructuredText syntax

========
SYNOPSIS
========

Use MoinMoin action RenderAsRestructuredtext

   ``moin2rst.py [<option>]... page``

===========
DESCRIPTION
===========

**moin2rst** contains a MoinMoin formatter plugin which formats a MoinMoin Wiki page as reStructuredText.

It is accompanied by a MoinMoin action plugin to use it inside a MoinMoin Wiki and by a script to be used from the command line.

Action RenderAsRestructuredtext
-------------------------------

If the action plugin is installed each page should come with an additional action RenderAsRestructuredtext in the list of possible actions. Using this action renders the page as ``text/x-rst`` and returns it to the browser where it can be saved for further use.

See INSTALLATION_ for instructions for installing the action plugin.

Command line interface
----------------------

The command line interface is implemented by ``moin2rst.py`` and can be used together with an existing Wiki installation.

See OPTIONS_ for the options of the script.

=======
OPTIONS
=======

General options
---------------

-d directory                  Directory where the configuration file of the 
                              wiki lives, defaults to '..'. 
--directory=directory         Alternate form of ``-d``.
-r revision                   Revision of the page to fetch (1-based), defaults
                              to current revision
--revision=revision           Alternate form of ``-r``.
-u url-template               If the wiki given by ``-d``/``--directory`` is 
                              part of a wiki farm then this gives a template 
                              to generate an URL from. The URL must be matched 
                              by one of the regular expressions found in wikis 
                              in the respective ``farmconfig.py``.
--url-template=url-template   May contain at most one %. The % is replaced by 
                              page to form a valid URL. If % is omitted it is
                              assumed at the end. Defaults to the empty string.


Arguments
---------

* ``page``
  
  The page named page is used as input. Output is to stdout.

============
INSTALLATION
============

The package contains two plugins: The formatter plugin which is needed always and the action plugin which is needed if the formatter should be used as an action.

Formatter plugin
----------------

Simply put ``RenderAsRestructuredtext.py`` to MoinMoin's ``plugin/formatter`` directory.

Action plugin
-------------

Simply put ``RenderAsRestructuredtext.py`` to MoinMoin's ``plugin/action`` directory.

Command line interface
----------------------

The script does not need installation.

======
AUTHOR
======

Stefan Merten <smerten@oekonux.de> (original author)

David Warde-Farley <dwf at cs dot toronto dot edu> (updated for Moin 1.8.4)

=======
LICENSE
=======

**moin2rst** is licensed under the terms of the GPL. See http://www.gnu.org/licenses/gpl.txt

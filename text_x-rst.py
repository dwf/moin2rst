"""
    MoinMoin - Formatter for reStructuredText

    @copyright: 2008 Stefan Merten
    @license: GNU GPL, see COPYING for details.
"""

import re

from MoinMoin.parser.wiki import Parser
from MoinMoin.formatter.base import FormatterBase
from MoinMoin import wikiutil

# TODO Test with others than the standard MoinMoin "wiki" parser; in particular
#      test with reStructuredText pages

###############################################################################
###############################################################################
# Classes

class Style(object):
    """
    Description of a style as used in reStructuredText.
    """

    def __init__(self, name, startString=None, endString=None):
        """
        @param name: Name of this style.
        @param startString: Start string to use. If ``None`` a text role named
                            by `name` is used.
        @param endString: End string to use. If ``None`` a text role is used.
        """
        self._name = name
        self._startString = startString
        self._endString = endString

    def getMarkup(self, content):
        if self._startString is None:
            self._startString = u":%s:`" % ( self._name, )
        if self._endString is None:
            self._endString = u"`"
        return u"%s%s%s" % ( self._startString, content, self._endString, )

###############################################################################

class LinkStyle(Style):
    """
    Style to describe a link.
    """

    def __init__(self, name, url, formatter):
        Style.__init__(self, name)
        self._url = url
        self._formatter = formatter

    _reUrlPrefix = re.compile("^(%s):" % ( Parser.url_pattern, ))
    _reAttachmentPrefix = re.compile("^(%s):"
                                     % ( "|".join(Parser.attachment_schemas), ))
    _reWord = re.compile("^[-\w]+$")

    def getMarkup(self, description):
        url = self._url
        if self._url.startswith(u"#"):
            url = url[1:]
            if description.startswith(u"#"):
                description = description[1:]
        if description == url:
            if (self._reUrlPrefix.search(description)
                and not self._reAttachmentPrefix.search(description)):
                # Plain URL
                return u"%s" % ( description, )
        else:
            # If description is not the URL then it needs mapping
            found = [ pair
                      for pair in self._formatter._description_urls
                      if pair[0] == description ]
            if not found:
                self._formatter._description_urls.append(( description, url, ))
            elif found[0][1] == url:
                # Duplicate
                pass
            else:
                # Collision
                return u"`%s <%s>`__" % ( description, url, )
        if self._reWord.search(description):
            # Single word
            return u"%s_" % ( description, )
        else:
            # Multiple words
            return u"`%s`_" % ( description, )

###############################################################################

class Formatter(FormatterBase):
    """
    Format stuff as reStructuredText.
    """

    def __init__(self, request, **kw):
        # Initialize globally accessible flags
        FormatterBase.__init__(self, request, **kw)
        """
        Current indentation in characters.
        @type: int
        """
        self._indentation = 0
        """
        Was last line completed by a linefeed?
        @type: bool
        """
        self._lastLineComplete = True
        """
        Maps substitution names to images.
        @type: { str: str, ... }
        """
        self._substitution2Image = { }
        """
        Current list of strings collecting text which is meant to be output.
        @type: [ str, ... ]
        """
        self._collectors = [ ]
        """
        Current list of open lists.
        @type: [ Formatter.List, ... ]
        """
        self._openLists = [ ]
        """
        Text output since last linefeed.
        @type: str
        """
        self._sinceEOL = u""
        """
        Text output since last block start.
        @type: str
        """
        self._sinceBLK = u""
        """
        Current inline style.
        @type: Style
        """
        self._currentStyle = None
        """
        A space pends to be output.
        @type: bool
        """
        self._spacePending = u""
        """
        Maps descriptions to URLs
        @type: [ ( str, str, ), ... ]
        """
        self._description_urls = [ ]
        """
        Number of last footnote.
        @type: int
        """
        self._lastFootNote = 0
        """
        Maps numbers to footnote texts not output so far.
        @type: { int: str, ... ]
        """
        self._number2Footnote = { }
        """
        Name of the rendered page.
        @type: str
        """
        self._pageName = None
        """
        Depth of the table of contents or ``None``. ``0`` means unlimited.
        @type: int
        """
        self._contentsDepth = None

    # Helpers #################################################################
    
    # Linefeed policy
    # ---------------
    #
    # Every block can expect to start in a new, valid context. This means it
    # starts on a blank line and indentation will occur automatically.
    #
    # Indentation policy
    # ------------------
    #
    # Indentation is controlled by a block which requires indentation of its
    # children.

    def _indent(self, string):
        """
        Returns a string containing linefeeds with correct indentation.
        """
        # TODO A link as the only content of a line - such as in a category tag
        #      - results in a line starting with a space destroying indentation
        
        indentation = u" " * self._indentation
        result = u""

        # MoinMoin parser adds an ugly space to every paragraph - compensate
        # for this
        if self._spacePending:
            string = u" " + string
            self._spacePending = False
        if string.endswith(u" "):
            string = string[:-1]
            self._spacePending = True

        lines = string.split(u"\n")
        lastLine = lines.pop()
        for line in lines:
            # Compensate in complete lines
            if line.endswith(u" "):
                line = line[:-1]
            if self._lastLineComplete and line:
                # Indent new, non-empty line
                result += indentation
            result += line + u"\n"
            self._lastLineComplete = True

        if lastLine:
            # Last line never has a trailing linefeed
            if self._lastLineComplete:
                # Indent new, non-empty line
                result += indentation
            result += lastLine
            self._lastLineComplete = False

        return result

    def _output(self, string=u""):
        """
        Saves string to current collector or returns it indented.
        """
        self._sinceEOL += string
        self._sinceBLK += string
        if not self._collectors:
            return self._indent(string)

        self._collectors[-1] += string
        return u""

    # TODO Wiki parser creates empty paragraphs or paragraphs containing only
    #      a blank ending up in ugly empty lines. Problem, however, is that
    #      single spaces are compensated for only in `_indent()` and so empty
    #      paragraphs are hard to recognize.

    def _output_EOL(self, string=u""):
        result = self._output(string)
        if self._sinceEOL:
            # More than empty strings have been output
            result += self._output(u"\n")
        self._sinceEOL = u""
        return result

    def _output_EOL_BLK(self, string=u""):
        result = self._output_EOL(string)
        if self._sinceBLK:
            # More than empty strings have been output
            result += self._output(u"\n")
        self._sinceEOL = u""
        self._sinceBLK = u""
        return result

    _reColon = re.compile(":")
    _reBacktick = re.compile("`")

    def _quoteLinkDescription(self, description):
        if not self._reColon.search(description):
            return description
        if not self._reBacktick.search(description):
            return u"`%s`" % description
        return self._reColon.sub("\\:", description)

    # Misc ####################################################################
    
    def sysmsg(self, on, **kw):
        # TODO Needs improvement. Would be great if there would be a directive:
        #
        # .. system-message::
        if on:
            return self._output_EOL_BLK() + self.strong(on)
        else:
            return self.strong(on) + self._output_EOL_BLK()

    def lang(self, on, languageName):
        """
        Switch content language. Called from a class of macros where language
        names are used as macro names.
        
        """
        return self._output()

    # Document Level ##########################################################

    # These are not called by the parser but by `Page.send_page()` when it is
    # to be output

    _instructionPrefix = u"#"
    _instructionComment = u"#"

    _reHeaderLine2 = re.compile(r"^" + _instructionPrefix + r"("
                                + _instructionComment + r"|\w+)\s*(.*)$")

    _instructionFormat = u"format"
    _instructionKeeps = ( u"refresh", u"redirect", u"deprecated", u"acl",
                          u"language", )

    _instructionPragma = u"pragma"

    _rePragma2 = re.compile(r"(\S+)\s*(.*)$")
    _pragmaKeywords = u"keywords"
    _pragmaDescription = u"description"
    _pragmaSectionNumbers = u"section-numbers"

    def _header(self, instruction, arguments, force=False):
        """
        Output header line as part of the header.

        @param instruction: Name of the instruction.
        @type instruction: str
        @param arguments: String containing arguments. Leading white-space is
                          already removed.
        @type arguments: str
        @param force: If this is called internally and header is just to be
                      output.
        @type force: bool
        """
        if force:
            pass
        elif instruction == self._instructionFormat:
            # Suppress old format instruction
            return self._output()
        elif instruction in self._instructionKeeps:
            # Keep some processing instructions
            pass
        elif instruction == self._instructionComment:
            # Comments *in the header* must be kept as they are
            pass
        elif instruction == self._instructionPragma:
            ( pragma,
              pragmaArguments, ) = self._rePragma2.search(arguments).groups()
            if pragma == self._pragmaSectionNumbers:
                pragmaArguments = pragmaArguments.strip()
                if pragmaArguments == u"on":
                    pragmaArguments = u"1"
                elif pragmaArguments == u"off":
                    pragmaArguments = u"0"
                try:
                    self._contentsDepth = int(pragmaArguments)
                except ValueError:
                    self._contentsDepth = 0
                if not self._contentsDepth:
                    # Switched off
                    self._contentsDepth = None
                elif self._contentsDepth == 1:
                    self._contentsDepth = 0
                # Output postponed to `startContent`()
                return self._output()
            elif pragma in ( self._pragmaKeywords, self._pragmaDescription, ):
                # `meta` directive not supported in MoinMoin reST so output
                # these unchanged
                pass
            else:
                # Output unknown pragmas unchanged
                pass
        else:
            # Output unknown instructions unchanged
            pass
        return self._output_EOL(u"#%s %s" % ( instruction, arguments, ))

    def startDocument(self, pagename):
        # `Page.send_page()` filters out these processing instructions:
        #
        # `format`
        #   Need to be filtered here as well.
        # `refresh`
        #   Should be retained.
        # `redirect`
        #   Page is not rendered at all.
        # `deprecated`
        #   Should be retained.
        # `pragma`
        #   Is remembered by `request.setPragma(key, val)` for pragmas
        #   with arguments; should be retained.
        # `acl`
        #   Should be retained.
        # `language`
        #   Should be retained.
        # `#` (comment)
        #   Should be retained.
        #
        # Empty line, empty processing instruction (i.e. just "#") and unknown
        # processing instruction end header and are given to the parser.
        # `Page.getPageHeader()` returns all lines starting with "#", however.
        self._pageName = pagename
        headerLines = self.page.getPageHeader().split("\n")
        # Remove last linefeed and trailing garbage
        headerLines.pop()
        # Remove all empty lines which may have been inserted by
        # `getPageHeader()`
        headerLines = [ line
                        for line in headerLines
                        if line ]
        result = self._header(self._instructionFormat, "rst", force=True)
        for headerLine in headerLines:
            ( instruction,
              arguments, ) = self._reHeaderLine2.search(headerLine).groups()
            result += self._header(instruction, arguments)
        if result:
            result += self._output_EOL_BLK()
        return result

    def endDocument(self):
        return self._output()

    def startContent(self, content_id="content", **kw):
        result = self._output()
        if self._contentsDepth is not None:
            result += self._output_EOL(u".. sectnum::")
            if self._contentsDepth:
                self._indentation += 3
                result += self._output(u":depth: %d"
                                       % ( self._contentsDepth, ))
                self._indentation -= 3
            result += self._output_EOL_BLK()
        return result

    def endContent(self):
        result = u""

        result += self.macro(None, u"FootNote", None)

        description_urls = self._description_urls[:]
        while description_urls:
            sameUrls = [ description_urls.pop(0), ]
            url = sameUrls[0][1]
            i = 0
            while i < len(description_urls):
                if description_urls[i][1] == url:
                    sameUrls.append(description_urls.pop(i))
                else:
                    i += 1
            lastDescription = sameUrls.pop()[0]
            for ( description, url, ) in sameUrls:
                result += self._output_EOL(u".. _%s:"
                                           % ( self._quoteLinkDescription(description), ))
            result += self._output_EOL_BLK(u".. _%s: %s"
                                           % ( self._quoteLinkDescription(lastDescription),
                                               url, ))

        for ( substitution, image, ) in self._substitution2Image.items():
            result += self._output_EOL_BLK(u".. |%s| image:: %s"
                                           % ( substitution, image, ))
        if result:
            # Add a separator line
            result = self.comment(self._instructionPrefix
                                  + self._instructionComment + u" "
                                  + "#" * 76) + result

        return result

    # Links ###################################################################

    def _link(self, on, url=None):
        """
        @param url: Given only if `on`
        """
        if on:
            return self._handleInline(1, LinkStyle('link', url, self))
        else:
            return self._handleInline(0)

    def pagelink(self, on, pagename='', page=None, **kw):
        """
        Create a link to `pagename` or `page.page_name`. See
        `wikiutil.link_tag()` for possible keyword parameters.

        @param pagename: Name of the page.
        @param page: `page.page_name` is used unless `pagename`.
        @keyword generated: ???
        @keyword anchor: Fragment name - given only if `on`.
        """
        if kw.get('generated'): 
            return self._output()

        if on:
            if not pagename and page:
                pagename = page.page_name
            url = self.request.normalizePagename(pagename)
            urlPath = url.split("/")
            thisPath = self.request.normalizePagename(self.page.page_name).split("/")
            while urlPath and thisPath and urlPath[0] == thisPath[0]:
                # Delete common entries
                urlPath.pop(0)
                thisPath.pop(0)

            if len(thisPath) == 1 and len(urlPath) >= 1:
                # Siblings and their children differ starting at the last path
                # element
                url = u"%s%s" % ( wikiutil.PARENT_PREFIX, "/".join(urlPath), )
            elif len(thisPath) == 0 and len(urlPath) > 0:
                # Children and their children differ below the parent element
                url = u"%s%s" % ( wikiutil.CHILD_PREFIX, "/".join(urlPath), )

            anchor = kw.get('anchor', "")
            if anchor:
                url = u"%s#%s" % ( url, anchor, )
            return self._link(on, url)
        else:
            return self._link(on)

    def interwikilink(self, on, interwiki='', pagename='', **kw):
        return self.pagelink(on, "wiki:%s:%s" % ( interwiki, pagename, ))
            
    def url(self, on, url=None, css=None, **kw):
        """
        Create a link to some URL.

        @param url: The URL to link to. Given only if `on`.
        @param css: A tag identifying the type of URL: `external` or the
                    protocol for an URL, ``None`` for anchors.
        @keyword do_escape: Flag set to 0 if `url` came in brackets.
        """
        if on:
            return self._link(on, url)
        else:
            return self._link(on)

    # Attachments #############################################################

    def _attachment(self, type, url, text=None):
        link = u"%s:%s" % ( type, url, )
        pre = self._link(True, link)
        if not text:
            text = link
        body = self.text(text)
        post = self._link(False)
        return pre + body + post

    def attachment_link(self, url, text, **kw):
        return self._attachment(u"attachment", url, text)

    def attachment_image(self, url, **kw):
        return self._attachment(u"attachment", url)

    def attachment_drawing(self, url, text, **kw):
        return self._attachment(u"drawing", url, text)

    def attachment_inlined(self, url, text, **kw):
        return self._attachment(u"inline", url, text)

    def anchordef(self, name):
        """
        Inserts an invisible target.

        @param name: Name of the target.
        """
        return self._output_EOL_BLK(u".. _%s:"
                                    % ( self._quoteLinkDescription(name), ))

    #def line_anchordef(self, lineno):

    def anchorlink(self, on, name='', **kw):
        """
        Insert a link to a target on same page.

        @param name: Name of the target.
        """
        # TODO
        # Used in [[TableOfContents]] and [[FootNote]] which are replaced by
        # reST constructs
        return self._output()

    #def line_anchorlink(self, on, lineno=0):

    def image(self, src=None, **kw):
        """
        Insert an inline image.

        Also called if this is really an explicit link to an image in which
        case keyword value differs from `src`.

        @param src: URL of the image file.
        @keyword alt: As the HTML attribute.
        @keyword title: As the HTML attribute.
        """
        title = src
        for titleattr in ('title', 'html__title', 'alt', 'html__alt'):
            if kw.has_key(titleattr):
                title = kw[titleattr]
                break
        if title == src:
            # Part of an explicit link
            return self._output(u"%s" % ( title, ))
        else:
            self._substitution2Image[title] = src
            return self._output(u"|%s|" % ( title, ))

    _reTrailingBackslash = re.compile(r"\\$")

    def smiley(self, text):
        # Trailing backslashes don't work - replace by slashes
        text = self._reTrailingBackslash.sub("/", text)
        return self._output(u"|%s|" % ( text, ))

    def nowikiword(self, text):
        return self.text(text)

    # Text and text attributes ################################################

    def text(self, text, **kw):
        # TODO It would be long lines could be folded if they were folded in
        #      the original
        return self._output(text)

    # TODO reST needs inline markup separated from surrounding; must be
    #      reflected properly; difficult to do, however

    def _inlineBegin(self, style):
        self._collectors.append(u"")
        return self._output()

    def _inlineEnd(self, style):
        content = self._collectors.pop()

        ( preWhite, content,
          postWhite, ) = re.search("^(\s*)(.*?)(\s*)$", content,
                                   re.DOTALL).groups()
        if not content:
            # Skip empty inline markup
            return self._output(preWhite + postWhite)

        return self._output(preWhite + style.getMarkup(content) + postWhite)

    def _handleInline(self, on, style=None):
        """
        @param style: Inline style to use. Used only if `on`. Must be a new
                      instance for every call wiht `on`.
        @type style: Style
        """
        result = u""
        if on:
            style.previous = self._currentStyle
            if style.previous:
                # Suspend previous style
                result += self._inlineEnd(style.previous)
            result += self._inlineBegin(style)
            self._currentStyle = style
            return result
        else:
            style = self._currentStyle
            result += self._inlineEnd(style)
            self._currentStyle = style.previous
            if self._currentStyle:
                # Resume previous style
                result += self._inlineBegin(self._currentStyle)
            return result

    def strong(self, on, **kw):
        return self._handleInline(on, Style('strong', u"**", u"**"))

    def emphasis(self, on, **kw):
        return self._handleInline(on, Style('emphasis', u"*", u"*"))

    def underline(self, on, **kw):
        return self._handleInline(on, Style('underline'))

    def highlight(self, on, **kw):
        return self._handleInline(on, Style('highlight'))

    def sup(self, on, **kw):
        return self._handleInline(on, Style('superscript'))

    def sub(self, on, **kw):
        return self._handleInline(on, Style('subscript'))

    def strike(self, on, **kw):
        return self._handleInline(on, Style('strike'))

    def code(self, on, **kw):
        return self._handleInline(on, Style('literal', u"``", u"``"))

    def preformatted(self, on, **kw):
        # Maintain the accessible flag `in_pre`
        FormatterBase.preformatted(self, on)
        if on:
            # TODO Minmized styles should be supported
            result = self._output_EOL_BLK(u"::")
            self._indentation += 3
            return result
        else:
            self._indentation -= 3
            return self._output_EOL_BLK()

    def small(self, on, **kw):
        return self._handleInline(on, Style('small'))

    def big(self, on, **kw):
        return self._handleInline(on, Style('big'))

    # Special markup for syntax highlighting ##################################

    def code_area(self, on, codeId, codeType='code', show=0, start=-1, step=-1):
        if on:
            result = self._output_EOL_BLK(u"::")
            self._indentation += 3
            return result
        else:
            self._indentation -= 3
            return self._output_EOL_BLK()

    def code_line(self, on):
        if on:
            return self._output()
        else:
            return self._output_EOL()

    def code_token(self, tok_text, tok_type):
        return self._output()

    # Paragraphs, lines, rules ################################################

    def linebreak(self, preformatted=1):
        return self._output(u"\n")

    def paragraph(self, on, **kw):
        # Maintain the accessible flag `in_p`
        FormatterBase.paragraph(self, on)
        if on:
            return self._output()
        else:
            return self._output_EOL_BLK()

    def rule(self, size=0, **kw):
        return self._output_EOL_BLK(u"-------------------------")

    def icon(self, type):
        # Called by macro `Icon`
        result = self._handleInline(1, Style('icon'))
        result += self.text(type)
        result += self._handleInline(0)
        return result

    # Lists ###################################################################

    class List(object):
        """
        Abstract class for all lists
        """

        def __init__(self, formatter):
            self._formatter = formatter

        def begin(self):
            # Make sure a block starts here - may be missing for an inner list
            return self._formatter._output_EOL_BLK(u"")

        def end(self):
            return self._formatter._output(u"")

        def item(self, on, normal=False):
            """
            @param normal: Normal paragraph inside a list.
            """
            # TODO `normal` paragraphs without a preceding item just indent.
            #      This is meant as blockquoting and should work fine but may
            #      need explicit markup to end previous indentation.
            prefix = self.prefix()
            if normal:
                prefix = u" " * len(prefix)
            if on:
                result = self._formatter._output(prefix)
                self._formatter._indentation += len(prefix)
                return result
            else:
                self._formatter._indentation -= len(prefix)
                return self._formatter._output_EOL_BLK()

    class BulletList(List):

        def __init__(self, formatter):
            Formatter.List.__init__(self, formatter)

        def prefix(self):
            return u"* "

    class NumberList(List):

        def __init__(self, formatter, type, start):
            """
            @param type: Numbering type. One of ``None`` / ``1`` for arabic
                         numbers, ``I`` / ``i`` for uppercase and lowercase
                         roman numbers, ``A`` / ``a`` for uppercase and
                         lowercase letters.
            @param start: The ordinal to start with or ``None``.
            """
            Formatter.List.__init__(self, formatter)
            if type is None:
                type = u"1"
            self._type = type
            if start is None:
                start = 1
            self._start = start
            self._first = True

        def prefix(self):
            if self._first:
                self._first = False
                # TODO self._start must be used
                return u"%s. " % ( self._type, )
            # TODO Auto numbering could be used but step must be taken explicit
            return u"#. "

    class DefinitionList(List):

        def __init__(self, formatter):
            Formatter.List.__init__(self, formatter)

        def term(self, on):
            if on:
                return self._formatter._output()
            else:
                return self._formatter._output_EOL()

        def description(self, on):
            if on:
                self._formatter._indentation += 2
                return self._formatter._output()
            else:
                self._formatter._indentation -= 2
                return self._formatter._output_EOL_BLK()

    def number_list(self, on, type=None, start=None, **kw):
        if on:
            self._openLists.append(self.NumberList(self, type, start))
            return self._openLists[-1].begin()
        else:
            return self._openLists.pop().end()

    def bullet_list(self, on, **kw):
        if on:
            self._openLists.append(self.BulletList(self))
            return self._openLists[-1].begin()
        else:
            return self._openLists.pop().end()

    def listitem(self, on, **kw):
        if on and not self.in_p:
            # This is a workaround for a (seemingly) bug in `wiki.py`. In case
            # of a normal paragraph after a non-first list item there is no
            # closing of a paragraph. Condition catches this situation.
            # Pretending we are in a paragraph remedies that.
            self.in_p = True
        return self._openLists[-1].item(on, kw.get('style', "") == "list-style-type:none")

    def definition_list(self, on, **kw):
        if on:
            self._openLists.append(self.DefinitionList(self))
            return self._openLists[-1].begin()
        else:
            return self._openLists.pop().end()

    def definition_term(self, on, compact=0, **kw):
        # TODO May have empty content in which case it should be suppressed
        return self._openLists[-1].term(on)

    def definition_desc(self, on, **kw):
        # TODO May have empty content in which case it must be a comment in
        #      reST to make a definition item
        return self._openLists[-1].description(on)

    def heading(self, on, depth, **kw):
        self._indentation = 0
        if on:
            self._collectors.append(u"")
            return self._output()
        else:
            heading = "".join(self._collectors.pop())
            decoration = u"=-~:,."[depth - 1] * len(heading)
            return self._output_EOL(heading) + self._output_EOL_BLK(decoration)

    # Tables ##################################################################
    
    # TODO

    def table(self, on, attrs={}, **kw):
        if on:
            self._collectors.append(u"")
            return self._output()
        else:
            self._collectors.pop()
            return self._output_EOL_BLK(u"[Table not converted]")

    def table_row(self, on, attrs={}, **kw):
        return u""

    def table_cell(self, on, attrs={}, **kw):
        return u""

    # Dynamic stuff / plugins #################################################
    
    def macro(self, macroObj, name, argString):
        """
        @type macroObj: wikimacro.Macro
        @param name: Name of the macro.
        @param argString: Unparsed parameter list or ``None``.
        """
        # TODO [[ImageLink()]] should be supported explicitly
        # TODO [[Include()]] should be supported explicitly in simple cases
        if name == u"TableOfContents":
            string = u".. contents::"
            if argString:
                string += u" :depth: %s" % ( argString, )
        elif name == u"FootNote":
            if argString:
                self._lastFootNote += 1
                self._number2Footnote[self._lastFootNote] = argString
                string = u"[%d]_" % ( self._lastFootNote, )
            else:
                numbers = self._number2Footnote.keys()
                numbers.sort()
                result = u""
                for number in numbers:
                    result += self._output_EOL_BLK(u".. [%d] %s"
                                                   % ( number, self._number2Footnote[number], ))
                    del(self._number2Footnote[number])
                return result
        elif name in ( u"Anchor", u"BR", u"Icon", ):
            # These map to explicit methods
            return macroObj.execute(name, argString)
        else:
            # TODO Should use a `macro` text role for inline macro calls and
            #      the directive for block level macro calls
            string = u"`[[%s" % ( name, )
            if argString is not None:
                string += u"(%s)" % ( argString, )
            string += "]]`_"
        return self._output(string)

    def processor(self, processorName, lines, isParser=0):
        """
        Create output which should be renderded by a certain parser.

        @param lines: Lines to be parsed. Contains bang calling parser.
        """
        bangLine = lines.pop(0)
        return (self.comment(bangLine) + self.preformatted(1)
                + self.text("\n".join(lines)) + self.preformatted(0))

    # Probably unused
    #def dynamic_content(self, parser, callback, arg_list=[], arg_dict={},
    #                    returns_content=1):

    # Other ###################################################################
    
    def div(self, on, **kw):
        return u""
    
    def span(self, on, **kw):
        return u""
    
    def rawHTML(self, markup):
        result = self._output_EOL(".. raw:: html")
        self._indentation += 3
        if not isinstance(markup, basestring):
            markup = "\n".join(markup)
        result += self.text(markup)
        self._indentation -= 3
        result += self._output_EOL_BLK()
        return result

    def escapedText(self, on, **kw):
        return self._output()

    def comment(self, text):
        """
        Output comments contained in the page but also other processing
        instructions.
        """
        # Called by `Page.send_page()` only for processing instructions which
        # *it* doesn't consider to be part of the header. `wiki.Parser()` gives
        # excess processing instructions to this method. Because *all* header
        # lines are processed by `startDocument()` they are not handled here.
        ( instruction, text, ) = self._reHeaderLine2.search(text).groups()
        if instruction != self._instructionComment:
            return self._output()

        # Comments may appear anywhere in the page where they should be real
        # comments. In the header they need to be retained in the processing
        # instruction format.
        result = self._output(".. ")
        self._indentation += 3
        result += self.text(text)
        self._indentation -= 3
        result += self._output_EOL_BLK()
        return result

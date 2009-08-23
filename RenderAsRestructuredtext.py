"""
    MoinMoin - Render as reStructuredText action - redirects to the
    reStructuredText formatter

    @copyright: 2008 Stefan Merten
    @license: GNU GPL, see COPYING for details.
"""

from MoinMoin.Page import Page
from MoinMoin.util import MoinMoinNoFooter

def execute(pagename, request):
    url = Page(request, pagename).url(request, {'action': 'format',
                                                'mimetype': 'text/x-rst'}, 0)
    request.http_redirect(url)
    raise MoinMoinNoFooter

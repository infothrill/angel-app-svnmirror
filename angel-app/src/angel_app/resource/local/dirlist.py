# Copyright (c) 2001-2004 Twisted Matrix Laboratories.
# See LICENSE for details.

"""Directory listing."""

# system imports
import os
import urllib
import stat
import time

# twisted imports
from twisted.web2 import resource, http, http_headers

from angel_app.tracker.connectToTracker import connectToTracker
from angel_app.config import config
nodename = config.getConfig().get("maintainer","nodename")

def formatFileSize(size):
    if size < 1024:
        return '%i' % size
    elif size < (1024**2):
        return '%iK' % (size / 1024)
    elif size < (1024**3):
        return '%iM' % (size / (1024**2))
    else:
        return '%iG' % (size / (1024**3))

def formatClones(path):
    from angel_app.resource.local import basic
    
    try:
        return ", \n".join([              
                   '<a href="' + `clone`+ '">' + clone.host + '</a>'
                   for clone in basic.Basic(path).clones()])
    except:
        return ""

_STATISTICS_CACHE = [0, ""] # timestamp, buffer
def getStatistics():
    now = time.time()
    # query the tracker max once per hour:
    if _STATISTICS_CACHE[0] + 3600 < now:
        _STATISTICS_CACHE[0] = now
        _STATISTICS_CACHE[1] = connectToTracker()
    return "<br/>".join(_STATISTICS_CACHE[1].split("\n"))

def showStatistics():
    return """<p>%s</p>""" % getStatistics()

def showDisclaimer():
    return """<p class="disclaimer">
DISCLAIMER: Lifetime estimate assumes:
(i) Availability of digital communication, the absence of 
nuclear wars, major meteorite impacts and lethal pandemics. 
(ii) Maintenance of the ANGEL APPLICATION by etoy and
its contributors. 
<br/>
Please help us make these assumptions hold, by becoming an
<a href="http://www.etoy.com/fundamentals/etoy-share/">etoy.INVESTOR</a>.
</p>"""

def htmlHead(title):
    return """
<head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <title>ANGEL APPLICATION: %s</title>
    <link href="http://www.missioneternity.org/themes/m221e/css/main.css" rel="stylesheet" type="text/css" media="all" />
    <link rel="shortcut icon" href="http://www.missioneternity.org/themes/m221e/buttons/m221e-favicon.ico" type="image/x-icon" />
</head>""" % title

def showClones(path):
    return """
Recently seen replicas of this resource: 
<br/>%s""" % formatClones(path)

def showFile(even, link, linktext, size, lastmod, type):
    even = even and "even" or "odd"
    s = """
<tr class="%s">
    <td>
        <a href="%s">%s</a>
    </td>
    <td align="right">%s</td>
    <td>%s</td>
    <td>%s</td>
</tr>
""" % (even, link, linktext, size, lastmod, type)    
    return s

def showFileListing(data_listing):
    s = """
        <table border="0" cellpadding="0" cellspacing="0" id="angel-listing">
        <tr>
            <th>Filename</th>
            <th>Size</th>
            <th>Last Modified</th>
            <th>File Type</th>
        </tr>"""
    even = False
    for row in data_listing:
        s += '\n' + showFile(even, row["link"], row["linktext"], row["size"], row["lastmod"], row["type"])
        even = not even               
    s += "\n</table>"
    return s

def showDirectoryNavigation(linkList):
    return "<h3>%s</h3>" % linkList

def showBlurb():
    return """
    <p>
You are viewing a directory listing of the <a href="http://angelapp.missioneternity.org">ANGEL APPLICATION</a>,
an autonomous peer-to-peer file system developed for <a href="http://missioneternity.org">MISSION ETERNITY</a>.
</p>
<p>
Much like <a href="http://freenetproject.org/">freenet</a>, it decouples the storage 
process from the physical storage medium by embedding data in a root-less and therefore fail-safe social network. 
Unlike freenet, our primary goal is not anonymity, but 
data preservation.
</p>
"""

def showHelpPreserve():
    return """<h3>Like the content on this site?</h3>
<ul>
<li>
You can help preserving and sharing it (and add your own) 
by running the <a href="http://angelapp.missioneternity.org">ANGEL APPLICATION</a> 
on your computer.
</li>
<li>
The ANGEL APPLICATION fully supports WebDAV. You can make this directory part of your desktop.
E.g. on Mac OS X, simply type Command-K in the Finder, and "connect to" this page's URL.
</li>
</ul>"""

def showNavi():
    return """
<div id="topnavi">
    <ul>
        <li><a href="http://missioneternity.org/cult-of-the-dead/">MISSION ETERNITY</a></li>
        <li><a href="http://missioneternity.org/data-storage/">DATA STORAGE</a></li>
        <li><a href="http://missioneternity.org/angel-application/">ANGEL APPLICATION</a></li>
    </ul>
</div>
"""

def showHost(nodeName):
    return """
<strong>This node is hosted on: %s</strong>
""" % nodeName

def showResourceStatistics(path, nodeName):
    return """<h1>About This Network</h1>
<p>%s<br/>
    %s
</p>
    %s
""" % (showHost(nodeName), showClones(path), showStatistics())

class DirectoryLister(resource.Resource):
    def __init__(self, pathname, dirs=None,
                 contentTypes={},
                 contentEncodings={},
                 defaultType='text/html'):
        self.contentTypes = contentTypes
        self.contentEncodings = contentEncodings
        self.defaultType = defaultType
        # dirs allows usage of the File to specify what gets listed
        self.dirs = dirs
        self.path = pathname
        resource.Resource.__init__(self)

    def data_listing(self, request, data):
        if self.dirs is None:
            directory = os.listdir(self.path)
            directory.sort()
        else:
            directory = self.dirs

        files = []

        directory.sort()

        directory = [item for item in directory if not item.startswith(".")]

        for path in directory:
            url = urllib.quote(path, '/')
            fullpath = os.path.join(self.path, path)
            try:
                st = os.stat(fullpath)
            except OSError:
                continue
            if stat.S_ISDIR(st.st_mode):
                url = url + '/'
                files.append({
                    'link': url,
                    'linktext': path + "/",
                    'size': '',
                    'type': '-',
                    'lastmod': time.strftime("%Y-%b-%d %H:%M", time.localtime(st.st_mtime)),
                    'clones': formatClones(fullpath)
                    })
            else:
                from twisted.web2.static import getTypeAndEncoding
                mimetype, dummyencoding = getTypeAndEncoding(
                    path,
                    self.contentTypes, self.contentEncodings, self.defaultType)
                
                filesize = st.st_size
                files.append({
                    'link': url,
                    'linktext': path,
                    'size': formatFileSize(filesize),
                    'type': mimetype,
                    'lastmod': time.strftime("%Y-%b-%d %H:%M", time.localtime(st.st_mtime)),
                    'clones': formatClones(fullpath)
                    })

        return files

    def __repr__(self):  
        return '<DirectoryLister of %r>' % self.path
        
    __str__ = __repr__


    def render(self, request):
        title = "Directory listing for %s" % urllib.unquote(request.path)
        # TODO we need a better way to transform between url paths and file paths...
        pathSegments = ["/"] + urllib.unquote(request.path.strip("/")).split(os.sep)
        linkTargets = ["/"]
        accumulated = "/"
        for segment in pathSegments[1:]:
            accumulated += urllib.quote(segment) + "/"
            linkTargets.append(accumulated)
        linkList = '<a href="%s">%s</a>' % ("/", "/")  + \
            "/".join(['<a href="%s">%s</a>' % (linkTarget, pathSegment) 
                    for (linkTarget, pathSegment) in 
                    zip(linkTargets[1:], pathSegments[1:])
                    ])
    
        s= """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">"""
        s += htmlHead(title)
        s += """
        <body class="bg-still3">
        <div id="metanavi"><a href="http://www.etoy.com/">etoy.CORPORATION</a> 2007</div>
        <div id="content">
        <h1 class="rechts">
            <a href="http://www.missioneternity.org/">
                <img src="http://www.missioneternity.org/themes/m221e/images/m221e-logo2-o.gif" alt="" border="0" />
            </a>
        </h1>"""
              
        s += showResourceStatistics(self.path, nodename)
        s += showHelpPreserve()
        s += "</div>" # id content
        s += """<div id="bilder">"""
        s += """<h1>Directory Listing</h1>"""
        s += showBlurb()
        s += showDirectoryNavigation(linkList)
        s += showFileListing(self.data_listing(request, None))   
        s += showDisclaimer()
        s += "</div>" # id bilder
        s += "\n</body></html>"
        response = http.Response(200, {}, s)
        response.headers.setHeader("content-type", http_headers.MimeType('text', 'html'))
        return response

__all__ = ['DirectoryLister']

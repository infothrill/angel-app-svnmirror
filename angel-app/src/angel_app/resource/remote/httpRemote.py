import socket
from httplib import HTTPConnection
from logging import getLogger

from angel_app import version

log = getLogger(__name__)

USER_AGENT = 'Angel/%s' % version.getVersionString()

class HTTPRemote(object):
    """
    Lowest-level wrapper around HTTPConnection.
    """
    
    def __init__(self, host, port, path):
        """
        @rtype Clone
        @return a new clone
        """
        
        # the host name or ip
        self.host = host
        
        # a port number
        self.port = port
        
        # a path string. must be valid as part of an absolute URL (i.e. quoted, using "/")
        self.path = path                    
    
    def performRequestWithTimeOut(self, method = "HEAD", headers = {}, body = "", timeout = 3.0):
        """
        Perform a request with a timeout. 
        
        TODO: It would be nice if we could set timeouts on a per-socket basis. For the time being, it
        seems we have to operate with socket.setdefaulttimeout(), which is obviously a dangerous and
        annoying hack (since it applies to all future sockets). We need to make sure that in the end, 
        the default time out is set back to the original value (typically None). Since python2.4 does
        not yet support the finally clause, we have to do that in two places (i.e. in the try statement,
        if the request succeeds, in the catch statement otherwise).
        
        @see Clone.ping
        """
        if 'User-Agent' not in headers: headers['User-Agent'] = USER_AGENT # add default user agent
        conn = HTTPConnection(self.host, self.port)
        oldTimeOut = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        try:
            conn.connect()
            conn.request(
                 method, 
                 self.path,
                 headers = headers,
                 body = body
                 )
            # revert back to blocking sockets -- 
            socket.setdefaulttimeout(oldTimeOut)
            return conn.getresponse()
        except:
            # revert back to blocking sockets
            socket.setdefaulttimeout(oldTimeOut)
            # then re-raise the exception
            raise


    def performRequest(self, method = "GET", headers = {}, body = ""):
        """
        Perform an http request on the clone's host.
        
        TODO: add content-length headers
        
        TODO: add support for stream bodies.
        
        vinc: I'm not sure the urllib client supports stream arguments for the body. In either case, _performRequest
        is not only called for file pushing, but is a generic abstraction for any http request to the given host
        (HEAD, PROPFIND, GET, MKCOL, PROPPATCH). One might have to distinguish between string-type bodies such as used
        for the PROPFIND and PROPPATCH requests and stream type bodies. In either case, it seems possible and
        desirable to supply a "content-length" header.

        pol:    - httplib does NOT support stream bodies (as in python <=2.5)
                - httplib does add the content-length header automatically (as of python >=2.4)
                - urllib/urllib2 have similar problems (they rely on httlib), although
                    urllib2's design allows for extensions, so it could be
                    hooked in, but this would essentially mean writing our
                    own request() method (not relying on httplib) and going
                    down the rabbit hole on urlencoding/multipart mime content encoding etc.
                    
        vinc: I still keep getting hangs in the maintainer -- and I think we will never be able to guarantee the absence 
        thereof, which is a major pain. I'll make performRequest use a (long) timeout.
        """
        return self.performRequestWithTimeOut(method, headers, body, timeout = 10.0)

    def __str__(self):
        return "%s:%s%s" % (self.host, self.port, self.path)
    
    def __repr__(self):
        return "HTTPRemote('%s', '%s', '%s')" % (self.host, self.port, self.path)

def rangeHeader(startoffset, endoffset, rangetype = 'bytes'):
    """
    Utility method to generate the http header syntax for querying a range of bytes from a resource
    @param startoffset: offset in bytes to start at
    @param endoffset: offset in bytes to end at (including this byte!)
    @param rangetype: default 'bytes'
    """
    assert endoffset >= startoffset >= 0
    return "%s=%d-%d" % (rangetype, startoffset, endoffset)

if __name__ == '__main__':
    # example to use byte range headers:
    r = HTTPRemote("localhost", 6221, "/MISSION%20ETERNITY/ARCANUM-CAPSULES/STOWAWAY/E20C7ABCB7D1DB66/5f537c32663df4edad16377d55feb86a6b9cef45-E20C7ABCB7D1DB66.txt")
    
    byterangeheader = {'range' : rangeHeader( 4, 5 ) }
    resp = r.performRequest("GET", byterangeheader)
    print resp.getheaders()
    buf = resp.read()
    print len(buf)
    print "'%s'" % buf

    
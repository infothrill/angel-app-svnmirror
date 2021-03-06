import os
from logging import getLogger

from twisted.web2 import responsecode
from twisted.web2.http import HTTPError, StatusResponse
from twisted.python.failure import Failure
from twisted.internet.defer import deferredGenerator, waitForDeferred
from twisted.web2.stream import readIntoFile
from twisted.web2.dav.http import statusForFailure

from angel_app.singlefiletransaction import SingleFileTransaction
from angel_app.config.config import getConfig

log = getLogger(__name__)

class Putable(object):
    """
    A mixin class (for AngelFile) that implements put operations.
    """
    def _put(self, stream): 

        if not self.isWritableFile():
            message = "http_PUT: not authorized to put file: " + self.fp.path
            log.error(message)
            raise HTTPError(StatusResponse(responsecode.UNAUTHORIZED, message))
         
        response = waitForDeferred(deferredGenerator(self.__putDelete)())
        yield response
        response = response.getResult()
        
        xx  = waitForDeferred(deferredGenerator(self.__putFile)(stream))
        yield xx
        xx = xx.getResult()
        
        self._registerWithParent()
        
        xx = waitForDeferred(deferredGenerator(self._updateMetadata)())
        yield xx
        
        yield response
        
        
    def __putDelete(self):
        """
        Original comment from Wilfredo:
        
        Perform a PUT of the given data stream into the given filepath.
        @param stream: the stream to write to the destination.
        @param filepath: the L{FilePath} of the destination file.
        @param uri: the URI of the destination resource.
        If the destination exists, if C{uri} is not C{None}, perform a
        X{DELETE} operation on the destination, but if C{uri} is C{None},
        delete the destination directly.
        Note that whether a L{put} deletes the destination directly vs.
        performing a X{DELETE} on the destination affects the response returned
        in the event of an error during deletion.  Specifically, X{DELETE}
        on collections must return a L{MultiStatusResponse} under certain
        circumstances, whereas X{PUT} isn't required to do so.  Therefore,
        if the caller expects X{DELETE} semantics, it must provide a valid
        C{uri}.
        @raise HTTPError: (containing an appropriate response) if the operation
            fails.
        @return: a deferred response with a status code of L{responsecode.CREATED}
        if the destination already exists, or L{responsecode.NO_CONTENT} if the
        destination was created by the X{PUT} operation.
        """
        
        # TODO: actually do the above
        
        if os.path.exists(self.fp.path):
            self.remove()
            success_code = responsecode.NO_CONTENT
        else:
            success_code = responsecode.CREATED
        yield success_code
    
    def __putFile(self, stream):
        """
         Write the contents of the request stream to resource's file
        """

        try:
            tmppath = getConfig().get('common', 'repository-tmp')
        except KeyError:
            tmppath = None
        t = SingleFileTransaction(tmppath)
        try:
            safe = t.open(self.fp.path, 'wb')
            x = waitForDeferred(readIntoFile(stream, safe))
            yield x
            x.getResult()
        except Exception, e:
            raise HTTPError(statusForFailure(
                                             Failure(),
                "writing to tmpfile: %s" % (safe.path,)
                ))

        # it worked, commit the file:
        t.commit() # TODO: catch exception here!
        
        yield None

            
    def http_PUT(self, request):
        """
        Respond to a PUT request. (RFC 2518, section 8.7)
        """
        return deferredGenerator(self._put)(request.stream)
        
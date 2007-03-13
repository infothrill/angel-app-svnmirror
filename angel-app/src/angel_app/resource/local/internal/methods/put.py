from twisted.web2 import responsecode
from twisted.web2.http import HTTPError, StatusResponse
from angel_app import elements


from twisted.python.failure import Failure
from twisted.internet.defer import deferredGenerator, waitForDeferred
from twisted.web2.stream import readIntoFile
from twisted.web2.dav.http import statusForFailure

from twisted.web2.dav.fileop import checkResponse
from angel_app.log import getLogger
from angel_app.resource.local.internal.util import inspectWithResponse
import angel_app.singlefiletransaction
import os

log = getLogger(__name__)

class Putable(object):
    """
    A mixin class (for AngelFile) that implements put operations.
    """
    def _put(self, stream): 
       
        if not os.path.exists(self.fp.path):
            log.debug("adding new file at: " + self.fp.path)

        if not self.isWritableFile():
            message = "http_PUT: not authorized to put file: " + self.fp.path
            log.error(message)
            raise HTTPError(StatusResponse(responsecode.UNAUTHORIZED, message))
        
        log.debug("_put: deleting file at: " + self.fp.path)        
        response = waitForDeferred(deferredGenerator(self.__putDelete)())
        yield response
        response = response.getResult()
        log.debug("_put: return code for deleting file: " + `response`)
        
        xx  = waitForDeferred(deferredGenerator(self.__putFile)(stream))
        yield xx
        xx = xx.getResult()
        
        self._registerWithParent()
        
        xx = waitForDeferred(deferredGenerator(self._updateMetadata)())
        yield xx
        
        log.debug("return code for updating meta data: " + `response`)
        
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
        log.debug("Deleting file %s" % (self.fp.path,))
        
        # TODO: actually do the above
        
        if os.path.exists(self.fp.path):
            log.debug("deleting: " + self.fp.path)
            response = self.delete()
            log.debug("__putDelete: " + `response`)
            checkResponse(response, "delete", responsecode.NO_CONTENT)
            success_code = responsecode.NO_CONTENT
        else:
            log.debug("__putDelete, file does not exist, not deleted.")
            success_code = responsecode.CREATED
        yield success_code
    
    def __putFile(self, stream):
        """
         Write the contents of the request stream to resource's file
        """

        t = angel_app.singlefiletransaction.SingleFileTransaction()
        try:
            safe = t.open(self.fp.path, 'wb')
            x = waitForDeferred(readIntoFile(stream, safe))
            yield x
            x.getResult()
            log.debug("__putFile: read stream into tmpfile: " + safe.name)
        except:
            log.debug("failed to write to tmpfile: " + safe.name)
            raise HTTPError(statusForFailure(
                                             Failure(),
                "writing to tmpfile: %s" % (safe.path,)
                ))

        # it worked, commit the file:
        log.debug("committing tmpfile %s to file %s" % (`safe.name`, `self.fp.path`))
        t.commit() # TODO: catch exception here!
        
        log.debug("__putFile: done putting file stream: " + self.fp.path)
        yield None

            
    def http_PUT(self, request):
        """
        Respond to a PUT request. (RFC 2518, section 8.7)
        """
        return deferredGenerator(self._put)(request.stream)
        #return deferredGenerator(self._put)(request.stream).addCallback(inspectWithResponse(self))
        #return deferredGenerator(self._put)(request.stream).addCallback(nonblockingInspection(self))
        
from twisted.python import log
from twisted.web2 import responsecode, dirlist
from twisted.web2.http import HTTPError
from twisted.web2 import http, stream
from twisted.web2.dav.xattrprops import xattrPropertyStore
from twisted.web2.dav.element import rfc2518
from twisted.web2.dav import davxml
from angel_app import elements
from angel_app.config.common import rootDir

from zope.interface import implements
from angel_app.resource import IResource
from angel_app.resource.local.safe import Safe
from angel_app.resource.local.external.methods.proppatch import ProppatchMixin
from ezPyCrypto import key as ezKey
import os

from angel_app.contrib import uuid

DEBUG = False

class Basic(Safe):
    """
    An extension to Safe, that implements common metadata operations.
    """
    implements(IResource.IAngelResource)
    
    def __init__(self, path,
                 defaultType="text/plain",
                 indexNames=None):
        Safe.__init__(self, path, defaultType, indexNames)
        self._dead_properties = xattrPropertyStore(self)

    def contentAsString(self):
        if self.fp.isdir(): 
            return "directory"
        return self.fp.open().read()
    
    def contentLength(self):
        if not self.isEncrypted():
            return super(Safe, self).contentLength()
        else:
            # getting the content length for an encrypted
            # file requires decryption of the file.
            # let's just pretend we don't know
            return None
 
    def get(self, davXMLTextElement):
        """
        @return the metadata element corresponding to davXMLTextElement
        """
        if not self.fp.exists():
            DEBUG and log.err("AngelFile.getOrSet: file not found for path: " + self.fp.path)
            raise HTTPError(responsecode.NOT_FOUND)
        
        # TODO: for some reason, the xml document parser wants to split
        # PCDATA strings at newlines etc., returning a list of PCDATA elements
        # rather than just one. We only have tags of depth one anyway, so we
        # might as well work around this thing right here:
        return "".join([
                        str(child) for child in 
                       self.deadProperties().get(davXMLTextElement.qname()).children
                                                 ])
        
    def getXml(self, davXMLTextElement):
        """
        @return the metadata element corresponding to davXMLTextElement
        """
        if not self.fp.exists():
            DEBUG and log.err("AngelFile.getOrSet: file not found for path: " + self.fp.path)
            raise HTTPError(responsecode.NOT_FOUND)
        
        # TODO: for some reason, the xml document parser wants to split
        # PCDATA strings at newlines etc., returning a list of PCDATA elements
        # rather than just one. We only have tags of depth one anyway, so we
        # might as well work around this thing right here:
        return  self.deadProperties().get(davXMLTextElement.qname()).toxml()
        
    def getOrSet(self, davXmlTextElement, defaultValueString = ""):
        """
        the metadata element corresponding to davXMLTextElement, setting it to defaultValueString if not already present
        """
        try:
            return self.get(davXmlTextElement)
        
        except HTTPError:
            DEBUG and log.err("angelFile.Basic.getOrSet: initializing element " + `davXmlTextElement.qname()` + " to " + defaultValueString)
            self.deadProperties().set(davXmlTextElement.fromString(defaultValueString))
            self.fp.restat()
            return defaultValueString
       
    def revisionNumber(self):
        """
        @rtype int
        @return the revision number. if not already set, it is initialized to 1.
        """
        return int(self.getOrSet(elements.Revision, "1"))

    def isEncrypted(self):
        """
        @rtype boolean
        @return whether the file is encrypted. 
        """
        if not self.parent():
            # in the absence of other information, we default to non-encryption
            default = "0"
        else:
            # there's a parent resource: use this as default
            default = self.parent().isEncrypted() and "1" or "0"
            
        return int(self.getOrSet(elements.Encrypted, default)) == 0
    
    def isWriteable(self):
        """
        A basic AngelFile is writeable (by a non-local host) exactly if:
          -- the resource is corrupted, i.e. it does not verify()
          -- the resource does not exist but is referenced by its parent()
          
        @rtype boolean
        @return whether the basic AngelFile is writeable
        """
        if not self.verify(): return True
        
        pp = self.parent()
        if not self.exists() and pp.verify() and [self in pp.metaDataChildren()]: return True
        return False
    
    def verify(self):
        
        if not self.exists():
            return False
        
        try:
            pk = self.get(elements.PublicKeyString)
            cs = self.get(elements.ContentSignature)
            sm = self.signableMetadata()
            ms = elf.getOrSet(elements.MetaDataSignature)
        except:
            return False
        
        publicKey = ezKey()
        publicKey.importKey(pk)

        contentSignature = self.get(elements.ContentSignature)
        #DEBUG and log.err("verify(): signature: " + contentSignature)
        dataIsCorrect = publicKey.verifyString(
                                  self.contentAsString(),
                                  cs)
        DEBUG and log.err("data signature for file " + self.fp.path + " is correct: " + `dataIsCorrect`)
            
        metaDataIsCorrect = publicKey.verifyString(ms, sm)
        
        DEBUG and log.err("meta data signature for file " + self.fp.path + " is correct: " + `metaDataIsCorrect`)
            
        return dataIsCorrect and metaDataIsCorrect
    
    def uuid(self):
        """
        @see IResource
        """
        if not self.deadProperties().contains(elements.UUID.qname()):
            self.deadProperties().set(
                  elements.UUID(
                        str(
                            uuid.uuid5(
                               uuid.NAMESPACE_URL, 
                               self.fp.path.split(os.sep)[-1]))))
            
        return self.deadProperties().get(elements.UUID.qname())
    
    def referenced(self):
        # the root is always referenced
        if self.parent() is None: return True
        
        return self in self.parent().metaDataChildren()
    
    def exists(self):
        """
        @rtype boolean
        @return true, if the corresponding file exists and is referenced by the parent collection.
        """       
        return self.referenced() and self.fp.exists()

    def removeIfUnreferenced(self):
        """
        @rtype boolean
        @return true if the resource was deleted, false otherwise
        """
        import commands
        if self.fp.exists() and not self.exists():
            # this implies this resource is not referenced:
            assert(commands.getstatus("rm -rf %s", self.fp.path) == 0), \
                "Failed to remove unreferenced resource: %s" % self.fp.path
            return True
        
        return False
    
    def familyPlanning(self):
        """
        Remove all direct children that are not referenced.
        """
        self.findChildren("1")

    def findChildren(self, depth):
        """ 
        @rtype [Filepath]
        @return child nodes of this node. Optionally (and by default),
        child nodes which have the deleted flag set can be ignored.
        """
        
        return [
                cc for 
                cc in super(Basic, self).findChildren(depth) 
                if not cc[0].removeIfUnreferenced()
                ]

    def relativePath(self):
        DEBUG and log.err(self.fp.path.split(rootDir)[1])
        return self.fp.path.split(rootDir)[1]

    def parent(self):
        """
        @return this resource's parent
        """
        assert(self.fp.path.find(rootDir)) == 0, "Path (%s) lies outside of repository." % self.fp.path
        
        if self.fp.path == rootDir:
            # this is the root directory, don't return a parent
            return None
        
        return self.createSimilarFile( 
                                  self.fp.parent().path
                                  )

    def metaDataChildren(self):
        """
        The children of this resource as specified in the resource metadata.
        This may (under special circumstances) be different from the list
        of children as specified in the findChildren routine, since the former
        lists all children as found on the file system, while the latter lists
        all children registered with the angel app. In the case of an incomplete
        push update, the latter list contains children that are not present in
        the former.
        
        TODO: this needs some more work... href parsing, validation etc.
        
        @see isWritable
        @rtype [Basic] 
        @return The children of this resource as specified in the resource metadata.
        """
        try:
            foo = self.deadProperties().get(elements.Children.qname())
        except:
            return []
        DEBUG and log.err(foo.toxml())
        children = foo.children
        return [
                self.createSimilarFile(self.fp.path + os.sep + str(child.childOfType(davxml.HRef))) 
                for child in children
                ]


    def publicKeyString(self):
        
        DEBUG and log.err("retrieving public key string for: " + self.fp.path)
        
        try:
            return self.get(elements.PublicKeyString)           
        except:
            # no key set yet -- maybe we have a key handy for signign?
            try:
                keyString = self.secretKey.exportKey()
                DEBUG and log.err("initializing public key to: " + keyString)
                return self.getOrSet(elements.PublicKeyString, keyString) 
            finally:
                raise HTTPError(responsecode.FORBIDDEN)
 

    def signableMetadata(self):
        """
        Returns a string representation of the metadata that needs to
        be signed.
        """
        sm = "".join([self.getXml(key) for key in elements.signedKeys])
        DEBUG and log.err("signable meta data for " + self.fp.path + ":" + sm)
        return sm

    def render(self, req):
        """You know what you doing. override render method (for GET) in twisted.web2.static.py"""
        if not self.exists():
            return responsecode.NOT_FOUND

        if self.fp.isdir():
            return self.renderDirectory(req)

        return self.renderFile()

    def renderDirectory(self, req):
        if req.uri[-1] != "/":
            # Redirect to include trailing '/' in URI
            DEBUG and log.err("redirecting")
            return http.RedirectResponse(req.unparseURL(path=req.path+'/'))
        
        # is there an index file?
        ifp = self.fp.childSearchPreauth(*self.indexNames)
        if ifp:
            # render from the index file
            return self.createSimilarFile(ifp.path).render(req)
        
        # no index file, list the directory
        return dirlist.DirectoryLister(
                    self.fp.path,
                    self.listChildren(),
                    self.contentTypes,
                    self.contentEncodings,
                    self.defaultType
                ).render(req)

    def getResponse(self):
        """
        Set up a response to a GET request.
        """
        response = http.Response()         
        
        for (header, value) in (
            ("content-type", self.contentType()),
            ("content-encoding", self.contentEncoding()),
        ):
            if value is not None:
                response.headers.setHeader(header, value)
                
        return response
    
    def getResponseStream(self):        
        """
        The Basic AngelFile just returns the cypthertext of the file.
        """
        try:
            f = self.fp.open()
        except IOError, e:
            import errno
            if e[0] == errno.EACCES:
                raise HTTPError(responsecode.FORBIDDEN)
            elif e[0] == errno.ENOENT:
                raise HTTPError(responsecode.NOT_FOUND)
            else:
                raise
        
        return stream.FileStream(f, 0, self.fp.getsize())

    def renderFile(self):
        
        DEBUG and log.err("running renderFile")
        
        response = self.getResponse()
        response.stream = self.getResponseStream()
        DEBUG and log.err("done running renderFile")
        return response

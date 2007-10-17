from angel_app import elements
from angel_app.contrib.ezPyCrypto import key as ezKey
from angel_app.log import getLogger
from angel_app.resource import IResource
from angel_app.resource import util
from zope.interface import implements


log = getLogger(__name__)

class Resource(object):
    """
    Provide implementation of resource methods common to both local and remote resources.
    The key methods that need to be implemented are 
    -- getPropertyManager() which must return an object that behaves like a 
        twisted.web2.dav.xattrprops.xattrPropertyStore and handles resource metadata
        
    -- getContentManager() which must return a file-like object from which we can read the resource contents.
    """
    
    implements(IResource.IAngelResource)
    
    def __init__(self):
        pass
    
    def getPropertyManager(self):
        """
        @see: IReadOnlyPropertyManager
        """
        raise NotImplementedError("Must be provided by subclass")
    
    def getContentManager(self):
        """
        @see: IReadOnlyContentManager
        """
        raise NotImplementedError("Must be provided by subclass")

    def stream(self):
        """
        @return a stream-like object that has the read() and close() methods, to read the contents of the local resource
        """
        return self.getContentManager().stream()
    
    def isCollection(self):
        return self.getPropertyManager().isCollection()
    
    def findChildren(self):
        return self.getPropertyManager().findChildren()

    def contentLength(self):
        return self.getContentManager().contentLength() 
        
    def getProperty(self, element):
        """
        Return a resource property by element.
        """
        return self.getPropertyManager().get(element.qname())
       
    def revision(self):
        """
        @rtype int
        @return the revision number. if not already set, it is initialized to 1.
        """
        return int(str(self.getProperty(elements.Revision)))

    def isEncrypted(self):
        """
        @rtype boolean
        @return whether the file is encrypted. 
        """
        isEncrypted = self.getProperty(elements.Encrypted)
        return int(str(isEncrypted)) == 1

    def contentSignature(self):
        """
        @return: the checksum of the resource content
        """
        return str(self.getProperty(elements.ContentSignature))
    
    def metaDataSignature(self):
        """
        @return the signature of the signed metadata
        """
        return str(self.getProperty(elements.MetaDataSignature))


    def _dataIsCorrect(self):
        cs = self.contentSignature()
        if cs == self._computeContentHexDigest():
            log.debug("data signature for file '%s' is correct: %s" % (self.fp.path, cs))
            return True
        else:
            log.info("data signature for file '%s' is incorrect: %s" % (self.fp.path, cs))
            return False

    def _metaDataIsCorrect(self):

        publicKey = ezKey()
        publicKey.importKey(self.publicKeyString())
        
        sm = self.signableMetadata()
        ms = self.metaDataSignature()
        
        log.debug(ms)
        log.debug(sm)
        try:
            return publicKey.verifyString(sm, ms)
        except:
            log.info("Can not verify metadata %s against signature %s" % (sm, ms))
            return False
    
    def validate(self):
        return (self._dataIsCorrect() and self._metaDataIsCorrect())
    
    def _computeContentHexDigest(self):
        """
        @return hexdigest for content of self
        """
        hash = util.getHashObject()
        f = self.stream()
        bufsize = 4096 # 4 kB
        while True:
            buf = f.read(bufsize)
            if len(buf) == 0:
                break
            hash.update(buf)
        f.close()
        return hash.hexdigest()

    def resourceID(self):
        """
        @see IResource
        """ 
        return self.getProperty(elements.ResourceID)
    
    def exists(self):
        """
        @rtype boolean
        @return true, if the corresponding file exists. If the resource is not the root resource, it must additionally be
            referenced by the parent collection.
        """   
        raise NotImplementedError

    def clones(self):
        """
        Return the list of clones stored with this resource.
        
        Note that this will recursively initialize the clone field all parent resources, 
        until one parent is found that does have clones. Will raise a RuntimeError if the root node has no
        clones.
        
        @see propertyManager.inheritClones
        """
        from angel_app.resource.remote import clone
        clonesElement = self.getProperty(elements.Clones)
        return clone.clonesFromElement(clonesElement)

    def childLinks(self):
        return self.getProperty(elements.Children)


    def publicKeyString(self):
        """
        @return: the string representation of the resource's public key.
        """
        return str(self.getProperty(elements.PublicKeyString))
 
    def keyUUID(self):
        """
        @return a SHA checksum of the public key string. We only take the first 16 bytes to be convertible
        to a UUID>
        """
        return util.uuidFromPublicKeyString(self.publicKeyString())

    def sigUUID(self):
        """
        @return a SHA checksum of the resource's signature. We only take the first 16 bytes to be convertible
        to a UUID>
        """
        return util.uuidFromPublicKeyString(self.get(elements.MetaDataSignature))

    def signableMetadata(self):
        """
        Returns a string representation of the metadata that needs to
        be signed.
        """
        try:
            sm = "".join([self.deadProperties().get(key.qname()).toxml() for key in elements.signedKeys])
            return sm
        except Exception, e:
            raise

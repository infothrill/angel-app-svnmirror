from twisted.web2 import responsecode
from twisted.web2.dav.element import rfc2518
from twisted.web2.dav import davxml
from angel_app import elements
#from angel_app.resource.remote import util
from angel_app.resource import IResource
from zope.interface import implements
from angel_app.contrib.ezPyCrypto import key
from angel_app.log import getLogger
import urlparse

log = getLogger(__name__)

from httplib import HTTPConnection

from angel_app.config import config
AngelConfig = config.getConfig()
providerport = AngelConfig.getint("provider","listenPort")

class CloneError(Exception):
    def __init__(self,value):
        self.parameter=value
    def __str__(self):
        return repr(self.parameter)

class CloneNotFoundError(CloneError):
    pass

class Clone(object):
    """
    Provides methods for transparent access to frequently used clone meta data.
    """
    implements(IResource.IAngelResource)
    
    def __init__(self, host = "localhost", port = providerport, path = "/"):
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
        
        self.validatePath()
        self.validateHostPort()
        
        self.propertyCache = {}
        
    def validatePath(self):
        from urllib import url2pathname, pathname2url
        # if the path is valid, then the composition of url2pathname and pathname2url is the identity function
        if not pathname2url(url2pathname(self.path)) == self.path:
            raise CloneError("Invalid path for clone: " + `self.path`)

        if not len(self.path) > 0:
            raise CloneError("Need non-empty path for clone. Got: " + self.path)
        
        if not self.path[0] == "/":
            raise CloneError("Need absolute path for clone. Got: " + self.path)
        
    def validateHostPort(self):
        import urlparse
        # if the clone is valid, we must be able to reconstruct the host, port, path from the string representation
        url = urlparse.urlsplit("http://" + `self`)
        if not url[1] == self.host + ":" + `self.port`:
            raise CloneError("Invalid host for clone: " + `self`)
        # as of python 2.5, we will also be able to do this:
        # assert url.port == self.port
        
    def updateCache(self):
        response = self.propertiesDocument(elements.signedKeys + [elements.MetaDataSignature, rfc2518.ResourceType])
        responseElement = response.root_element.childOfType(rfc2518.Response)
        availableProperties = responseElement.childrenOfType(rfc2518.PropertyStatus)[0]
        # the second entry will contain the properties for which the request failed.
        
        properties = availableProperties.childOfType(rfc2518.PropertyContainer).children
        for property in properties:
            self.propertyCache[property.qname()] = property                            
        
    
    def checkForRedirect(self):

        response = self.__performRequest(method = "HEAD", body = "")
        if response.status == responsecode.MOVED_PERMANENTLY:
            log.info("clone received redirect: " + `self`)
            try:
                redirectURL = urlparse.urlparse(response.getheader("location"))
                path = redirectURL[2]
                assert path != ""
                self.path = path
                log.info("redirecting to: " + `path`)
            except:
                error = "redirection url invalid: " + `redirectURL`
                log.warn(error)
                raise CloneNotFoundError(error)
            
    
    def __eq__(self, clone):
        """
        @rtype boolean
        Comparison operator.
        """
        return self.host == clone.host and self.port == clone.port
    
    def __repr__(self):
        return self.host + ":" + `self.port` + self.path
    
    def __hash__(self):
        return `self`.__hash__()

    def __performRequest(self, method = "GET", headers = {}, body = ""):
        # a default socket timeout leads to socket.error: (35, 'Resource temporarily unavailable'), so we disable it
        #import socket
        #socket.setdefaulttimeout(60)
        log.debug("attempting " + method + " connection to: " + self.host + ":" + `self.port` + " " + self.path) 
        conn = HTTPConnection(self.host, self.port)
        conn.connect() 
        conn.sock.settimeout(10.0) # FIXME: implement a timeout on connect
        conn.request(
                 method, 
                 self.path,
                 headers = headers,
                 body = body
                 )
        
        return conn.getresponse()

  
    def stream(self):
        response = self.__performRequest()
        if response.status != responsecode.OK:
            raise "must receive an OK response for GET, otherwise something's wrong"
        return response
    
    
    def propFindAsXml(self, properties):
        """
        @rtype string
        @return the raw XML body of the multistatus response corresponding to the respective PROPFIND request.
        """  
        #log.debug("running PROPFIND on clone " + `self` + " for properties " + `properties` + " with body " + self.__makePropfindRequestBody(properties))
        resp = self.__performRequest(
                              method = "PROPFIND", 
                              headers = {"Depth" : 0}, 
                              body = makePropfindRequestBody(properties)
                              )

        data = resp.read()

        if resp.status != responsecode.MULTI_STATUS:
            if resp.status == responsecode.NOT_FOUND:
                raise CloneNotFoundError("Clone %s not found, response code is: %s, data is %s" % (self, `resp.status`, data) )
            else:
                raise CloneError("must receive a MULTI_STATUS response for PROPFIND, otherwise something's wrong, got: " + `resp.status` +\
                    data)

        #log.debug("PROPFIND body: " + data)
        return data
    
    def propertiesDocument(self, properties):
        """
        @rtype WebDAVDocument
        @return the properties as a davxml document tree.
        """
        xmlProps = self.propFindAsXml(properties)
        return davxml.WebDAVDocument.fromString(xmlProps)


    def propertyFindBodyXml(self, property):
        """
        @param property an WebDAVElement corresponding to the property we want to get
        @return the XML of a property find body as appropriate for the supplied property
        @rtype string
        """
        return self.propertiesDocument([property]
                         ).root_element.children[0].children[1].children[0].children[0].toxml()


    
    def uncachedPropertyFindBody(self, property):
        """
        @rtype string
        @return the body of a property consisting of just PCDATA.
        """
        log.info("Performing lookup for property " + `property.qname()` +" on remote host.")
        propertyDocument = self.propertiesDocument([property])
        log.debug("returned for property "  + `property.qname()` + ": " + propertyDocument.toxml())
        # points to the first dav "prop"-element
        properties = propertyDocument.root_element.children[0].children[1].children[0]
        
        return "".join([str(ee) for ee in properties.children[0].children])
    
    def propertyFindBody(self, property):
        """
        @rtype string
        @return the body of a property consisting of just PCDATA.
        
        TODO: this caching scheme could be much improved.
        """
        
        if property.qname() in self.propertyCache.keys():
            log.debug("property " + `property` + " returned from local cache.")
            properties = self.propertyCache[property.qname()]   
            return "".join([str(ee) for ee in properties.children])
        else:
            log.debug("property " + `property` + " not cached.")
            return self.uncachedPropertyFindBody(property)
    

    def exists(self): 
        """
        Existence does not imply validity.
        """
        try:
            response = self.__performRequest(method = "HEAD", body = "")
            return response.status == responsecode.OK
        except:
            return False       

    
    def ping(self):
        """
        If an HTTP request can be performed, the remote host is up.
        """
        try:
            response = self.__performRequest(method = "HEAD", body = "")
            return True
        except:
            return False  

    def isCollection(self):
         log.debug("isCollection(): " + self.propertyFindBody(rfc2518.ResourceType) + " " + rfc2518.Collection.sname())
         return self.propertyFindBody(rfc2518.ResourceType) == rfc2518.Collection.sname()
    
    
    def resourceID(self):
        return self.propertyFindBody(elements.ResourceID)
    
    
    def revision(self):
        """
        @rtype int
        @return the clone's revision number.
        """
        try:
            return int(self.propertyFindBody(elements.Revision))
        except:
            log.warn("no revision found on clone: " + `self`)
            return -1
    
    def publicKeyString(self):
        """
        @rtype string
        @return the public key string of the clone.
        """
        return self.propertyFindBody(elements.PublicKeyString)
    
    def metaDataSignature(self):
        """
        @rtype string
        @return the public key string of the clone.
        """
        return self.propertyFindBody(elements.MetaDataSignature)
    
    
    def validate(self):
        """
        @rtype boolean
        @return if the meta data of a given clone is internally consistent.
        """
        
        
        # TODO: this probably sucks rocks performance-wise, since for each
        # element, we generate a HTTP request...
        toBeVerified = "".join([
                                self.propertyFindBodyXml(element)
                                for element in elements.signedKeys
                                ])
        
        #log.debug("Clone: " + toBeVerified)
        
        pubKey = key()
        try:
            pubKey.importKey(self.publicKeyString())
            return pubKey.verifyString(
                                   toBeVerified, 
                                   self.metaDataSignature())
            
        except Exception, e:
            log.warn(`self` + ": validation failed. Exception: " + `e`)
            return False
        
        
        
    def cloneList(self):
        """
        @rtype [(string, int)]
        @return a list of (string hostname, int port) tuples of clones registered with this clone.
        """

        try:
            prop = self.propertiesDocument(
                                       [elements.Clones]
                                       ).root_element.children[0].children[1].children[0]
                                       
            return clonesFromElement(prop)
        except:
            return []

    def putFile(self, stream):
        """
        Push the file contents, after pushing the relevant properties of a local parent clone to the 
        remote parent clone via a PROPPATCH request.
        
        @see performPushRequest
        
        TODO: read the file lazily
        """
        resp = self.__performRequest(method = "PUT", body = stream.read())

    def mkCol(self):
        """
        Make a remote collection, after pushing the relevant properties of a local parent clone to the 
        remote parent clone via a PROPPATCH request.
        """
        resp = self.__performRequest(method = "MKCOL", body = "")
        log.debug("response on MKCOL: " + `resp.status`)


    def performPushRequest(self, localClone, elements = elements.requiredKeys):
        """
        Push the relevant properties of a local clone to the remote clone via a PROPPATCH request.
        @param elements is a list of property elements we want to push out to the remote clone
        """
        pb = makePushBody(localClone, elements)
        log.debug("pushing metadata:" + pb + " for clone " + `self`)
        resp = self.__performRequest(
                                     method = "PROPPATCH", 
                                     body = pb
                                     )
        
        # we probably ignore the returned data, but who knows
        data = resp.read()
        if resp.status != responsecode.MULTI_STATUS:
            if resp.status == responsecode.NOT_FOUND:
                raise CloneNotFoundError("Clone %s not found, response code is: %s, data is %s" % (`self`, `resp.status`, data) )
            else:
                raise CloneError("must receive a MULTI_STATUS response for PROPPATCH, otherwise something's wrong, got: " + `resp.status` +\
                    data)

   
def makePropfindRequestBody(properties):
    """
    @rtype string
    @return XML body of PROPFIND request.
    """
    return rfc2518.PropertyFind(
                rfc2518.PropertyContainer(
                      *[property() for property in properties]
                      )).toxml()
           
def makePushBody(localClone, elements = elements.requiredKeys):
    """
    Generate the DAVDocument representation of the required properties of the local clone.
    """
    
    def makeSetElement(elements):
        return rfc2518.Set(
                         rfc2518.PropertyContainer(element))
    
    
    for el in elements:
        log.debug("makePushBody: " + localClone.deadProperties().get(el.qname()).toxml())
        
    cc = Clone("localhost", providerport, localClone.relativeURL())
    pList = [makeSetElement(element) for element in
             [localClone.deadProperties().get(el.qname()) for el in elements]
              + [clonesToElement([cc])]]
    
    log.debug(`pList`)
    
    pu = davxml.PropertyUpdate(*pList)
    return pu.toxml()

def getClonesOf(clonesList):
    """
    TODO: this should probably be replaced by a generator
    
    @type clonesList [Clone]
    @param clonesList list of clones we want to get the clones from
    @rtype [Clone]
    @return list of clones of the clones in clonesList, except the clones stored on the localhost
    """
    cc = []
    for clone in clonesList:
        cc += [Clone(host, port) for host, port in clone.cloneList()]
    return cc

def getUncheckedClones(clonesList, checkedClones):
    """
    @rtype ([Clone], [Clone])
    @return (cc, checkedClones + cc), where cc ist the list of clones in clonesList which are not in checkedClones
    """
    cc = [clone for clone in clonesList if clone not in checkedClones]
    return cc, checkedClones + cc


def getMostCurrentClones(clonesList):
    """
    @rtype [Clone]
    @return the most current clones from the clonesList
    """
    newest = max([clone.revision() for clone in clonesList])    
    return [clone for clone in clonesList if clone.revision() == newest]


def splitParse(cloneUri):
    host, rest = cloneUri.split(":")
    fragments = rest.split("/")
    port = int(fragments[0])
    
    if len(fragments) > 1:
        return host, port, "/" + "/".join(fragments[1:])
    
    return (host, port)

def cloneFromGunk(gunk):
    assert len(gunk) > 1
    assert len(gunk) < 4
    if len(gunk) == 2: return Clone(gunk[0], gunk[1])
    else: return Clone(gunk[0], gunk[1], gunk[2])
    
    
def cloneFromElement(cc):
    """
    Takes an child element of the Clones element and returns a Clone instance.
    """
    return cloneFromGunk(splitParse(str(cc.children[0].children[0])))


def clonesFromElement(cloneElement):
    """
    Takes a Clone element and returns a list of corresponding Clone instances
    """
    return [cloneFromElement(cc) for cc in cloneElement.children]

def clonesToElement(cloneList):
    """
    Takes a list of clones and generates a Clones element from it.
    """
    return elements.Clones(*[
                    elements.Clone(rfc2518.HRef(`cc`)) for cc in cloneList
                    ])
    
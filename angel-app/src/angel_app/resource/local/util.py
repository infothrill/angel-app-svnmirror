legalMatters = """
 Copyright (c) 2006, etoy.VENTURE ASSOCIATION
 All rights reserved.
 
 Redistribution and use in source and binary forms, with or without modification, 
 are permitted provided that the following conditions are met:
 *  Redistributions of source code must retain the above copyright notice, 
    this list of conditions and the following disclaimer.
 *  Redistributions in binary form must reproduce the above copyright notice, 
    this list of conditions and the following disclaimer in the documentation 
    and/or other materials provided with the distribution.
 *  Neither the name of etoy.CORPORATION nor the names of its contributors may be used to 
    endorse or promote products derived from this software without specific prior 
    written permission.
 
 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY 
 EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES 
 OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT 
 SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, 
 SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT 
 OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) 
 HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
 OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS 
 SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. 
"""

author = """Vincent Kraeutler, 2006"""

from urllib import quote, unquote
from urlparse import urlsplit
from os import sep

# get config:
from angel_app.config import config
AngelConfig = config.getConfig()
repository = AngelConfig.get("common","repository")

def resourceFromURI(uri, resourceClass):
    
    (scheme, host, path, query, fragment) = urlsplit(uri)
    segments = path.split("/")
    assert segments[0] == "", "URL path didn't begin with '/': %s" % (path,)
    segments = map(unquote, segments[1:])
    path = repository + sep + sep.join(segments)
    return resourceClass(path)

def getHashObject():
    """
    Returns an object that can create SHA-1 hash values when feeded with data
    using the update() method.
    This method exists solely for python version compatibility.
    """
    from platform import python_version_tuple
    (major,minor,patchlevel) = python_version_tuple()
    major = int(major)
    minor = int(minor)
    if (major >=2 and minor < 5 ):
        import sha
        obj = sha.new()
    else:
        import hashlib
        obj = hashlib.sha1()
    return obj

def getHexDigestForFile(fp):
    hash = getHashObject()
    if fp.isdir(): 
        hash.update("directory") # directories always have the same signature
    else:
        myFile = fp.open()
        bufsize = 4096 # 4 kB
        while True:
            buf = myFile.read(bufsize)
            if len(buf) == 0:
                break
            hash.update(buf)
        myFile.close()
    return hash.hexdigest()




# -*- test-case-name: twisted.web2.dav.test.test_copy,twisted.web2.dav.test.test_move -*-
##
# Copyright (c) 2006 etoy.CORPORATION, Inc. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Vincent Kraeutler, vincent@etoy.com
##

"""
WebDAV MOVE method. Very much incomplete.
"""

DEBUG = True

__all__ = ["http_MOVE"]

from twisted.python import log
from twisted.web2.dav.method.copymove import http_MOVE as hm
from angel_app.resource.local.util import resourceFromURI

class moveMixin:
    
    def http_MOVE(self, request):
        
        
        def changeRegister(response):
            
            self._deRegisterWithParent()
            
            destination_uri = request.headers.getHeader("destination")
            DEBUG and log.err("changeRegister: " + `self.__class__`)
            destination = resourceFromURI(destination_uri, self.__class__)
            destination._registerWithParent()
        
            return response
        
        return hm(self, request).addCallback(changeRegister)
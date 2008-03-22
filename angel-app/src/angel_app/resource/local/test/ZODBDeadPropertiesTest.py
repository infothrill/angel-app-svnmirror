"""
Tests for local resource.
"""

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

author = """Vincent Kraeutler 2007"""

from angel_app.config import config
from angel_app.log import initializeLogging
from angel_app.resource.IDeadPropertyStore import IDeadPropertyStore
from angel_app.resource.local import ZODBDeadProperties
from angel_app.resource.local.internal.resource import Crypto
from angel_app.resource.local.propertyManager import PropertyManager
import os
import shutil
import unittest
import zope.interface.verify
from angel_app import elements

AngelConfig = config.getConfig()
repositoryPath = AngelConfig.get("common","repository")

loghandlers = ['console'] # always log to file
initializeLogging("test", loghandlers)

class ZODBTest(unittest.TestCase):
    
    testDirPath = os.path.sep.join([repositoryPath, "TEST"])
    testFilePath = os.path.sep.join([testDirPath, "file.txt"])
    testText = "lorem ipsum"
    
    def makeTestDirectory(self):
        self.testDirectory = Crypto(self.testDirPath) 
        if not self.testDirectory.fp.exists():
            os.mkdir(self.testDirPath)
        self.testDirectory._registerWithParent()
        self.testDirectory._updateMetadata()
    
    def setUp(self):
        self.makeTestDirectory()
        self.testStore = ZODBDeadProperties.ZODBDeadProperties(self.testDirectory)
        
    def testInterfaceCompliance(self):
        """
        Verify interface compliance.
        """
        assert IDeadPropertyStore.implementedBy(ZODBDeadProperties.ZODBDeadProperties)
        assert zope.interface.verify.verifyClass(
                                                 IDeadPropertyStore, 
                                                 ZODBDeadProperties.ZODBDeadProperties)   
        
    def testLookup(self):
        """
        Lookup a resource. Will hang if no running ZEO instance.
        """
        root = Crypto(repositoryPath)
        zodb = ZODBDeadProperties.getZODBDefaultRoot()
        ZODBDeadProperties.lookup(zodb, root)
        assert "repository" in zodb
        #print zodb
        for cc in root.children():
            ZODBDeadProperties.lookup(zodb, cc)
            print cc.resourceName(), zodb
            assert cc.resourceName() in zodb["repository"].children
            
    def testModify(self):
        myProps = ZODBDeadProperties.ZODBDeadProperties(self.testDirectory)
        myProps.list()
        myElement = elements.Revision("0")
        myProps.set(myElement)
        assert myProps.contains(myElement.qname())
        print myProps.list()
        assert 1 <= len(myProps.list())
        assert myProps.contains(myElement.qname())
        ll = len(myProps.list())
        myProps.delete(myElement.qname())
        assert ll - 1 == len(myProps.list())
        
    def testDelete(self):
        td = self.testDirectory
        td.remove()
        key = td.resourceName()
        dict = self.testDirectory.parent().getPropertyManager().store.zodb.children
        assert key not in dict
        
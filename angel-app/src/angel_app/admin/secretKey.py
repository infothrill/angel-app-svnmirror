"""
Utilities for creating the default repository directory layout.
"""

import os
from angel_app.config import config

AngelConfig = config.getConfig()
from angel_app.log import getLogger
log = getLogger("master")

def createKey(filePath = os.path.join(AngelConfig.get("common","keyring"), "default.key")):
    kk = ezKey()
    # TODO: make key size configurable
    kk.makeNewKeys() 
    log.info("creating new key in file: " + `filePath`)
    open(filePath, 'w').write(kk.exportKeyPrivate())

def createAtLeastOneKey():
    from angel_app.contrib.ezPyCrypto import key as ezKey
    
    # where the keys are located
    keyDirectory = AngelConfig.get("common", "keyring")
    
    # the keys that already exist
    keyFiles = os.listdir(keyDirectory)
    
    log.info("current key files: " + `keyFiles`)
    
    # make a key if we don't have any keys yet
    if keyFiles == []:
        createKey()        
        # make sure the new key is globally visible
        from angel_app.resource.local.internal import resource
        resource.reloadKeys()

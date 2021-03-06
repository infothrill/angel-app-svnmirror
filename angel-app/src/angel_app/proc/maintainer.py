import sys

def bootInit():
    """
    Method to be called in __main__ before anything else. This method cannot rely on any
    framework being initialised, e.g. no logging, no exception catching etc.
    """    
    pass

def postConfigInit():
    """
    Run this method after the config system is initialized.
    """
    from angel_app.admin.directories import makeDirectories
    makeDirectories()

    # setup our internal temporary path for files:
    from angel_app import singlefiletransaction
    singlefiletransaction.setup()

def dance(options):
    from angel_app.log import getLogger
    from angel_app.config import config
    from angel_app.maintainer import client
    from angel_app.admin import initializeRepository

    log = getLogger("maintainer")

    log.debug("initializing repository")
    if not initializeRepository.initializeRepository():
        log.warn("Going to quit because initializeRepository failed.")
        return 1

    angelConfig = config.getConfig()
    repository = angelConfig.get("common", "repository")
    log.info("starting maintenance loop at '%s'" % repository)
    log.growl("User", "MAINTENANCE PROCESS", "Started.")
    try:
        client.maintenanceLoop()
    except Exception, e:
        log.critical("An exception occurred in the maintenance loop", exc_info = e)
        log.growl("User", "MAINTENANCE PROCESS", "Crash.")
        return -1
    else:
        log.growl("User", "MAINTENANCE PROCESS", "Quit.")
        log.info("Quit")
        return 0


def boot():
    bootInit()
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-d", "--daemon", dest="daemon", help="daemon mode?", default='')
    parser.add_option("-c", "--config", dest="config", help="alternative config file", default=None)
    parser.add_option("-l", "--log", dest="networklogging", help="use network logging?", action="store_true" , default=False)
    (options, dummyargs) = parser.parse_args()

    # setup/configure config system
    from angel_app.config.config import getConfig
    angelConfig = getConfig(options.config)
    postConfigInit()
    angelConfig.bootstrapping = False

    appname = "maintainer"
    # setup/configure logging
    from angel_app.log import initializeLogging
    loghandlers = [] # default: no handlers, add as needed below
    if len(options.daemon) > 0:
        loghandlers.append('socket')
    else:
        if (options.networklogging):
            loghandlers.append('socket')
        else:
            loghandlers.append('console')
            if angelConfig.getboolean('common', 'desktopnotification'):
                loghandlers.append('growl')
    if 'socket' not in loghandlers: # if there is no network logging, then log at least to file:
        loghandlers.append('file')
    initializeLogging(appname, loghandlers)

    if angelConfig.get(appname, 'enable') == False:
        from angel_app.log import getLogger
        getLogger().info("%s process is disabled in the configuration, quitting." % appname)
        sys.exit(0)

    if len(options.daemon) > 0:
        from angel_app.proc import daemonizer
        daemonizer.startstop(action=options.daemon, stdout=appname+'.stdout', stderr=appname+'.stderr', pidfile=appname+'.pid')

    return options
                

if __name__ == '__main__':
    options = boot()
    sys.exit(dance(options))
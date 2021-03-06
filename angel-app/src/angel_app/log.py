"""
Logger for angel-app
"""

legalMatters = """See LICENSE for details."""
__author__ = """Paul Kremer, 2007"""

"""
This is a module that provides wrapping services for logging.
It is responsible for tying together possibly different logging engines,
initializing them and configuring them ...
It uses the logging module from the python standard library and monkey patches
the standard logging.getLogger method.

Logfiles are in $HOME/.angel_app/log/
The directory $HOME/.angel_app/log/ will automatically get created if needed.

See the documentation of the  
<a href="http://docs.python.org/lib/module-logging.html">python logging module</a>
and  
<a href="http://twistedmatrix.com/projects/core/documentation/howto/logging.html">twisted.log</a>
for more information.
"""

import os
import re
import logging

from twisted.python import log as twistedlog

from angel_app.config.config import getConfig


DEBUG = False # this will start printing to the console if set to True
"""
Defaults for the logging backend (RotatingFileHandler)
"""
log_maxbytes = 1024 * 1024 # each logfile has a max of 1 MB
log_backupcount = 7        # max 7 "rotated" logfiles

angelConfig = getConfig()
loggers = {}

appname = "default" # this string is prepended with a trailing dot to all log messages

def getLogger(area = ""):
    """
    the most important method in here. Call this to get a logger object, so
    you can log a message using one of the methods 'error' 'info' 'critical' 'debug' ...
    See the python 'logging' module documentation for more information.
    Additionally, this method can be called using an additional parameter called 'area'.
    The area is used to tag the logged messages, so it is easier to read the log.
    The value of area really can be any string you like, it might make sense to use
    for example the class/module name you are in.
    In logged messages, the area appears just behind the application name, prepended with a dot:
    "presenter.config" means the log message is from application presenter and area config.
    """
    if len(area) > 0:
        area = appname+ '.' + area
    else:
        area = appname
    return _getLogger(area)

# keep a reference to the original std library getLogger method
# and monkey patch on startup:
_std_getLogger = logging.getLogger
logging.getLogger = getLogger

def _getLogger(area = ''):
    if not loggers.has_key(area):
        loggers[area] = _std_getLogger(area)
    return loggers[area]


def getAngelLogPath():
    angelLogPath = angelConfig.get("common", "logdir")
    return angelLogPath


def getAngelLogFilename():
    return getAngelLogFilenameForApp(appname)

def getAngelLogFilenameForApp(app):
    return os.path.join(getAngelLogPath(), app + ".log")

class AngelLogger(logging.getLoggerClass()):
    "We use our own Logger class so we can introduce additional logger methods"
    def growl(self, type, title, msg):
        """
        Method to explicitly send a notification to the desktop of the user
        
        Essentially, this method is an alternative to using loglevels for the decision whether the
        message should be a desktop notification or not. 
         
        @param type: a notification type
        @param title: the title of the notification
        @param msg: the actual message
        """
        # before explicitly growling, check wether it's enabled:
        if not angelConfig.getboolean('common', 'desktopnotification'): return
        # otherwise, try to growl and don't fail if it's not working, but say so in the log
        try:
            g = getAngelGrowlNotifier()
            g.notify(type, title, msg)
        except Exception, e:
            getLogger().debug("Growling failed", exc_info = e)
            pass
        #self.info("%s %s" % (title, msg))
        
logging.setLoggerClass(AngelLogger)
    
class AngelLogFilter(logging.Filter):
    def __init__(self, f):
        self.f = f
    def filter(self, record):
        if DEBUG: print "HIT THE FILTER"
        stringobj = str(record.msg) # this enables us to log all sorts of types, by using their string representation
        record.msg = stringobj.replace("\n", "\\n") # TODO: this is not safe enough, there might be control chars, and record.args also can contain bad data
        if record.levelno >= self.f[1]:
            if DEBUG: record.msg = "PASS FILTER" + record.msg
            return True
        else:
            if DEBUG: record.msg = "STOP FILTER" + record.msg
            return False
        return True

class AngelLogTwistedFilter(logging.Filter):
    def __init__(self):
        self.re = re.compile("HTTPChannel,\d+,.*: (PROPFIND )|(HEAD )|(OPTIONS )\/.* HTTP\/1\.1")
    def filter(self, record):
        if DEBUG: print "TWISTED LOGFILTER"
        if self.re.search(record.msg):
            return False
        else:
            return True


def initializeLogging(appname = "default", handlers = ['console']):
    """
    This is the single-step routine to initialize the logging system.
    """
    import angel_app #hmja, stupid, but needed to set the module variable, afaik
    angel_app.log.appname = appname
    setup()
    for handler in handlers:
        enableHandler(handler)
    getReady()

def setup():
    """
    setup() creates the needed internal directory structure for logging
    (.angel_app/log/). It must be called once during bootstrap.
    """
    __configLoggerBasic()
    angelLogPath = getAngelLogPath()
    if not os.path.exists(angelLogPath):
        os.mkdir(angelLogPath)
    elif not os.path.isdir(angelLogPath):
        raise Exception, "Filesystem entry '%s' occupied, cannot create directory here." % angelLogPath

def enableHandler(handlername, handler = None):
    if handlername == "console":
        __addConsoleHandler()
    if handlername == "growl":
        __addGrowlHandler()
    if handlername == "socket":
        __addSocketHandler()
    if handlername == "file":
        __addRotatingFileHandler()
    if handlername == "wx":
        logging.getLogger().addHandler(handler)

def removeHandler(handler):
    logging.getLogger().removeHandler(handler)

def getReady():
    """
    must be called after setup() and after enabling handlers with enableHandler()
    """
    
    ourTwistedLogger = getLogger("twisted")
    ourTwistedLogger.addFilter( AngelLogTwistedFilter() )
    filters = getLoggingFilters()
    for f in filters:
        logger = _getLogger(f[0])
        logger.addFilter( AngelLogFilter(f) )
        
    twistedlog.startLoggingWithObserver(logTwisted, setStdout=0)


def logTwisted(eventDict):
    """
    callback for the twisted logging engine
    """
    ourTwistedLogger = getLogger("twisted")
    # to make sure this log observer for twisted never gets removed, we
    # must ensure never to throw an exception from it, so we encapsulate it in a try block:
    try:
        #print "START ---------"
        #print eventDict
        #print "END ---------"
        # TODO : beautify more... see twisted.python.log for details on how to implement that
        # according to the twisted doc, the eventDict always has the 'isError' key set to indicate wether it is an error or not
        isError = eventDict['isError']
        # buggy twisted: sometimes it also has the eventDict-key isErr:
        if eventDict.has_key('isErr'):
            isError = eventDict['isErr']
        isWarning = False
        if eventDict.has_key('warning'):
            isWarning= True
    
        if isError and eventDict.has_key('failure'):
            import string
            ourTwistedLogger.critical(eventDict.get('why') or 'Unhandled Error')
            if callable(getattr(eventDict['failure'], 'getTraceback')):
                ourTwistedLogger.critical("Exception:", exc_info = eventDict['failure'])
                for line in string.split(eventDict['failure'].getTraceback(), '\n'):
                    #print "line: %s" % line
                    ourTwistedLogger.critical(line)
            else:
                ourTwistedLogger.critical("failure has no getTraceBack() method. hmmm")
            return
    
        text = ""
        if eventDict.has_key("system"):
            text = eventDict["system"] + ": "
        if eventDict.has_key("message"):
            text += " ".join([str(m) for m in eventDict["message"]])
    
        if isError == 1:
            ourTwistedLogger.error(text)
        elif isWarning:
            text = "%s: %s (Filename: %s, Line number: %s)" %( eventDict['category'], eventDict['warning'], eventDict['filename'], eventDict['lineno'] )
            ourTwistedLogger.warn(text, exc_info = eventDict['warning'])
        else:
            ourTwistedLogger.info(text)
    except Exception, e:
        ourTwistedLogger.critical("A exception occured in the twisted log observer", exc_info = e)
        


def __configLoggerBasic():
    # leave this as is. It is the default root logger and goes to /dev/null
    # the way to call basicConfig() changed from version 2.3 to version 2.4
    # to be able to run in 2.3 (although with slightly messy logging), we detect this here:
    from platform import python_version_tuple
    (major, minor, dummy) = python_version_tuple()
    major = int(major)
    minor = int(minor)
    if (major >=2 and minor > 3 ):
        logging.basicConfig(level=logging.DEBUG, format='%(message)s', filename='/dev/null', filemode='w')
        #format='%(name)s %(asctime)s %(levelname)-8s %(message)s',
    else:
        logging.basicConfig()


def getAllowedLogLevels():
    """
    Utility to get a list of allowed loglevels (sorted by ascending log level) that we know of. The list contains only strings.

    @return: list
    """
    levelnames = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    return levelnames
    

def loglevelToInt(loglevel = 'NOTSET'):
    return logging._levelNames[loglevel]
#    levels = { "NOTSET": 0, "DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
#    if not levels.has_key(level):
#        raise NameError, "The given loglevel %s is not defined" % level
#    return levels[level]


def __getConfiguredLogLevel():
    loglevel = angelConfig.get('common', 'loglevel')
    return loglevelToInt(loglevel)


def __addConsoleHandler():
    # define a console Handler:
    console = logging.StreamHandler()
    console.setLevel(__getConfiguredLogLevel())
    #console.setLevel(logging.WARN) # for the console logger, we always use DEBUG!
    # set a format which is simpler for console use
    formatstring = angelConfig.get('common', 'consolelogformat')
    formatter = logging.Formatter(formatstring)
    # tell the handler to use this format
    console.setFormatter(formatter)
    # add the handler to the app's logger
    logging.getLogger().addHandler(console)
    #getLogger().addHandler(console)


def __addRotatingFileHandler():
    # define a file Handler:
    fileHandler = logging.handlers.RotatingFileHandler(getAngelLogFilename(), 'a', log_maxbytes, log_backupcount)
    fileHandler.setLevel(__getConfiguredLogLevel())
    # set a format which is simpler for console use
    formatstring = angelConfig.get('common', 'logformat')
    formatter = logging.Formatter(formatstring)
    # tell the handler to use this format
    fileHandler.setFormatter(formatter)    
    # add the handler to the app's logger
    logging.getLogger().addHandler(fileHandler)
    #getLogger().addHandler(fileHandler)


def __addSocketHandler():
    # define a socket Handler:
    socketHandler = logging.handlers.SocketHandler('localhost', angelConfig.getint("common", "loglistenport"))
    socketHandler.setLevel(__getConfiguredLogLevel())
    # don't bother with a formatter, since a socket handler sends the event as
    # an unformatted pickle
    # add the handler to the app's logger
    logging.getLogger().addHandler(socketHandler)
    #getLogger().addHandler(socketHandler)
 
def __addGrowlHandler():
    # growl support is optional:
    try:
        g = getAngelGrowlNotifier()
        growlHandler = GrowlHandler(level = __getConfiguredLogLevel(), growl = g)
        logging.getLogger().addHandler(growlHandler)
    except:
        pass

def getLoggingFilters():
    """
    Reads per module loglevels from the 'logfilters' section of the
    config file.
    Levels can be: NOTSET, DEBUG, INFO, WARN, ERROR, CRITICAL
    The default loglevel applies, so even if the per module 
    value is lower (==more verbosity), it won't get logged.
    This method returns a list of tuples, each of which has
    two values:
        - module name (string)
        - loglevel (int)

    Example:
    [logfilters]
    master.angel_app.admin.initializeRepository = WARN
    master.config = INFO
    master.ExternalProcessManager = ERROR
    presenter.delete = INFO
    presenter = INFO
    presenter.twisted = INFO
    provider.angel_app.resource.local.external.methods.proppatch = INFO
    """
    digits = re.compile("\d+")
    sectionname = 'logfilters'
    log = getLogger(__name__)
    if not angelConfig.has_section(sectionname):
        log.info("No section '%s' in config file, skipping", sectionname)
        return []
    filters = []
    #print "=======LOGGING CONFIG================"
    #print "Default LOGLEVEL: " + str(__getConfiguredLogLevel())
    for logfilter in angelConfig.container[sectionname].keys():
        level = angelConfig.get(sectionname, logfilter)
        if not digits.match(level):
            level = loglevelToInt(level)
        #print "LOGLEVEL " + str(level) + " for " + logfilter
        filters.append( [ logfilter, level] )
    #print "=======END CONFIG================"
    return filters

# Growl support is optional:
try:
    # to use Growl, http://growl.info/downloads_developers.php must be installed
    # Unfortunately, they added new python dependencies at some point
    # So we can only use version 1.1.4
    import Growl

    def getAngelGrowlNotifier():
        # TODO: this should return a singleton
        "returns a GrowlNotifier initialized/customized for Angel"
        from angel_app.gui.compat.common import getResourcePath
        app_icon = Growl.Image.imageFromPath(os.path.join(getResourcePath(), 'images', 'm221e.png')) # TODO: we should not need to know about paths/filenames here
        notifications = getAllowedLogLevels()
        notifications.append('User')
        g = Growl.GrowlNotifier(applicationName="Angel", notifications=notifications, defaultNotifications=['User'], applicationIcon=app_icon)
        g.register()
        return g

    class GrowlHandler(logging.Handler):
        """
        This is a logging handler doing growl notifications.

        It receives _all_ log messages and decides on the configured loglevel (given at construction or via setLevel())
        if it shall growl or not.
        
        To explicitly growl, you must call the logger's "growl()" method which bypasses the actual logging system.

        NOTE: as we have multiple processes that use a network logging system, we might get multiple
        calls with the same message if handlers are not configured correctly (e.g. the logging client
        and the logging server do the notification). To avoid this, you have to properly initialize the logging system. 
        """
        notifications = {
                         logging.DEBUG:'DEBUG',
                         logging.INFO:'INFO',
                         logging.WARNING:'WARNING',
                         logging.ERROR:'ERROR',
                         logging.CRITICAL:'CRITICAL'
                         }

        def __init__(self, level = logging.DEBUG, growl = None):
            """
            Constructor
            
            @param level: the minimum loglevel at which the messages get displayed
            @param growl: the GrowlNotifier object to use
            """
            logging.Handler.__init__(self, level)
            self.growl = growl
        
        def emit(self, record):
            if record.levelno not in self.notifications:
                #assert record.levelno in self.notifications, 'Error level %s not registered within GrowlHandler' % record.levelno
                pass # 'Error level %s not registered within GrowlHandler' % record.levelno
            else:
                title = "%s (%s)" % (self.notifications[record.levelno], record.name)
                self.growl.notify(self.notifications[record.levelno], title, record.msg)

except ImportError:
    pass
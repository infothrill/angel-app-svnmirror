import os

import wx
import wx.html as wxhtml

import angel_app.gui.compat.wrap as platformwrap
from angel_app.version import getVersionString
from angel_app.version import getBuildString
from angel_app.version import getPythonVersionString
from angel_app.version import getTwistedVersionString
from angel_app.log import getLogger

log = getLogger(__name__)

_ = wx.GetTranslation

class AboutWindow(wx.Dialog):
    """Information window"""

    def __init__(self, parent, id, title, pos=wx.DefaultPosition, 
                size=wx.DefaultSize, style=wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, id, title, pos, size, style)

        hboxButtons = wx.BoxSizer(wx.HORIZONTAL)
        vboxMain = wx.BoxSizer(wx.VERTICAL)
        hboxTop = wx.BoxSizer(wx.HORIZONTAL)
        vboxNameAndVersion = wx.BoxSizer(wx.VERTICAL)
        vboxMain.Add(hboxTop, 0, wx.CENTRE, 5)
        bmp = wx.Bitmap(os.path.join(platformwrap.getResourcePath(), "images", "m221e.png"), wx.BITMAP_TYPE_PNG)
        hboxTop.Add(wx.StaticBitmap(self, -1, bmp, wx.Point(-1, -1)), 0, wx.ALL | wx.CENTRE, 15)
        hboxTop.Add(vboxNameAndVersion, 0, wx.ALL | wx.ALIGN_CENTER | wx.ALIGN_CENTER_VERTICAL, 5)

        name = "ANGEL APPLICATION"
        version = 'Version %s (%s)' % (getVersionString(), getBuildString())
        website = "http://angelapp.missioneternity.org/"
        description ="""The ANGEL APPLICATION (a subproject of MISSION ETERNITY) aims to minimize,
and ideally eliminate, the administrative and material costs of backing up.
It does so by providing a peer-to-peer/social storage infrastructure where
people collaborate to back up each other's data."""

        # unicode copyright symbol: \u00A9
        copyright = u'\u00A9 Copyright 2006-2009 etoy.VENTURE ASSOCIATION, all rights reserved.'

        nameLabel = wx.StaticText(self, -1, name, style=wx.ALIGN_LEFT)
        nameLabel.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
        vboxNameAndVersion.Add(nameLabel, 1, wx.ALL | wx.ALIGN_CENTER, 5)
        versionLabel = wx.StaticText(self, -1, version, style=wx.ALIGN_LEFT)
        versionLabel.SetFont(wx.Font(16, wx.SWISS, wx.NORMAL, wx.BOLD))
        vboxNameAndVersion.Add(versionLabel, 1, wx.ALL | wx.ALIGN_CENTER, 5)

        copyLabel = wx.StaticText(self, -1, copyright, style=wx.ALIGN_CENTER)
        copyLabel.SetFont(wx.Font(10, wx.SWISS, wx.NORMAL, wx.BOLD))
        vboxMain.Add(copyLabel, 1, wx.ALL | wx.ALIGN_CENTER, 5)

        descLabel = wx.StaticText(self, -1,  _(description), style=wx.ALIGN_CENTER)
        descLabel.SetFont(wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL))
        vboxMain.Add(descLabel, 1, wx.ALL | wx.ALIGN_CENTER, 5)

        pageLabel = wx.HyperlinkCtrl(self, -1, website, website, wx.DefaultPosition)
        pageLabel.SetFont(wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL))
        vboxMain.Add(pageLabel, 1, wx.ALL | wx.ALIGN_CENTER, 5)

        vboxMain.Add(wx.StaticLine(self, -1), 0, wx.ALL | wx.EXPAND, 5)

        self.buttonCredits = wx.Button(self, 2004, _("C&redits"))
        hboxButtons.Add(self.buttonCredits, 0, wx.ALL | wx.ALIGN_LEFT, 3)
      
        self.buttonLicence = wx.Button(self, 2006, _("&Licence"))
        hboxButtons.Add(self.buttonLicence, 0, wx.ALL | wx.ALIGN_LEFT, 3)
      
        self.buttonOK = wx.Button(self, 2003, _("&Close"))
        hboxButtons.Add(self.buttonOK, 0, wx.ALL | wx.ALIGN_RIGHT, 3)
      
        vboxMain.Add(hboxButtons, 0, wx.ALL | wx.ALIGN_CENTER, 5)

        self.SetSizer(vboxMain)
        vboxMain.Fit(self)

        wx.EVT_BUTTON(self, 2003, self.onClose)
        wx.EVT_BUTTON(self, 2004, self.onCredits)
        wx.EVT_BUTTON(self, 2006, self.onLicence)

    def onClose(self, event):
        self.Destroy()

    def onCredits(self, event):
        creditsWindow = CreditsWindow(self, -1, _("Credits"), size=(500, 240))
        creditsWindow.CenterOnParent()
        creditsWindow.Show(True)
      
    def onLicence(self, event):
        licenseWindow = LicenseWindow(self, -1, _("Licence"), size=(500, 400), style=wx.DEFAULT_FRAME_STYLE)
        licenseWindow.CenterOnParent()
        licenseWindow.Show(True)


class LicenseWindow(wx.Frame):
    """Licence window class"""

    def __init__(self, parent, id, title, pos=wx.DefaultPosition,
                size=wx.DefaultSize, style=wx.CENTRE):
        wx.Frame.__init__(self, parent, id, title, pos, size, style)

        try:
            filename = os.path.join(platformwrap.getResourcePath(), "files", 'copying.html')
            fd = open(filename)
            data = fd.read()
            fd.close()
        except IOError, e:
            log.error("Unable to read licence file: %s" % filename, exc_info = e)
            data = "Error: <i>license file '%s' not found</i>" % filename

        scWinAbout = wx.ScrolledWindow(self, -1, wx.DefaultPosition, wx.Size(-1, -1))

        htmlWin = wxhtml.HtmlWindow(scWinAbout, -1, style=wx.SUNKEN_BORDER)
        htmlWin.SetFonts('Helvetica', 'Fixed', [12]*5)
        htmlWin.SetPage(data)
        htmlWin.Bind(wx.EVT_CHAR, self.OnChar)
      
        scBox = wx.BoxSizer(wx.VERTICAL)
        scBox.Add(htmlWin, 1, wx.ALL | wx.EXPAND, border = 0)
        scWinAbout.SetSizer(scBox)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(scWinAbout, proportion = 1, flag = wx.ALL | wx.EXPAND, border = 0)

        self.SetSizer(vbox)

    def onClose(self, event):
        """This method is invoked when Close button is clicked"""
        self.Destroy()

    def OnChar(self, event):
        if event.CmdDown() and event.GetKeyCode() in (87, 119): # cmd/ctrl and 'w'/'W'
            self.Close()
        event.Skip()

      
class CreditsWindow(wx.Dialog):
    """Credits window"""
   
    def __init__(self, parent, id, title, pos=wx.DefaultPosition,
                size=wx.DefaultSize):
        wx.Dialog.__init__(self, parent, id, title, pos, size)
      
        vbox = wx.BoxSizer(wx.VERTICAL)
      
        nb = wx.Notebook(self, -1)
      
        # "Written by" panel
        writePanel = wx.Panel(nb, -1)
        vboxWrite = wx.BoxSizer(wx.VERTICAL)
        programmers = ("Vincent Kraeutler <vincent@etoy.com>", "Paul Kremer <pol@etoy.com>")
        writtenString = "\n".join(programmers)
        labelWrite = wx.StaticText(writePanel, -1, writtenString)
        vboxWrite.Add(labelWrite, 0, wx.ALL, 10)
        writePanel.SetSizer(vboxWrite)
        writePanel.SetFocus()
      
        nb.AddPage(writePanel, _("Programmers"))

        # "Versions" panel
        versionsPanel = wx.Panel(nb, -1)
        vboxSP = wx.BoxSizer(wx.VERTICAL)
        pythonversion = "Python %s" % getPythonVersionString()
        twistedVersion = "%s" % getTwistedVersionString()
        wxversion = "wxPython " + ".".join( map( str, wx.VERSION ) )
        versions_list = [pythonversion, wxversion, twistedVersion]
        versionsString = "\n".join(versions_list)
        labelSP = wx.StaticText(versionsPanel, -1, versionsString)
        vboxSP.Add(labelSP, 0, wx.ALL, 10)
        versionsPanel.SetSizer(vboxSP)
        nb.AddPage(versionsPanel, _("Versions"))
      
        vbox.Add(nb, 1, wx.ALL | wx.EXPAND, 3)
      
        buttonClose = wx.Button(self, 2005, _("&Close"))
        vbox.Add(buttonClose, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
      
        self.SetSizer(vbox)
      
        wx.EVT_BUTTON(self, 2005, self.onClose)

      
    def onClose(self, event):
        """This method is invoked when Close button is clicked"""
        self.Destroy()

class ChangesWindow(wx.Frame):
    """Changes window class"""

    def __init__(self, parent, id, title, pos=wx.DefaultPosition,
                size=wx.DefaultSize, style=wx.CENTRE):
        wx.Frame.__init__(self, parent, id, title, pos, size, style)


        #
        # Read file
        #
        try:
            filename = os.path.join(platformwrap.getResourcePath(), "files", 'CHANGES')
            fd = open(filename)
            data = fd.read()
            fd.close()
        except IOError, e:
            log.error("Unable to read file: %s" % filename, exc_info = e)
            data = "Error: file '%s' not found!" % filename

        text = wx.TextCtrl(self, -1, data, style=wx.TE_MULTILINE|wx.TE_READONLY)
        text.SetFont(wx.Font(12, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)) # monospace

        text.Bind(wx.EVT_CHAR, self.OnChar)
    
        textsizer = wx.BoxSizer(wx.VERTICAL)
        textsizer.Add(text, proportion = 1, border = 0, flag = wx.ALL | wx.EXPAND)

        self.SetSizer(textsizer)

    def OnChar(self, event):
        if event.CmdDown() and event.GetKeyCode() in (87, 119): # cmd/ctrl and 'w'/'W'
            self.Close()
        event.Skip()

    def onClose(self, event):
        """This method is invoked when Close button is clicked"""
        self.Destroy()
      
if __name__ == '__main__':
    """
    This allows us to run it separately from the rest of the GUI (for quick testing)
    """
    from angel_app.log import initializeLogging
    initializeLogging()
    app = wx.App(0)
    win = ChangesWindow(None, -1, _("Version History"), size=(620, 400), style=wx.DEFAULT_FRAME_STYLE)
    #win = LicenseWindow(None, -1, _("Software license"), size=(620, 400), style=wx.DEFAULT_FRAME_STYLE)
    win.CenterOnParent()
    win.Show(True)
    app.MainLoop()
"""
This module is supposed to contain code that is run once on startup
of the GUI, e.g. after having 
"""
import wx

from angel_app.maintainer.mount import getMountTab

_ = wx.GetTranslation

def askYesNo(text):
    questiontext = text 
    dlg = wx.MessageDialog(None, questiontext, _('Warning'), wx.ICON_QUESTION | wx.YES_NO | wx.NO_DEFAULT)
    res = dlg.ShowModal()
    dlg.Destroy()
    if res == wx.ID_YES:
        return True
    else:
        return False

def checkM221eMount():
    found = False
    url = "http://missioneternity.org:6221/"
    mntpoint = "MISSION ETERNITY"
    for k in getMountTab():
        print k[0]
        if k[0] == url:
            found = True
            break
    if found:
        return True
    res = askYesNo(_("""The ANGEL APPLICATION is currently not set up to replicate %s on your computer. Would you like to become an ANGEL by activating it?""" % url))
    if res:
        from angel_app.gui.mounttab import MountsWindow 
        window = MountsWindow(None, -1, _("Mounts"))
        window.CenterOnParent()
        window.mountsPanel.listPanel.modifyMountPoints("Edit mount point", url, mntpoint)
    else:
        return True
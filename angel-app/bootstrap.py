#!/usr/bin/env python

INSTALL_LOCATION = "angel-app"

import os

os.mkdir(INSTALL_LOCATION)

import commands
def run(command, description):  
  print description
  print command + ":" + commands.getstatusoutput(command)[1]

run(
  "python ./virtual-python.py --prefix=" + INSTALL_LOCATION,
  "create virtual python installation")

print "use virtual python installation from now on"
os.environ["PATH"] = INSTALL_LOCATION + "/bin"  + ":" + os.environ["PATH"] 
print os.environ["PATH"]

run("python ./setup.py install",
 "install angel-app libraries")

run("cp src/bin/* " + INSTALL_LOCATION + "/bin",
  "installing angel-app binaries")

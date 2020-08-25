#!/usr/local/bin/psupython
# pylint:disable=C0103, E0611, E0401, W0703
# -*- coding: utf-8 -*-
'''
------------------------
  Penn State MacAdmins
------------------------
Performs the following:
  - Reads a preference that is always set by jamf when using a
    computer level WiFi Configuration Profile and reports it back to jamf
-------------------------------------
  Joshua D. Miller - josh@psu.edu
  The Pennsylvania State University

  Last Update: Dec 4, 2019
  Tested: Python 3.8.0
  Requirements:
    - pyobjc-core
    - pyobjc-CoreWLAN

-------------------------------------
'''

# Imports
from __future__ import print_function

import CoreWLAN

# ----------------------------------------------------------------
def wifi_check():
    '''Checks that Your WiFi System Mode is True or False'''
    try:
        # Load all available wifi INTERFACES
        INTERFACES = dict()
        for i in CoreWLAN.CWInterface.interfaceNames():
            INTERFACES[i] = CoreWLAN.CWInterface.interfaceWithName_(i)

        # Repeat the configuration with every wifi interface
        for i in INTERFACES:
            # Grab a mutable copy of this interface's configuration
            configuration_copy = CoreWLAN.CWMutableConfiguration.alloc() \
                .initWithConfiguration_(INTERFACES[i].configuration())
            # Find all the preferred/remembered network profiles
            profiles = list(configuration_copy.networkProfiles().array())
            for profile in profiles:
                if profile.ssid() == "Your WiFi SSID to check Here":
                    if profile.systemMode() == 0:
                        print("<result>False</result>")
                    else:
                        print("<result>True</result>")
    except Exception:
        print("<result>True</result>")


if __name__ == '__main__':
    wifi_check()

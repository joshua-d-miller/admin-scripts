#!/usr/local/bin/psupython
# -*- coding: utf-8 -*-
# pylint:disable=C0103, E0611, E0401, W0703
'''
------------------------
  Penn State MacAdmins
------------------------
Performs the following:
  - Check for Preferred WiFi Network and report to jamf Pro
-------------------------------------
  Joshua D. Miller - josh@psu.edu
  The Pennsylvania State University

  Last Update: December 4, 2019
  Tested: Python 3.8.0
  Modules Required:
    - pyobjc-core
    - pyobjc-framework-CoreWLAN
-------------------------------------
References:
  - https://gist.github.com/coreyb42/69c03139086ae45ce0b57e64de297d3a
  - https://gist.github.com/pudquick/fcbdd3924ee230592ab4
  - https://www.jamf.com/jamf-nation/feature-requests/6281/break-up-multi-mdm-payload-gui-payloads
'''

# Imports
from __future__ import print_function
import CoreWLAN

# ----------------------------------------------------------------
def preferred_wifi_check():
    '''Checks that PSU is the preferred WiFi'''
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
            ssid_list = [x.ssid() for x in profiles]
            # Check to see if our preferred SSID is in the list
            FirstWiFi = ssid_list[0]
            if FirstWiFi == "Your Preferred WiFi here":
                print("<result>Yes</result>")
            else:
                print("<result>No</result>")
    except Exception:
        print("<result>No</result>")


if __name__ == '__main__':
    preferred_wifi_check()

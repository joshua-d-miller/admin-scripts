#!/usr/local/bin/psupython
# -*- coding: utf-8 -*-
# pylint:disable=C0103, E0611, E0401, W0703
'''
------------------------
  Penn State MacAdmins
------------------------
Performs the following:
  - Turns off the System mode for WiFi networks you specify that were
    configured using jamf Pro's WiFi Computer level config profile
Notes:
  - References
    # https://gist.github.com/coreyb42/69c03139086ae45ce0b57e64de297d3a
    # https://gist.github.com/pudquick/fcbdd3924ee230592ab4
  - Bug Jamf to change this behavior by voting this up
    # https://www.jamf.com/jamf-nation/feature-requests/6281/break-up-multi-mdm-payload-gui-payloads
-------------------------------------
  Joshua D. Miller - josh@psu.edu
  The Pennsylvania State University

  Last Update: November 26, 2019
  Tested: Python 3.8.0
  Requirements:
    - pyobjc-core
    - pyobjc-CoreWLAN

-------------------------------------
'''

# Imports
from __future__ import print_function
from Foundation import NSOrderedSet
import CoreWLAN

# ----------------------------------------------------------------
def WiFi_Adjustments():
    '''Performs settings the WiFi system mode to false for
    the networks specified below and then sets our preferred
    networks as specified below as well'''
    try:
        print('• Set System Mode to FALSE'
              ' for our specified WiFi Networks')
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
                for network in ssids_to_fix:
                    if profile.ssid() == network:
                        profile.setSystemMode_(False)
                        print(
                            ' ○ System Mode set to False'
                            ' for {0:}'.format(network))
        print('  ✓ Completed')
    except Exception as error:
        print(error)
        print('  ✖ Unable to set system mode as false for'
              ' the specified SSIDs. Please try again')
    # Set Preferred Network Order
    try:
        print('• Reorganize WiFi Networks as specified')
        # Grab all the SSIDs, in order
        ssids = [x.ssid() for x in profiles]
        # Check to see if our preferred SSID is in the list
        if ssids_to_fix[0] in ssids:
            # Second
            profiles.sort(
                key=lambda x: x.ssid() == ssids_to_fix[1], reverse=True)
            # First
            profiles.sort(
                key=lambda x: x.ssid() == ssids_to_fix[0], reverse=True)
            # Now we move next_to_last_SSID to the end
            profiles.sort(
                key=lambda x: x.ssid() == ssids_to_put_at_end_of_line[0],
                reverse=False)
            # Now we move last_SSID to the end (bumping next_to_last_SSID)
            profiles.sort(
                key=lambda x: x.ssid() == ssids_to_put_at_end_of_line[1],
                reverse=False)
            print('  ✓ Completed')
    except Exception as error:
        print(error)
        print('  ✖ Unable to arrange WiFis in the prefferd order')
    # Finalize Configuration
    try:
        print('• Finalize Configuration of WiFi')
        profile_set = NSOrderedSet.orderedSetWithArray_(profiles)
        configuration_copy.setNetworkProfiles_(profile_set)
        INTERFACES[i].commitConfiguration_authorization_error_(
            configuration_copy, None, None)
        print('  ✓ Completed')
    except Exception as error:
        print(error)
        print('  ✖ Unable to finalize config. Changes NOT Saved')


if __name__ == '__main__':
    print('', end='\n')
    print('------------------------', end='\n')
    print('  Penn State MacAdmins  ', end='\n')
    print('------------------------', end='\n')
    ssids_to_fix = ['First WiFi', 'Second WiFi']
    ssids_to_put_at_end_of_line = ['First WiFi you want at end',
                                   'Second WiFi you want at end']
    WiFi_Adjustments()

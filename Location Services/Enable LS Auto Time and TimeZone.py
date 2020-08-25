#!/usr/local/bin/psupython
# -*- coding: utf-8 -*-
# pylint:disable=C0103, W0621, W0702, W0703, E1101, E0611, R1710
'''
------------------------
  Penn State MacAdmins
------------------------
Performs the following:
  - Enable Location Services
  - Enable 'Set Date and Time Automatically'
  - Enable 'Set time zone automatically using current location'
-------------------------------------
  Joshua D. Miller - josh@psu.edu
  The Pennsylvania State University

  Last Update: August 21, 2020
  Tested: Python 3.8.0
  Modules Required:
    - pyobjc-core
    - pyobjc-framework-CoreLocation
-------------------------------------
'''

# Import Modules needed
from __future__ import print_function
from pwd import getpwnam
from os import remove, seteuid
from subprocess import check_output, PIPE
from CoreLocation import CLLocationManager
from Foundation import (CFPreferencesSetValue, CFPreferencesSetAppValue,
                        CFPreferencesSynchronize, kCFPreferencesCurrentUser,
                        kCFPreferencesCurrentHost)

# ----------------------------------------------------------------
# Location Services
def location_services():
    '''This funciton will allow the Mac to change its time zone
    # based off its location when it is connected to WiFi'''
    print(' ○ Location Services')
    ls_status = CLLocationManager.locationServicesEnabled()
    if ls_status is False:
        try:
            # Switch to Locationd user
            locationd_uid = getpwnam('_locationd').pw_uid
            seteuid(locationd_uid)
            # Enable Location Services
            CFPreferencesSetValue('LocationServicesEnabled',
                                  True, 'com.apple.locationd',
                                  kCFPreferencesCurrentUser,
                                  kCFPreferencesCurrentHost)
            # Switch back to Root
            seteuid(0)
            # Restart the location deamon to enable
            check_output(
                ['/bin/launchctl', 'kickstart',
                 '-k', 'system/com.apple.locationd'], stderr=PIPE)
            print('  ✓ Completed', end='\n')

        except Exception as error:
            print('  ✖ {0:}'.format(error), end='\n')
            print('   - Failed to enable Location Services. '
                  'Please see error listed above')
    else:
        print('  ✓ Already Enabled')

# ----------------------------------------------------------------
# Auto TimeZone
def autotimezone():
    '''Turns on Automatic Time Zone'''
    # Remove any plists in timed
    print(' ○ Automatic Time and Timezone')
    try:
        remove('/var/db/timed/Library/Preferences/*.*')
    except:
        pass
    try:
        remove('/var/db/timed/Library/Preferences/ByHost/*.*')
    except:
        pass
    try:
        # Switch to timed to make changes
        timed_uid = getpwnam('_timed').pw_uid
        seteuid(timed_uid)
        CFPreferencesSetAppValue('TMAutomaticTimeOnlyEnabled',
                                 True, 'com.apple.timed')
        CFPreferencesSetAppValue('TMAutomaticTimeZoneEnabled',
                                 True, 'com.apple.timed')
        CFPreferencesSynchronize(
            'com.apple.timed', kCFPreferencesCurrentUser,
            kCFPreferencesCurrentHost)
        # Switch back to root
        seteuid(0)
        # Restart the Service
        check_output(
            ['/bin/launchctl', 'kickstart',
             '-k', 'system/com.apple.timed'], stderr=PIPE)
        print('  ✓ Completed', end='\n')

    except Exception as error:
        print('  ✖ {0:}'.format(error), end='\n')
        print('   - Failed to enable automatic time and time zone. '
              'Please see error listed above.')

# ----------------------------------------------------------------
# Main Function
if __name__ == '__main__':
    print('', end='\n')
    print('------------------------', end='\n')
    print('  Penn State MacAdmins  ', end='\n')
    print('------------------------', end='\n')
    print('• Enabling Location Services, Automatic Time and Timezone')
    # Turn on Location Services and set Time Zone by Location
    location_services()
    # Turn on Auto Time and Auto TimeZone
    autotimezone()
    print('', end='\n')

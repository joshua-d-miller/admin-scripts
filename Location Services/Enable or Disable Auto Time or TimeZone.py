#!/usr/local/bin/psupython
# -*- coding: utf-8 -*-
# pylint:disable=C0103, W0621, W0703, E1101, E0611, R1710
'''
------------------------
  Penn State MacAdmins
------------------------
Performs the following:
  - Enable / Disable Automatic Time Zone and Time (Not Modifiable)
Note:
  - Argument five is used as the first four are used by jamf Pro
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

# Import Modules
from __future__ import print_function
from os import setuid
from subprocess import check_output, PIPE
from pwd import getpwnam
from sys import argv
from Foundation import (CFPreferencesSetValue, CFPreferencesSynchronize,
                        kCFPreferencesAnyUser, kCFPreferencesCurrentUser,
                        kCFPreferencesCurrentHost)

def auto_timezone(setting):
    '''Automatic TimeZone setting can be enabled or disabled'''
    # Turn on/off Auto Timezone
    CFPreferencesSetValue('Active', setting, 'com.apple.timezone.auto',
                          kCFPreferencesAnyUser, kCFPreferencesCurrentHost)
    # Syncrhonize Preferences for Auto Timezone
    CFPreferencesSynchronize('com.apple.timezone.auto',
                             kCFPreferencesAnyUser,
                             kCFPreferencesCurrentHost)
    try:
        timed_uid = getpwnam('_timed').pw_uid
        setuid(timed_uid)
        CFPreferencesSetValue('TMAutomaticTimeOnlyEnabled',
                              setting, 'com.apple.timed',
                              kCFPreferencesCurrentUser,
                              kCFPreferencesCurrentHost)
        check_output(['/usr/bin/defaults',
                      'delete',
                      'com.apple.timed',
                      'TMAutomaticTimeOnlyEnabled'],
                     stderr=PIPE)
        CFPreferencesSetValue('TMAutomaticTimeZoneEnabled',
                              setting, 'com.apple.timed',
                              kCFPreferencesCurrentUser,
                              kCFPreferencesCurrentHost)
    except Exception as error:
        print('  ✖ {0:}'.format(error), end='\n')

    CFPreferencesSynchronize('com.apple.timed',
                             kCFPreferencesAnyUser,
                             kCFPreferencesCurrentHost)


if __name__ == '__main__':
    print('', end='\n')
    print('------------------------', end='\n')
    print('  Penn State MacAdmins  ', end='\n')
    print('------------------------', end='\n')
    if argv[5] == "enable":
        try:
            print('• Enable automatic TimeZone setting in Date & Time')
            auto_timezone(True)
            print('  ✓ Completed', end='\n')
        except Exception as error:
            print(
                '  ✖'
                ' Unable to Enable Automatic TimeZone setting in Date & Time',
                end='\n')
    elif argv[5] == "disable":
        try:
            print('• Disable automatic TimeZone setting in Date & Time')
            auto_timezone(False)
            print('  ✓ Completed', end='\n')
        except Exception as error:
            print(
                '  ✖'
                ' Unable to Disable Automatic TimeZone setting in Date & Time',
                end='\n')

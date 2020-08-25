#!/usr/local/bin/psupython
# pylint:disable=C0103, E0611
'''
------------------------
  Penn State MacAdmins
------------------------
Performs the following:
  - Adds the following keys to GlobalProtect PLIST
    * Portal (Portal needed to connect)
    * Prelogon (Enable Prelogon)

-------------------------------------
  Joshua D. Miller - josh@psu.edu
  The Pennsylvania State University

  Last Update: June 16, 2020
  Tested: Python 3.8.0

-------------------------------------
'''

# Imports
from __future__ import print_function
from os import path
from plistlib import dump as writePlist

# ------------------------------------------------------------------
def configure_globalprotect():
    '''This function will allow us to preconfigure the GlobalProtect
    secure portal before the app launches'''
    # PLIST name for GlobalProtect
    gp_name = 'com.paloaltonetworks.GlobalProtect.settings.plist'
    # Create PLIST if it doesn't already exist
    gp_plist_location = ('/Library/Preferences/{0:}'.format(gp_name))
    if path.isfile(gp_plist_location):
        print('PLIST Exists. No creation is needed...')
    else:
        gp_plist = {
            'Palo Alto Networks': {
                'GlobalProtect': {
                    'PanSetup': {
                        'Portal': 'Your Portal Address Here',
                        'Prelogon': '1'
                    }
                }
            }
        }
        with open(gp_plist_location, 'wb') as pl:
            writePlist(gp_plist, pl)


if __name__ == '__main__':
    configure_globalprotect()

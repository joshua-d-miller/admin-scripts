#!/usr/local/bin/psupython
# pylint:disable=C0103, E0611
'''
------------------------
  Penn State MacAdmins
------------------------
Performs the following:
  - Determines the current TeamViewer ID of the machine and reports
    it to jamf Pro
-------------------------------------
  Joshua D. Miller - josh@psu.edu
  The Pennsylvania State University

  Last Update: January 22, 2020
  Tested: Python 3.8.0
-------------------------------------
'''

from __future__ import print_function
from Foundation import CFPreferencesCopyAppValue

# ---------------------------------------------------------
def get_teamviewer_id():
    '''Retreives the TeamViewer ID of the current client'''
    # The directory to search for the TeamViewer PLIST file
    # Usually this is /Library/Preferences
    tv_plist = "com.teamviewer.teamviewer.preferences"
    try:
        tv_id = CFPreferencesCopyAppValue(
            'ClientID', '/Library/Preferences/{0:}.plist'.format(
                tv_plist
                ))
        print('<result>{0:}</result>'.format(tv_id))
        exit(0)
    except IOError:
        print('<result>Not Installed</result>')


if __name__ == '__main__':
    get_teamviewer_id()

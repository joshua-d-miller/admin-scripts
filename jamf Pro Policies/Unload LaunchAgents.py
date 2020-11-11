#!/usr/bin/python
# pylint:disable=C0103, C0411, C0111, E0611
'''
------------------------
  Penn State MacAdmins
------------------------
Performs the following:
  - Unloads LaunchAgents not needed on Shared Workstations
Notes:
  - Real world usage is disabling items like NoMAD on a machine
    that is on the network always that doesn't keep a profile or
    the Palo Alto VPN for the same reason
-------------------------------------
  Joshua D. Miller - josh@psu.edu
  The Pennsylvania State University

  Last Update: November 11, 2020
  Tested: Python 3.8.0
  Requirements:
    - pyobjc-core

-------------------------------------
'''

from SystemConfiguration import SCDynamicStoreCopyConsoleUser
from subprocess import CalledProcessError, check_output, PIPE


def unload_launchAgents(agent_to_unload):
    '''Function to unload the specified launchAgents'''
    # Create Agent Path
    la_path = '/Library/LaunchAgents/{0:}.plist'.format(agent_to_unload)
    # Determine Status
    try:
        la_status = check_output(
            ['/bin/launchctl', 'asuser', str(current_user[1]), '/bin/launchctl',
             'list', agent_to_unload], stderr=PIPE)
    except CalledProcessError:
        la_status = ""
    # Disable the LaunchAgent
    try:
        check_output(
            ['/bin/launchctl', 'disable', 'user/{0:}/{1:}'.format(
                str(current_user[1]), agent_to_unload)],
            stderr=PIPE)
    except CalledProcessError:
        print("Agent {0:} Already Disabled. Continuing...".format(
            agent_to_unload))
    # Unload the LaunchAgent
    while la_status != "":
        try:
            check_output(
                ['/bin/launchctl', 'bootout', 'gui/{0:}'.format(
                    str(current_user[1])), la_path], stderr=PIPE)
            la_status = check_output(
                ['/bin/launchctl', 'asuser', str(current_user[1]),
                 '/bin/launchctl', 'list', agent_to_unload],
                stderr=PIPE)
        except CalledProcessError:
            la_status = ""


if __name__ == '__main__':
    # Get Current User
    current_user = SCDynamicStoreCopyConsoleUser(None, None, None)
    # LaunchAgents to unload (Create your list of LaunchAgents here)
    # Use just their name without .plist
    la_list = [
        ''
    ]
    for agent in la_list:
        unload_launchAgents(agent)

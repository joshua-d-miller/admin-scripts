#!/usr/local/bin/psupython
# -*- coding: utf-8 -*-
# pylint:disable=C0103, W0621, W0702, W0703, E1101, E0611, R1710
'''
------------------------
  Penn State MacAdmins
------------------------
Performs the following:
  - Sets Computer Name to Prefix-SerialNumber (E7)
  - Sets specified administrators for Remote Management and Login
  - Creates a launch daemon to keep the computer name even after reboot
  - Sets a network time server
  - Creates a manifest for the machine in our munki repo
  - Sets account pictures and display names for our specified admins
  - Binds to EAD
  - Unlocks the following System Preference Panes
    * Energy Saver
    * Time Machine
    * Date & Time
    * Network
  - Enables Location Services, enables Automatic Time, and enables
    Automatic Time Zone
  - Downloads and installs the latest version of munki from GitHub releases
    https://github.com/munki/munki/releases
Notes:
  - This can be run altogether as an enrollment script or can be called
    seperatly using argument five
  - Argument five is used because the first four are used by jamf

-------------------------------------
  Joshua D. Miller - josh@psu.edu
  The Pennsylvania State University

  Last Update: August 21, 2020
  Tested: Python 3.8.0
  Requirements:
    - pyobjc-core
    - pyobjc-framework-CoreLocation
    - pyobjc-framework-OpenDirectory
    - pyobjc-framework-SystemConfiguration
    - munki repo with mwa2
      * https://github.com/munki/mwa2

-------------------------------------
'''

# Import Modules needed
from __future__ import print_function
from ctypes import CDLL, c_void_p, byref
from ctypes.util import find_library
from grp import getgrnam
from json import dumps as json_dumps, loads as json_loads
from os import chown, chmod, remove, seteuid
from platform import mac_ver
from distutils import version
from pwd import getpwnam
from subprocess import (CalledProcessError, check_output, PIPE, STDOUT)
from sys import argv, version_info
from CoreLocation import CLLocationManager
from Foundation import (NSBundle, NSData, NSString, CFPreferencesSetValue,
                        CFPreferencesSetAppValue,
                        CFPreferencesSynchronize, kCFPreferencesAnyUser,
                        kCFPreferencesCurrentUser, kCFPreferencesCurrentHost)
from OpenDirectory import (ODSession, ODNode, kODRecordTypeGroups,
                           kODRecordTypeUsers, kODAttributeTypeFullName,
                           kODAttributeTypePicture, kODAttributeTypeJPEGPhoto)
from SystemConfiguration import (
    SCPreferencesCreate, SCPreferencesSetComputerName,
    SCPreferencesSetLocalHostName, SCPreferencesCommitChanges,
    SCPreferencesApplyChanges, SCPreferencesSynchronize)
import objc
if version_info[0] == 2:
    from plistlib import writePlist
else:
    from plistlib import dump as plist_dump



# ----------------------------------------------------------------
def build_computer_name():
    '''Builds the computer name to be E7-SerialNumber'''
    # Location of IOKit Bundle - Code from Mike Lynn's Gist
    # https://gist.github.com/erikng/46646ff81e55b42e5cfc
    IOKit_bundle = NSBundle.bundleWithIdentifier_('com.apple.framework.IOKit')
    functions = [("IOServiceGetMatchingService", b"II@"),
                 ("IOServiceMatching", b"@*"),
                 ("IORegistryEntryCreateCFProperty", b"@I@@I"), ]
    objc.loadBundleFunctions(IOKit_bundle, globals(), functions)
    # pylint:disable=E0602
    serial_number = IORegistryEntryCreateCFProperty(
        IOServiceGetMatchingService(
            0, IOServiceMatching(
                "IOPlatformExpertDevice".encode("utf-8"))),
        NSString.stringWithString_(
            'IOPlatformSerialNumber'), None, 0)
    # Build Computer Name
    new_computer_name = '{0:}-{1:}'.format(prefix, serial_number)
    return new_computer_name

# ----------------------------------------------------------------
# Computer Name Function
def set_computer_name():
    '''Reads the computer's serial number
    Sets the computer name to Prefix-SerialNumber'''

    print('• Set Computer Name to {0:}'.format(computer_name), end='\n')

    # Connect SystemConfiguration to System
    sys_prefs = SCPreferencesCreate(None, "SystemConfiguration", None)
    # Set Computer Name
    try:
        SCPreferencesSetComputerName(sys_prefs, computer_name, 0)
        SCPreferencesSetLocalHostName(sys_prefs, computer_name)
        # Apply Changes
        SCPreferencesCommitChanges(sys_prefs)
        SCPreferencesApplyChanges(sys_prefs)
        SCPreferencesSynchronize(sys_prefs)
    except Exception as error:
        print('  ✖ {0:}'.format(error), end='\n')

# ----------------------------------------------------------------
# Connect to the Local Node Function
def connect_local():
    '''Function that connects us to the /Local/Default Node'''
    func_local_node, _ = ODNode.nodeWithSession_name_error_(
        ODSession.defaultSession(), "/Local/Default", None)
    return func_local_node, _

# ----------------------------------------------------------------
# Harden ARD Security by only allowing our specified accounts
def harden_ard():
    '''This will only allow the administrator(s) specified to use ARD'''

    print('• Harden Remote Management', end='\n')

    kickstart = ('/System/Library/CoreServices/RemoteManagement/'
                 'ARDAgent.app/Contents/Resources/kickstart')

    try:
    	# Turn off ARD and remove all settings
        check_output(
            [kickstart, '-deactivate', '-configure',
             '-access', '-off'],
            stderr=STDOUT)

    	# Enable ARD
        check_output(
            [kickstart, '-activate', '-configure',
             '-allowAccessFor', '-specifiedUsers'],
            stderr=STDOUT)

    	# Add Access for Users
        check_output(
            [kickstart, '-configure', '-users',
             ','.join(admin_list),
             '-access', '-on',
             '-privs', '-all'], stderr=STDOUT)

        # Restart ARDAgent
        check_output(
            [kickstart, '-restart', '-agent'],
            stderr=STDOUT)
        print('  ○ ARD Access set to only allow {0:}'.format(
            ','.join(admin_list)), end='\n')
    except Exception as error:
        print('  ✖ {0:}'.format(error), end='\n')

# ----------------------------------------------------------------
# Harden SSH Security by only allowing our specified accounts
def harden_ssh(local_node):
    '''This will allow the administrator(s) specified to use SSH'''

    try:
        # Turn off SSH Temporarily
        check_output(['/usr/sbin/systemsetup', '-f', '-setremotelogin',
                      'off'], stderr=PIPE)

        # Remove Disabled List as we are setting Users for SSH
        local_ssh_disabled, _ = local_node.\
            recordWithRecordType_name_attributes_error_(
                kODRecordTypeGroups, 'com.apple.access_ssh-disabled', None, None)
        if local_ssh_disabled is not None:
            local_ssh_disabled.deleteRecordAndReturnError_(None)

        # Remove the current SSH List since we are going to create a fresh one
        local_ssh_current, _ = local_node.\
            recordWithRecordType_name_attributes_error_(
                kODRecordTypeGroups, 'com.apple.access_ssh', None, None)
        if local_ssh_current is not None:
            local_ssh_current.deleteRecordAndReturnError_(None)

        # Create SSH Group fresh
        local_node.createRecordWithRecordType_name_attributes_error_(
            kODRecordTypeGroups, 'com.apple.access_ssh', None, None)

        # Pull SSH Access Settings
        local_ssh, _ = local_node.recordWithRecordType_name_attributes_error_(
            kODRecordTypeGroups, 'com.apple.access_ssh', None, None)

        # Add primary group
        local_ssh.addValue_toAttribute_error_(
            '501', 'dsAttrTypeStandard:PrimaryGroupID', None)
        # Update our admin accounts to allow them to SSH
        for ssh_account in admin_list:
            # Pull Local Administrator Record
            ssh_account_info, _ = local_node.\
                recordWithRecordType_name_attributes_error_(
                    kODRecordTypeUsers, ssh_account, None, None)
            ssh_account_info_values, _ = ssh_account_info.\
                recordDetailsForAttributes_error_(None, None)
            ssh_account_uid = ssh_account_info_values[
                'dsAttrTypeStandard:GeneratedUID'][0]
            # Add our specified administrator(s) name and uid
            local_ssh.addValue_toAttribute_error_(
                ssh_account, 'dsAttrTypeStandard:GroupMembership', None)
            local_ssh.addValue_toAttribute_error_(
                ssh_account_uid, 'dsAttrTypeStandard:GroupMembers', None)

        # Synchronize the record as we made changes
        local_ssh.synchronizeAndReturnError_(None)

        # Turn on SSH
        check_output(['/usr/sbin/systemsetup', '-f', '-setremotelogin',
                      'on'], stderr=PIPE)
        print('  ○ SSH Access set to only allow {0:}'.format(
            ','.join(admins_to_prepare)), end='\n')
    except Exception as error:
        print('  ✖ {0:}'.format(error), end='\n')

# ----------------------------------------------------------------
# Set the NTP Server and Set Computer Name Daemon Function
def settings_setup():
    '''Script will set initial settings for macOS devices such
    as NTP Server, and Set Computer Name Daemon'''

    print('• Settings Setup for Time Server and Set Computer Name LaunchDaemon', end='\n')

    # Set NTP Server
    try:
        check_output(['/usr/sbin/systemsetup', '-setnetworktimeserver',
                      'clock.psu.edu'], stderr=PIPE)
        check_output(['/usr/sbin/systemsetup', '-setusingnetworktime',
                      'on'], stderr=PIPE)
        print(
            '  ○ Network Time Server set to clock.psu.edu')
    except Exception as error:
        print('  ✖ {0:}'.format(error), end='\n')

    # Create LaunchDaemon to ensure Computer Name on Boot
    try:
        daemon_path = '/Library/LaunchDaemons/edu.psu.setcomputername.plist'
        set_computer_name_plist = dict(
            RunAtLoad=True,
            Label="edu.psu.setcomputername",
            ProgramArguments=[
                "/usr/sbin/systemsetup", "-setcomputername", computer_name,
                "-setlocalsubnetname", computer_name]
        )
        if version_info[0] == 2:
            writePlist(set_computer_name_plist, daemon_path)
        else:
            with open(daemon_path, 'wb') as daemon_file:
                plist_dump(set_computer_name_plist, daemon_file)
        root_uid = getpwnam('root').pw_uid
        wheel_uid = getgrnam('wheel').gr_gid
        chown(daemon_path, root_uid, wheel_uid)
        chmod(daemon_path, 0o644)
        print('  ○ Set Computer Name on Boot LaunchDaemon Created', end='\n')
    except Exception as error:
        print(error, end='\n')

# ----------------------------------------------------------------
# Create a manifest for the macOS Device in Munki Function
def create_munki_manifest():
    '''This function connects to MunkiWebAdmin2
    and creates a manifest for the device'''

    print('• Create Munki Manifest for {0:}'.format(computer_name), end='\n')

    # Build the URL
    url = "{0}{1}{2}".format(mwa_address, '/api/manifests/',
                             'hosts/{0:}'.format(computer_name))

    # Data to add to manifest
    data = {"catalogs": ['production'],
            "included_manifests": ['global'],
            "managed_installs": [],
            "managed_uninstalls": [],
            "managed_updates": [],
            "optional_installs": [], }

    data = json_dumps(data)

    # Connect and determine if a manifest exists
    get_request = check_output(['/usr/bin/curl', ' -i', '-H',
                                'Authorization: {0:}'.format(
                                    basic_auth_string_mwa),
                                '-H', 'Content-Type: application/json',
                                '-X', 'GET', url],
                               stderr=PIPE)

    if 'production' in str(get_request, 'utf-8'):  # manifest already exists
        print('  ○ A manifest was already found for this machine', end='\n')
    elif 'failed' in str(get_request, 'utf-8'):  # manifest does not exist
        # Create manifest
        check_output(['/usr/bin/curl', '-i', '-H',
                      'Authorization: {0:}'.format(
                          basic_auth_string_mwa),
                      '-H', 'Content-Type: application/json',
                      '--data', data,
                      '-X', 'POST', url],
                     stderr=PIPE)
        print('  ○ Manifest created for {0:}'.format(computer_name), end='\n')
    else:
        print('  ○ No modifications where made', end='\n')

# ----------------------------------------------------------------
# Get Authorization Right
def authorization_right_get(right):
    '''Get Authorization Right thanks to Tom Burgin
    https://gist.github.com/tburgin/77ebd114d59d368b0b4321ca7cf77767'''
    db_buffer = c_void_p()
    AuthorizationRightGet(right.encode('ascii'), byref(db_buffer))
    if db_buffer:
        # pylint:disable=E1101
        return objc.objc_object(c_void_p=db_buffer).mutableCopy()

# ----------------------------------------------------------------
# Set Authorization Right
def authorization_right_set(right, value):
    '''Set Authorization Right thanks to Tom Burgin
    https://gist.github.com/tburgin/77ebd114d59d368b0b4321ca7cf77767'''
    auth_ref = c_void_p()
    AuthorizationCreate(None, None, 0, byref(auth_ref))
    return AuthorizationRightSet(
        auth_ref, right.encode('ascii'), value.__c_void_p__(), None, None, None)

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
        print('  ★ Already Enabled')

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
def power_prefs():
    '''This function will set the system preferences we have specified
    and will turn on location services based off WiFi location'''

    # Enable all users access to the System Preference Panes
    # we defined above

    print('• Unlock the following System Preference Panes:', end='\n')

    for preference in system_prefs_to_change:
        if macOS_version < "10.10.0":
            print('  ✖ This script will not function on 10.9.5 or below...',
                  end='\n')
            return
        else:
            db = authorization_right_get(
                preference)
            if preference == 'system.preferences.datetime':
                print(' ○ {0:}'.format(preference.replace(
                    'system.preferences.datetime', 'Date & Time')))
                if db['shared'] is True:
                    print('  ★ Already set')
                    continue
                else:
                    db['shared'] = True
                    authorization_right_set(
                        preference, db)
                    print('  ✓ Completed', end='\n')
            else:
                # Print name of System Preference Pretty
                if preference == 'system.preferences':
                    print(' ○ {0:}'.format(preference.replace(
                        'system.preferences', 'System Preferences Overall')))
                elif preference == 'system.preferences.timemachine':
                    print(' ○ {0:}'.format(preference.replace(
                        'system.preferences.timemachine', 'Time Machine')))
                elif preference == 'system.preferences.energysaver':
                    print(' ○ {0:}'.format(preference.replace(
                        'system.preferences.energysaver', 'Energy Saver')))
                elif preference == 'system.preferences.network':
                    print(' ○ {0:}'.format(preference.replace(
                        'system.preferences.network', 'Network')))
                if db['group'] == 'admin':
                    db['group'] = 'everyone'
                    authorization_right_set(
                        preference, db)
                    print('  ✓ Completed', end='\n')
                else:
                    print('  ★ Already set')
                    continue

#-----------------------------------------------------------------
# Make admin accounts pretty function
def beautify_admin_accounts():
    '''This function will download accounts pictures for the admin
    accounts and change their display names'''

    print('• Beautify Admin Accounts', end='\n')
    # Beautification process
    for beauty_account in admin_list:
        # Connect to local account node
        beauty_account_node, _ = local_node.\
            recordWithRecordType_name_attributes_error_(
                kODRecordTypeUsers, beauty_account, None, None)
        # Account Picture
        check_output(['/usr/bin/curl',
                      admins_to_prepare[beauty_account]['picture_address'],
                      '--output',
                      admins_to_prepare[beauty_account]['picture_filename']],
                     stderr=PIPE)
        beauty_account_node.setValue_forAttribute_error_(
            admins_to_prepare[beauty_account]['picture_filename'],
            kODAttributeTypePicture, None)
        # Real Name
        beauty_account_node.setValue_forAttribute_error_(
            admins_to_prepare[beauty_account]['display_name'],
            kODAttributeTypeFullName, None)
        # Make Sure Account is Hidden
        beauty_account_node.setValue_forAttribute_error_(
            '1', 'dsAttrTypeNative:IsHidden', None)

        beauty_account_image = NSData.dataWithContentsOfFile_(
            admins_to_prepare[beauty_account]['picture_filename'])
        # JPEG Photo (Remove)
        beauty_account_node.setValue_forAttribute_error_(
            beauty_account_image, kODAttributeTypeJPEGPhoto, None)

# ----------------------------------------------------------------
# Downoad Munki from GitHub and install function
def munki_download_and_install():
    '''Downloads the latest version of munki from GitHub
    and installs it on the macOS Device. The bootstrap is
    also triggered to then begin building the machine'''
    print('• Download and Install Munki and trigger bootstrap', end='\n')

    # Get JSON Data from GitHub
    munki_github_url = 'https://api.github.com/repos/munki/munki/releases/latest'
    munki_url_output = check_output(['/usr/bin/curl', ' -i', '-H',
                                     '-H', 'Content-Type: application/json',
                                     '-X', 'GET', munki_github_url],
                                    stderr=PIPE)

    # Evaluate the output and find the download URL
    munki_url_data = json_loads(munki_url_output)
    munki_download_url = munki_url_data['assets'][0]['browser_download_url']

    # Download and install munki then trigger bootstrap
    check_output(['/usr/bin/curl', '-L', munki_download_url, '--output',
                  '/tmp/munki.pkg'], stderr=PIPE)
    check_output(['/usr/sbin/installer', '-pkg',
                  '/tmp/munki.pkg', '-target', '/'],
                 stderr=PIPE)
    check_output(['/usr/local/munki/managedsoftwareupdate',
                  '--set-bootstrap-mode'], stderr=PIPE)

# ---------------------------------------------------------------
# Main Function
if __name__ == '__main__':
    print('', end='\n')
    print('------------------------', end='\n')
    print('  Penn State MacAdmins  ', end='\n')
    print('------------------------', end='\n')
    # Variables needed
    prefix = 'Your Prefix Here'
    computer_name = build_computer_name()
    local_node, _ = connect_local()
    mwa_address = 'https://your.address.here:portnumber'
    basic_auth_string_mwa = 'Basic: YourAuthTagHere'
    admin_list = ['admin1', 'admin2']
    admins_to_prepare = {
        admin_list[0]: {
            'display_name': 'Display Name Here',
            'picture_address': 'Web address of account Picture',
            'picture_filename': 'Filename for picture downloaded'
        },
        admin_list[1]: {
            'display_name': 'Display Name Here',
            'picture_address': 'Web address of account Picture',
            'picture_filename': 'Filename for picture downloaded'
        }}
    # ^^ SideNote: Made dictionary as jamf makes its own admin and we
    # have a local admin we use

    # ------------------------------------------------------------
    # The loop to run all our commands or one
    while argv[6] != "exit":
        # Run the Set Computer Name Script
        if argv[5] == "computer":
            try:
                set_computer_name()
                print('  ✓ Completed', end='\n')
            except Exception:
                print('  ✖ Unable to set computer name', end='\n')
            if argv[4] == "DEP":
                argv[5] = "remotemanagement"
            else:
                argv[6] = "exit"

        # Run the Harden Remote Management Script
        elif argv[5] == "remotemanagement":
            try:
                harden_ard()
                harden_ssh(local_node)
                print('  ✓ Completed', end='\n')
            except Exception:
                print('  ✖ Unable to Harden Remote Management properly',
                      end='\n')
            if argv[4] == "DEP":
                argv[5] = "settings"
            else:
                argv[6] = "exit"

        # Run the Settings Setup for Time Zone and Daemon Script
        elif argv[5] == "settings":
            try:
                settings_setup()
                print('  ✓ Completed', end='\n')
            except Exception:
                print('  ✖ Unable to set settings for NTP Server'
                      'and Set Computer Name Daemon', end='\n')
            if argv[4] == "DEP":
                argv[5] = "createmanifest"
            else:
                argv[6] = "exit"

        # Create a Munki Manifest for the macOS Device
        elif argv[5] == "createmanifest":
            try:
                create_munki_manifest()
                print('  ✓ Completed', end='\n')
            except Exception:
                print('  ✖ Unable to create a munki manifest', end='\n')
            if argv[4] == "DEP":
                argv[5] = "beautifyadmin"
            else:
                argv[6] = "exit"
        # Make the admin accounts pretty
        elif argv[5] == "beautifyadmin":
            try:
                beautify_admin_accounts()
                print('  ✓ Completed', end='\n')
            except Exception as error:
                print(error)
                print('  ✖ Unable to add flair to the admin accounts.',
                      end='\n')
            if argv[4] == "DEP":
                argv[5] = "directorybinding"
            else:
                argv[6] = "exit"
        # Bind to EAD
        elif argv[5] == "directorybinding":
            print('• Bind to EAD', end='\n')
            try:
                check_output(['/usr/local/bin/jamf', 'policy',
                              '-event', 'fixEADBinding'], stderr=STDOUT)
                print('  ✓ Completed')
            except CalledProcessError as error:
                print('  ✖ Unable to bind to Enterprise Active Directory',
                      end='\n')
            if argv[4] == "DEP":
                argv[5] = "munki"
            else:
                argv[6] = "exit"

        # Download the latest version of munki and install it
        elif argv[5] == "munki":
            try:
                munki_download_and_install()
                print('  ✓ Completed', end='\n')
            except Exception as error:
                print('  ✖ Unable to install munki and trigger bootstrap',
                      end='\n')
            if argv[4] == "DEP":
                argv[5] = "sysprefs"
            else:
                argv[6] = "exit"
        # Unlock System Preference Panes
        elif argv[5] == "sysprefs":
            try:
                # Get the current version of macOS running on the client
                macOS_version = mac_ver()[0]
                macOS_version = version.StrictVersion(macOS_version)
                # Load Security Framework thanks to Tom burgin
                # https://gist.github.com/tburgin/ca7cf77767
                Security = CDLL(find_library("Security"))
                AuthorizationRightGet = Security.AuthorizationRightGet
                AuthorizationRightSet = Security.AuthorizationRightSet
                AuthorizationCreate = Security.AuthorizationCreate
                # Create list of system preferences that we want to modify
                system_prefs_to_change = [
                    'system.preferences',
                    'system.preferences.datetime',
                    'system.preferences.timemachine',
                    'system.preferences.energysaver',
                    'system.preferences.network',
                    ]
                power_prefs()
            except Exception as error:
                print(
                    '  ✖'
                    ' Unable to unlock all System Preference Panes specified',
                    end='\n')
            print('• Enable Location Services and set the computer to'
                  ' use automatic time and timezone')
            # Turn on Location Services and set Time Zone by Location
            location_services()
            # Turn on Auto Time and Auto TimeZone
            autotimezone()
            argv[6] = "exit"

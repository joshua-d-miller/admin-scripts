#!/usr/local/bin/psupython
# pylint:disable=C0103, C0111, E0611, E0602, E1101, W0612, W0703, W0612
'''
------------------------
  Penn State MacAdmins
------------------------
Performs the following:
  - Downloads the macOS Installer of our choice from our
    munki repo
  - Erases and Installs macOS
Notes:
  - Use Variable 4 in jamf Pro for installer location in munki
    repo
  - Use Variable 5 in jamf Pro for the authorization
  - Use Variable 6 in jamf Pro for the macOS Installer Name
-------------------------------------
  Joshua D. Miller - josh@psu.edu
  The Pennsylvania State University

  Last Update: September 8, 2020
  Tested: Python 3.8.0

-------------------------------------
'''

# Imports
from __future__ import print_function
from distutils.version import StrictVersion
from subprocess import check_output, PIPE
from re import search
from shutil import disk_usage
from sys import argv
import plistlib
import objc
from Foundation import (NSBundle, NSString)

def check_compatibility():
    '''Checks to make sure that the machine is compatible with
    the latest macOS'''
    current_model = get_macbook_model()
    valid_macbook_model = search(
        '(MacBookAir[5-8]|MacBookPro(9|1[0-6])'
        '|MacPro6|iMac(Pro)?1[3-9]?|MacBook(10|9|8)|Macmini[6-8])',
        current_model)
    mac_os_version_support = is_system_version_supported()
    free_space = calculate_free_space()

    if (valid_macbook_model and
            mac_os_version_support is True and
            free_space >= 25):
        return True
    return False

def io_key(keyname):
    '''Retreive specific properties about the hardware
    From Mike Lynn's GIST https://gist.github.com/pudquick/c7dd1262bd81a32663f0
    '''
    return IORegistryEntryCreateCFProperty(
        IOServiceGetMatchingService(
            0, IOServiceMatching(
                "IOPlatformExpertDevice".encode(
                    "utf-8"))), NSString.stringWithString_(keyname), None, 0)

def get_macbook_model():
    '''Returns the Model of MacBook'''
    return io_key('model').bytes().tobytes().decode('utf-8').rstrip('\x00')

def is_system_version_supported():
    '''Determine if Catalina is supported by the hardware'''
    system_version_plist = '/System/Library/CoreServices/SystemVersion.plist'
    with open(system_version_plist, 'rb') as f:
        sys_plist = plistlib.load(f)
    product_name = sys_plist['ProductName']
    product_version = sys_plist['ProductVersion']
    if StrictVersion(product_version) >= StrictVersion('10.9'):
        return True
    return False

def calculate_free_space():
    '''Determines how much free space is currently on the drive
    https://www.tutorialexample.com/a-simple-guide-to-python-
    get-disk-or-directory-total-space-used-space-and-free-
    space-python-tutorial/'''
    free_bytes = disk_usage('/')
    try:
        free_bytes = float(free_bytes[2])
        kb = free_bytes / 1024
    except Exception as error:
        return "Error"
    if kb >= 1024:
        M = kb / 1024
        if M >= 1024:
            G = M / 1024
            return G
        return M
    return kb
def download_macOS():
    '''Downloads macOS from the munki repo'''
    # Download latest macOS Installer
    try:
        check_output(['/usr/bin/curl', '-H', argv[5], argv[4],
                      '--output', '/tmp/macOSInstaller.dmg'],
                     stderr=PIPE)
    except Exception as error:
        print(error)
        exit(1)
    # Mount the Installer
    try:
        check_output(['/usr/bin/hdiutil', 'attach', '/tmp/macOSInstaller.dmg'],
                     stderr=PIPE)
    except Exception as error:
        print(error)
        exit(1)

def erase_and_install_macOS():
    '''Starts the installation which will wipe the device'''
    try:
        startos_install_path = ('/Volumes/Install macOS {0:}'
                                '/Install macOS {0:}.app/Contents'
                                '/Resources/startosinstall'.format(argv[6]))
        # Start the Installer which will erase all data
        check_output([startos_install_path, '--agreetolicense', '--forcequitapps',
                      '--eraseinstall'],
                     stderr=PIPE)
    except Exception as error:
        print(error)
        exit(1)

if __name__ == '__main__':
    print('', end='\n')
    print('------------------------', end='\n')
    print('  Penn State MacAdmins  ', end='\n')
    print('------------------------', end='\n')
    print('Erase and install macOS {0:}'.format(argv[6]))

    IOKit_bundle = NSBundle.bundleWithIdentifier_('com.apple.framework.IOKit')
    functions = [("IOServiceGetMatchingService", b"II@"),
                 ("IOServiceMatching", b"@*"),
                 ("IORegistryEntryCreateCFProperty", b"@I@@I"), ]
    objc.loadBundleFunctions(IOKit_bundle, globals(), functions)

    compatible = check_compatibility()
    if compatible is True:
        download_macOS()
        erase_and_install_macOS()
    else:
        print('macOS Catalina is NOT Supported on this device. Exiting...')

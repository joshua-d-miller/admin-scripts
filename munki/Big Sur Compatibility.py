#!/usr/local/bin/psupython
# pylint:disable=C0103
# encoding: utf-8
'''
------------------------
  Penn State MacAdmins
------------------------
Performs the following:
  - Checks that the device is compatible with macOS Big Sur
Notes:
  - Originally made by Hannes Juutilainen but made compatible with
    Python 3
Sources:
  - https://stackoverflow.com/questions/65290242/pythons-platform-mac-ver-reports-incorrect-macos-version/65402241
  - https://github.com/hjuutilainen/adminscripts/blob/master/check-10.15-catalina-compatibility.py
-------------------------------------
  Joshua D. Miller - josh@psu.edu
  The Pennsylvania State University

  Last Update: August 25, 2021
  Tested: Python 3.8.0
-------------------------------------
'''

from __future__ import print_function
import sys
import subprocess
import os
import plistlib
import re
import shutil
from ctypes import CDLL, c_uint, byref, create_string_buffer
from distutils.version import StrictVersion
import objc
from Foundation import (NSBundle, NSString, CFPreferencesCopyValue,
                        kCFPreferencesAnyUser, kCFPreferencesCurrentHost)


# ------------------------------------
#       Configuration Variables
# ------------------------------------
# Set this to False if you don't want any output, just the exit codes
verbose = True

# Set this to True if you want to add "bigsur_supported"
# custom conditional to /Library/Managed Installs/ConditionalItems.plist
update_munki_conditional_items = True

def logger(message, status, info):
    '''Logger'''
    if verbose:
        print('{0:>10}: {1:>17} {2:>8}'.format(
            message, status, info))
    else:
        pass


def conditional_items_path():
    '''Reads the current setting for ManagedInstallDir from
    ManagedInstalls.plist to determine the location of
    ConditionalItems.plist'''
    # <https://github.com/munki/munki/wiki/Conditional-Items>

    managed_installs_dir = CFPreferencesCopyValue(
        'ManagedInstallDir', 'ManagedInstalls', kCFPreferencesAnyUser,
        kCFPreferencesCurrentHost)
    # Make sure we're outputting our information to "ConditionalItems.plist"
    if managed_installs_dir:
        return os.path.join(managed_installs_dir, 'ConditionalItems.plist')

    # Munki default
    return '/Library/Managed Installs/ConditionalItems.plist'


def munki_installed():
    '''Determines if munki is installed on the client
    Thanks to Mike Lynn for showing this to me
    https://gist.github.com/pudquick/d64234a093e223e319d2d7a104d4b85e'''
    PackageKit = NSBundle.bundleWithPath_(
        '/System/Library/PrivateFrameworks/PackageKit.framework')
    PKReceipt = PackageKit.classNamed_('PKReceipt')
    munki_receipt = PKReceipt.receiptWithIdentifier_volume_(
        'com.googlecode.munki.core', '/')
    if munki_receipt:
        return True
    return False


def is_system_version_supported():
    '''Determine if Big Sur is supported by the hardware'''
    product_name = subprocess.check_output([
        '/usr/bin/sw_vers', '-productName'],
        stderr=subprocess.PIPE).decode('ascii').rstrip()
    product_version = subprocess.check_output([
        '/usr/bin/sw_vers', '-productVersion'],
        stderr=subprocess.PIPE).decode('ascii').rstrip()
    if StrictVersion(product_version) >= StrictVersion('11.0'):
        logger("System",
               "%s %s" % (product_name, product_version),
               "Failed")
        return False, product_version
    elif StrictVersion(product_version) >= StrictVersion('10.9'):
        logger("System",
               "%s %s" % (product_name, product_version),
               "OK")
        return True, ''
    else:
        logger("System",
               "%s %s" % (product_name, product_version),
               "Failed")
        return False, ''

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


def is_virtual_machine():
    '''Determines if this is a VM
    https://gist.github.com/pudquick/8107bb7b6e8d63eaddec7042c081e656'''
    libc = CDLL('/usr/lib/libc.dylib')
    size = c_uint(0)
    libc.sysctlbyname('machdep.cpu.features', None, byref(size), None, 0)
    buf = create_string_buffer(size.value)
    libc.sysctlbyname('machdep.cpu.features', buf, byref(size), None, 0)
    return buf.value

def is_supported_model():
    '''Determine if the model is supported'''

    current_model = get_macbook_model()

    supported_model_regex = (
        '(MacBook(10|9|8)|MacBookAir(10|[6-9])|MacBookPro1[1-7]|Macmini[7-9]'
        '|MacPro[6-7]|iMacPro1),\d|iMac(14,4|1[5-9],\d|20,\d)')

    if re.match(supported_model_regex, current_model):
        logger("Model", current_model, "OK")
        return True
    else:
        logger("Model", "\"%s\" is not supported" % current_model, "Failed")
        return False

def calculate_free_space():
    '''Determines how much free space is currently on the drive
    https://www.tutorialexample.com/a-simple-guide-to-python-
    get-disk-or-directory-total-space-used-space-and-free-
    space-python-tutorial/'''
    free_bytes = shutil.disk_usage('/Volumes/Macintosh HD/')
    try:
        free_bytes = float(free_bytes[2])
        kb = free_bytes / 1024
    except Exception as error:
        return "Error"
    if kb >= 1024:
        M = kb / 1024
        M = round(M)
        if M >= 53760:
            logger("Free Space", "{0:} MB".format(M), "OK")
            return True
        else:
            logger("Free Space", "{0:} MB".format(M), "Failed")
            return False

def append_conditional_items(dictionary):
    '''Appends to munki's conditional items PLIST'''
    current_conditional_items_path = conditional_items_path()
    if os.path.exists(current_conditional_items_path):
        with open(current_conditional_items_path, 'rb') as f:
            existing_dict = plistlib.load(f)
        output_dict = {**existing_dict, **dictionary}
    else:
        output_dict = dictionary

    with open(current_conditional_items_path, 'wb') as fp:
        plistlib.dump(output_dict, fp)


def main(argv=None):
    '''main function'''
    IOKit_bundle = NSBundle.bundleWithIdentifier_('com.apple.framework.IOKit')
    functions = [("IOServiceGetMatchingService", b"II@"),
                 ("IOServiceMatching", b"@*"),
                 ("IORegistryEntryCreateCFProperty", b"@I@@I"), ]
    objc.loadBundleFunctions(IOKit_bundle, globals(), functions)
    bigsur_supported_dict = {}

    if verbose:
        print('', end='\n')
        print('------------------------', end='\n')
        print('  Penn State MacAdmins  ', end='\n')
        print('------------------------', end='\n')
    # Run the checks
    model_passed = is_supported_model()
    system_version_passed, product_version = is_system_version_supported()
    disk_free_passed = calculate_free_space()

    if is_virtual_machine():
        bigsur_supported = 0
        bigsur_supported_dict = {'bigsur_supported': True}
    elif model_passed and system_version_passed and disk_free_passed:
        bigsur_supported = 0
        bigsur_supported_dict = {'bigsur_supported': True}
    else:
        bigsur_supported = 1
        bigsur_supported_dict = {'bigsur_supported': False}

    # Update "ConditionalItems.plist" if munki is installed
    if munki_installed() and update_munki_conditional_items:
        append_conditional_items(bigsur_supported_dict)
    if verbose and bigsur_supported == 0:
        print('')
        print('macOS Big Sur is supported by this machine')
    elif verbose and bigsur_supported == 1:
        if StrictVersion(product_version) >= StrictVersion('11.0'):
            print('')
            print('macOS Big Sur or newer is ALREADY installed on this machine')
        else:
            print('')
            print('macOS Big Sur is NOT supported by this machine')
    # Exit codes:
    # 0 = Big Sur is supported
    # 1 = Big Sur is not supported
    return bigsur_supported


if __name__ == '__main__':
    sys.exit(main())

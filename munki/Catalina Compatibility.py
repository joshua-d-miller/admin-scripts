#!/usr/local/bin/psupython
# pylint:disable=C0103
# encoding: utf-8
'''
------------------------
  Penn State MacAdmins
------------------------
Performs the following:
  - Checks that the device is compatible with macOS Catalina
Notes:
  - Originally made by Hannes Juutilainen but made comapitble with
    Python 3
-------------------------------------
  Joshua D. Miller - josh@psu.edu
  The Pennsylvania State University

  Last Update: September 2, 2020
  Tested: Python 3.8.0
  Original Source: (https://github.com/hjuutilainen/adminscripts
  /blob/master/check-10.15-catalina-compatibility.py)
-------------------------------------
'''

from __future__ import print_function
import sys
import subprocess
import os
import re
import plistlib
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

# Set this to True if you want to add "catalina_supported"
# custom conditional to /Library/Managed Installs/ConditionalItems.plist
update_munki_conditional_items = True

def logger(message, status, info):
    '''Logger'''
    if verbose:
        print('{0:>8}: {1:>25} {2:>8}'.format(
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
    '''Determine if Catalina is supported by the hardware'''
    system_version_plist = '/System/Library/CoreServices/SystemVersion.plist'
    with open(system_version_plist, 'rb') as f:
        sys_plist = plistlib.load(f)
    product_name = sys_plist['ProductName']
    product_version = sys_plist['ProductVersion']
    if StrictVersion(product_version) >= StrictVersion('10.9'):
        logger("System",
               "%s %s" % (product_name, product_version),
               "OK")
        return True
    logger("System",
           "%s %s" % (product_name, product_version),
           "Failed")
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


def get_board_id():
    '''Gets the Board ID of the macOS Device'''
    return io_key('board-id').bytes().tobytes().decode('utf-8').rstrip('\x00')


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
    non_supported_models = [
        'iMac4,1',
        'iMac4,2',
        'iMac5,1',
        'iMac5,2',
        'iMac6,1',
        'iMac7,1',
        'iMac8,1',
        'iMac9,1',
        'iMac10,1',
        'iMac11,1',
        'iMac11,2',
        'iMac11,3',
        'iMac12,1',
        'iMac12,2',
        'MacBook1,1',
        'MacBook2,1',
        'MacBook3,1',
        'MacBook4,1',
        'MacBook5,1',
        'MacBook5,2',
        'MacBook6,1',
        'MacBook7,1',
        'MacBookAir1,1',
        'MacBookAir2,1',
        'MacBookAir3,1',
        'MacBookAir3,2',
        'MacBookAir4,1',
        'MacBookAir4,2',
        'MacBookPro1,1',
        'MacBookPro1,2',
        'MacBookPro2,1',
        'MacBookPro2,2',
        'MacBookPro3,1',
        'MacBookPro4,1',
        'MacBookPro5,1',
        'MacBookPro5,2',
        'MacBookPro5,3',
        'MacBookPro5,4',
        'MacBookPro5,5',
        'MacBookPro6,1',
        'MacBookPro6,2',
        'MacBookPro7,1',
        'MacBookPro8,1',
        'MacBookPro8,2',
        'MacBookPro8,3',
        'Macmini1,1',
        'Macmini2,1',
        'Macmini3,1',
        'Macmini4,1',
        'Macmini5,1',
        'Macmini5,2',
        'Macmini5,3',
        'MacPro1,1',
        'MacPro2,1',
        'MacPro3,1',
        'MacPro4,1',
        'MacPro5,1',
        'Xserve1,1',
        'Xserve2,1',
        'Xserve3,1',
        ]
    current_model = get_macbook_model()
    if current_model in non_supported_models:
        logger("Model",
               "\"%s\" is not supported" % current_model,
               "Failed")
        return False
    logger("Model",
           current_model,
           "OK")
    return True


def is_supported_board_id():
    '''Determines if the board ID is supported'''
    platform_support_values = [
        'Mac-00BE6ED71E35EB86',
        'Mac-1E7E29AD0135F9BC',
        'Mac-2BD1B31983FE1663',
        'Mac-2E6FAB96566FE58C',
        'Mac-3CBD00234E554E41',
        'Mac-4B7AC7E43945597E',
        'Mac-4B682C642B45593E',
        'Mac-5A49A77366F81C72',
        'Mac-06F11F11946D27C5',
        'Mac-06F11FD93F0323C5',
        'Mac-6F01561E16C75D06',
        'Mac-7BA5B2D9E42DDD94',
        'Mac-7BA5B2DFE22DDD8C',
        'Mac-7DF2A3B5E5D671ED',
        'Mac-7DF21CB3ED6977E5',
        'Mac-9AE82516C7C6B903',
        'Mac-9F18E312C5C2BF0B',
        'Mac-27AD2F918AE68F61',
        'Mac-27ADBB7B4CEE8E61',
        'Mac-031AEE4D24BFF0B1',
        'Mac-031B6874CF7F642A',
        'Mac-35C1E88140C3E6CF',
        'Mac-35C5E08120C7EEAF',
        'Mac-42FD25EABCABB274',
        'Mac-53FDB3D8DB8CA971',
        'Mac-65CE76090165799A',
        'Mac-66E35819EE2D0D05',
        'Mac-66F35F19FE2A0D05',
        'Mac-77EB7D7DAF985301',
        'Mac-77F17D7DA9285301',
        'Mac-81E3E92DD6088272',
        'Mac-90BE64C3CB5A9AEB',
        'Mac-112B0A653D3AAB9C',
        'Mac-189A3D4F975D5FFC',
        'Mac-226CB3C6A851A671',
        'Mac-473D31EABEB93F9B',
        'Mac-551B86E5744E2388',
        'Mac-747B1AEFF11738BE',
        'Mac-827FAC58A8FDFA22',
        'Mac-827FB448E656EC26',
        'Mac-937A206F2EE63C01',
        'Mac-937CB26E2E02BB01',
        'Mac-9394BDF4BF862EE7',
        'Mac-50619A408DB004DA',
        'Mac-63001698E7A34814',
        'Mac-112818653D3AABFC',
        'Mac-A5C67F76ED83108C',
        'Mac-A369DDC4E67F1C45',
        'Mac-AA95B1DDAB278B95',
        'Mac-AFD8A9D944EA4843',
        'Mac-B809C3757DA9BB8D',
        'Mac-B4831CEBD52A0C4C',
        'Mac-BE0E8AC46FE800CC',
        'Mac-BE088AF8C5EB4FA2',
        'Mac-C3EC7CD22292981F',
        'Mac-C6F71043CEAA02A6',
        'Mac-CAD6701F7CEA0921',
        'Mac-CF21D135A7D34AA6',
        'Mac-DB15BD556843C820',
        'Mac-E43C1C25D4880AD6',
        'Mac-EE2EBD4B90B839A8',
        'Mac-F60DEB81FF30ACF6',
        'Mac-F65AE981FFA204ED',
        'Mac-F305150B0C7DEEEF',
        'Mac-FA842E06C61E91C5',
        'Mac-FC02E91DDD3FA6A4',
        'Mac-FFE5EF870D7BA81A',
        ]
    board_id = get_board_id()
    if board_id in platform_support_values:
        logger("Board ID",
               board_id,
               "OK")
        return True
    logger("Board ID",
           "\"%s\" is not supported" % board_id,
           "Failed")
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
    catalina_supported_dict = {}

    if verbose:
        print('', end='\n')
        print('------------------------', end='\n')
        print('  Penn State MacAdmins  ', end='\n')
        print('------------------------', end='\n')
    # Run the checks
    model_passed = is_supported_model()
    board_id_passed = is_supported_board_id()
    system_version_passed = is_system_version_supported()


    if is_virtual_machine():
        catalina_supported = 0
        catalina_supported_dict = {'catalina_supported': True}
    elif model_passed and board_id_passed and system_version_passed:
        catalina_supported = 0
        catalina_supported_dict = {'catalina_supported': True}
    else:
        catalina_supported = 1
        catalina_supported_dict = {'catalina_supported': False}

    # Update "ConditionalItems.plist" if munki is installed
    if munki_installed() and update_munki_conditional_items:
        append_conditional_items(catalina_supported_dict)

    if verbose and catalina_supported == 0:
        print('')
        print('macOS Catalina is supported by this machine')
    elif verbose and catalina_supported == 1:
        print('')
        print('macOS Catalina is NOT supported by this machine')
    # Exit codes:
    # 0 = Catalina is supported
    # 1 = Catalina is not supported
    return catalina_supported


if __name__ == '__main__':
    sys.exit(main())

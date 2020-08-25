#!/usr/local/bin/psupython
# -*- coding: utf-8 -*-
# pylint:disable=C0103, R1702, W0612, W0703
'''
------------------------
  Penn State MacAdmins
------------------------
Performs the following:
  - Removes duplicates from munki if AutoPKG failed to
    run a makecatalogs before it imported the same item again.
-------------------------------------
  Joshua D. Miller - josh@psu.edu
  The Pennsylvania State University

  Last Update: August 21, 2020
  Tested: Python 3.8.0
-------------------------------------
'''

from __future__ import print_function
from os import devnull, remove, walk
from sys import argv
import subprocess

def remove_duplicates_from_repo():
    '''Removes duplicates from the munki repo'''
    # This for loop will search your Munki Repository for duplications
    count = 1
    try:
        while count != 10:
            DUPE_TO_REMOVE = '__' + str(count)
            for dirname, dirnames, filenames in walk(argv[1]):
                for filename in filenames:
                    # Is the current file a duplication in the Munki Repo?
                    if DUPE_TO_REMOVE in filename:
                        try:
                            # Remove the File
                            remove(dirname + '/' + filename)
                            print('  ✓ {0:} has been removed.'.format(filename))
                        except StandardError as error:
                            print('  ✖ Could not remove the file {0:}'.format(filename))
                            print('    {0:}'.format(error))
                    else:
                        continue
            count = count + 1
    except Exception as error:
        print('  ✖ Could not traverse directory or other unspecified error. \
          Please make sure Munki Repo is mounted.')

def update_catalogs():
    '''Updates munki catalogs'''
    try:
        print('• Updating munki catalogs')
        # Suppress the output of makecatalogs
        our_null = open(devnull, 'w')
        subprocess.check_call(
            ['/usr/local/munki/makecatalogs'],
            stdout=our_null, stderr=our_null)
        print('  ✓ Completed')
    except Exception as error:
        print('Could not update the Munki catalogs.  Please run makecatalogs')
        print(error)

if __name__ == '__main__':
    print('', end='\n')
    print('------------------------', end='\n')
    print('  Penn State MacAdmins  ', end='\n')
    print('------------------------', end='\n')
    if argv[1] == "":
        print('No munki repo specified! Exiting...')
    else:
        print('• Remove Duplicates from munki repo')
        remove_duplicates_from_repo()
        update_catalogs()

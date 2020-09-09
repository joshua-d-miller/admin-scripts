#!/usr/local/bin/psupython
# pylint:disable=C0103, W0703
# encoding: utf-8
'''
------------------------
  Penn State MacAdmins
------------------------
Performs the following:
  - Determines the version of Nessus Installed
Notes:
  - Nessus package receipt is either 1.0 or verison 0
  - Use as installcheck_script for munki
-------------------------------------
  Joshua D. Miller - josh@psu.edu
  The Pennsylvania State University

  Last Update: September 9, 2020
  Tested: Python 3.8.0

-------------------------------------
'''

from __future__ import print_function
import re
from subprocess import check_output, PIPE


def determine_nessus_version():
    '''This function will determine the version of the
    Nessus Agent we are running'''
    try:
        nessusd_output = check_output(
            ['/Library/NessusAgent/run/sbin/nessuscli',
             '--version'], stderr=PIPE).decode("utf-8")
        result = re.search(r'\(Nessus Agent\) 8\.1\.0', nessusd_output)
        if result:
            exit(1)
        else:
            exit(0)
    except Exception as error:
        print(error)
        exit(0)


if __name__ == '__main__':
    determine_nessus_version()

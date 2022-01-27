#!/bin/sh
: '
------------------------
  Penn State MacAdmins
------------------------
Performs the following:
  - Uses the serial number of the device
  to send the EnableRemoteDesktop MDM
  command to the device
Notes:
  - It is recommended that you continue
  to use the kickstart command to set
  access after this command has completed
-------------------------------------
  Joshua D. Miller - josh@psu.edu
  The Pennsylvania State University

  Last Update: January 6, 2022
-------------------------------------
'
### Variables ###
jssURL=$(/usr/bin/defaults read \
  /Library/Preferences/com.jamfsoftware.jamf.plist jss_url | sed s'/.$//')
apiUser=$4
apiPassword=$5

### Get Serial Number of Device ###
SERIAL_NUMBER=$(/usr/sbin/ioreg -c IOPlatformExpertDevice \
  -d 2 \
  | awk -F\" '/IOPlatformSerialNumber/{print $(NF-1)}')

### Get XML for Device in jmaf Pro ###
DEVICE_XML=$(/usr/bin/curl -sfku "${apiUser}":"${apiPassword}" \
  "$jssURL/JSSResource/computers/serialnumber/$SERIAL_NUMBER" \
  -X GET \
  -H "accept: application/xml")

### Grab Device ID From XML ###
DEVICEID=$(/usr/bin/xmllint --xpath '//computer/general/id/text()' \
  - <<< "$DEVICE_XML" 2> /dev/null)

### Send Enable Remote Desktop Command ###
if /usr/bin/curl -fu "${apiUser}":"${apiPassword}" \
 "$jssURL/JSSResource/computercommands/command/EnableRemoteDesktop/id/$DEVICEID" \
 -X POST
then
  /bin/echo "Screen Sharing was enabled for device ${SERIAL_NUMBER}"
else
  /bin/echo "Screen Sharing was NOT enabled for device ${SERIAL_NUMBER}"
fi

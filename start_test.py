import subprocess
import os
import time


print("Starting gps module")

log = open('/home/pi/.driver_analytics/log_out.txt', 'w')  # so that data written to it will be appended


os.system('pkill -f central')
os.system('pkill -f param_daemon')
os.system('pkill -f gps')


ini_path="/home/pi/.driver_analytics/ini/parameters_rpi.ini"
central_path="/home/pi/.driver_analytics/bin/central"
param_daemon_path="/home/pi/.driver_analytics/bin/param_daemon"
gps_path="/home/pi/.driver_analytics/bin/gps"

test_central = subprocess.Popen([central_path,"-u","-s"], stdout=log, stderr=log)

time.sleep(1)

test_param_daemon = subprocess.Popen([param_daemon_path,ini_path], stdout=log, stderr=log,)

time.sleep(1)

test_gps = subprocess.Popen(gps_path, stdout=log, stderr=log,)

time.sleep(5)

print("Modules started")
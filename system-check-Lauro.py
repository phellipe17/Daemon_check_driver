#!/usr/bin/python
import os
import subprocess
import re
import time
print("\n\nDriverAnalytics 3.2 health check for HAT PCB\n\n")
### GPS ####
print("Checking GPS health...")
gps_device_fd = "/dev/serial0"
gps_device = os.open(gps_device_fd, os.O_RDWR)
gps_data = ""
for i in range(1024):
   gps_data += os.read(gps_device, 2048)
if "$GPRMC" in gps_data or "$GNRMC" in gps_data:
   #print("GPS: OK");    
   print("\033[1;32;40m GPS: OK \033[0;37;40m");
else:
   #print("GPS: ERROR");
   print("\033[1;31;40m GPS: ERROR \033[0;37;40m");
### IMU ###
print("Checking IMU health...")
i2c_process = subprocess.Popen(["/home/pi/.driver_analytics/bin/imu", "RTIMULib"], stdout=subprocess.PIPE)
#i2c_process_out = str(i2c_process.communicate())
is_imu_ok = False
for i in range(0, 9):
   line = str(i2c_process.stdout.readline())
   if "init complete" in line:
      is_imu_ok = True
      break;
i2c_process.terminate()
if is_imu_ok :
   #print("IMU: OK")
   print("\033[1;32;40m IMU: OK \033[0;37;40m");
else:
   #print("IMU: ERROR")
   print("\033[1;31;40m IMU: ERROR \033[0;37;40m");
### SIM-CARD and MODEM ###
print("Checking SIM card and Modem health...")
sim_process = subprocess.Popen(["/home/pi/sim_card.sh"], stdout=subprocess.PIPE)
#sim_process_out = str(i2c_process.communicate())
is_sim_ok = False
for i in range(0, 10):
   line = str(sim_process.stdout.readline())
   if "ICCID READ" in line:
       is_sim_ok = True
       break;
sim_process.terminate()
if is_sim_ok:
   #print("SIM CARD: OK")
   print("\033[1;32;40m SIM CARD: OK \033[0;37;40m")
else:
   #print("SIM CARD: ERROR")
   print("\033[1;31;40m SIM CARD: ERROR \033[0;37;40m")

modem_process = subprocess.Popen(["/home/pi/internet.sh"], stdout=subprocess.PIPE)
is_modem_ok = False
time.sleep(5)
with open ("/home/pi/log_wvdial.txt", "r") as myfile:
   ip_address = False
   connected = False
   modem_data=myfile.readlines()
   for line in modem_data:
      if "IP address" in line:
         ip_address = True
      if "Connected" in line:
        connected = True
   is_modem_ok = ip_address and connected
modem_process.terminate()
if is_modem_ok:
   #print("MODEM: OK")
   print("\033[1;32;40m MODEM: OK \033[0;37;40m\n\n")
else:
   #print("MODEM: ERROR")
   print("\033[1;31;40m MODEM: ERROR \033[0;37;40m\n\n");

#-----------------------------------------------------------------------------------------

def check_camera_status():
   
   print("Checking Camera status...")
   
   try:
      subprocess.run(["raspistill", "-o", "/tmp/camera_test.jpg", "-w", "640", "-h", "480"], check=True)
      print("\033[1;32;40m CAMERA: OK \033[0;37;40m\n\n")
   except subprocess.CalledProcessError as e:
      print("\033[1;31;40m CAMERA: ERROR ({e.returncode})\033[0;37;40m\n\n")

check_camera_status()
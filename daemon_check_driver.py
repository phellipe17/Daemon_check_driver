import time
import socket
#import psutil
import os
import subprocess
import serial

#from daemonize import Daemonize
daemon_name = 'chk_status'

def color(msg, collor):
    if collor == "green":
        return f'\033[1;32;40m{msg}\033[0m'
    elif collor == "red":
        return f'\033[1;31;40m{msg}\033[0m'
    elif collor == "yellow":
        return f'\033[1;33;40m{msg}\033[0m'
    elif collor == "magenta":
        return f'\033[1;35;40m{msg}\033[0m'

# This function runs a shell command specified as command and returns its standard output and standard error as strings.
def run_bash_command(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    return output.decode(), error.decode()


def imu_check():
    command2 = 'i2cdetect -y 1 | grep -ia 68'
    result, error=run_bash_command(command2)
    if (result != ''):
        return color(' ON ','green')
    else:
        return color(' OFF ','red')

    # ---- Opcao 2 -----
    # bus_number = 1
    # command = f"i2cdetect -y {bus_number}"
    # result = subprocess.check_output(command, shell=True, text=True)
    
    # for line in result.split('\n')[1:]:
    #     if not line:
    #         continue
    #     address_range, *addresses = line.split()
    #     for address in addresses:
    #         if address != "--":
    #             print(f"Device detected at address {address} on bus {bus_number}")

# capture_first_line(command): This function executes a shell command and captures its first line of output. 
# It is designed to terminate the process after reading the first line.
# def capture_first_line(command):
#     first_line=''
#     try:
#         process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
#         lines= process.stdout.readlines()
#         process.terminate()  # Encerra o processo após ler a primeira linha
#         if lines:
#             first_line= lines[0].strip()
#             return first_line
#         else:
#             return ''
#     except Exception as e:
#         return f"Erro ao executar o comando: {str(e)}"
    
# def read_iccid():
#     command_icc='sudo timeout 2 cat /dev/ttyUSB4 & sudo stty -F /dev/ttyUSB4 raw -echo & sudo echo -e "AT+CCID\r" > /dev/ttyUSB4'
#     result, error=run_bash_command(command_icc)
#     print(error)
#     if 'OK' in result:
#         return '\033[1;32;40mSim inserted\033[0m'
#     else:
#         return '\033[1;31;40mSim not inserted\033[0m'
        


# check_internet(): This function checks for internet connectivity by attempting to create a connection to 
# www.google.com. It returns True if the connection is successful and False otherwise.
def check_internet():
    try:
        # Tente fazer uma conexão com um servidor remoto (por exemplo, o Google)
        socket.create_connection(("www.google.com", 80))
        return color(' ON ','green')
    except OSError:
        return color(' OFF ','red')
 
# get_machine_storage(): This function calculates and returns the total and free storage space on the root filesystem. 
# If the total storage is less than 10 GB, it attempts to expand the root filesystem and requests a reboot.
def get_machine_storage():
    total_size_status = ''
    free_size_status = ''
    result=os.statvfs('/')
    block_size=result.f_frsize
    total_blocks=result.f_blocks
    free_blocks=result.f_bfree
    # giga=1024*1024*1024
    giga=1000*1000*1000
    total_size=total_blocks*block_size/giga
    free_size=free_blocks*block_size/giga
    total_size = round(total_size)
    free_size = round(free_size)
    if (total_size > 10):
        total_size_status = color(' OK ','green')
    else:
        total_size_status = color(' NOK ','red')

    if (free_size < 0.05 * total_size):
        free_size_status = color(' NOK ','red')
    else:
        free_size_status = color(' OK ','green')
    return total_size_status, free_size_status

# clear_log_file(log_file_path): This function clears the contents of a log file specified by log_file_path.
def clear_log_file(log_file_path):
    with open(log_file_path, 'w') as file:
        file.write("") 


# chk_gps(): This function checks the GPS status by running a command that reads data from the /dev/serial0
# device and checks if the first line contains the string "$GNGSA,A,3." It returns "GPS ON" if the condition
# is met, otherwise "GPS OFF."
    
#Cheking gps health with bytes
# def chk_gps2():
#     gps_device_fd = "/dev/serial0"
#     gps_device = os.open(gps_device_fd, os.O_RDWR)
#     gps_data = ""
#     danger =3
#     phrase=''
#     for i in range(1024):
#         gps_data += os.read(gps_device, 2048).decode('utf-8') 
#     if "$GNGSA,A,3" in gps_data or "$GNGSA,A,2" in gps_data:
#         danger="\033[1;32;40mOK\033[0m"
#         phrase= "\033[1;32;40mINFO SATELLITE\033[0m"
#     elif "$GPRMC" in gps_data or "$GNRMC" in gps_data:
#         danger ="\033[1;33;40mOK\033[0m"
#         phrase= "\033[1;33;40mNOINFO SATELLITE\033[0m"
#     else:    
#         danger="\033[1;31;40mNOK\033[0m"
#         phrase= "\033[1;31;40mERROR\033[0m"
#     return danger, phrase 

def chk_gps3():
    gps_device_fd = "/dev/serial0"
    gps_device = os.open(gps_device_fd, os.O_RDWR)
    gps_data = ""
    for _ in range(1024):
        gps_data += os.read(gps_device, 2048).decode('utf-8')

    validity_status = None
    num_satellites = None
    
    nmea_sentences = gps_data.split('\n') # Split the GPS data into individual NMEA sentences
    countA = 0
    countV = 0
    fix_values = []
    snr_values = []
    satellites = []
    for sentence in nmea_sentences:
        parts = sentence.split(',')
        if sentence[3:6] == 'GSA':
            # Parse the GNGSA sentence for fix mode, number of satellites, and signal strength
            fix_values.append(int(parts[2]))
            num_satellites = len([s for s in parts[3:15] if s])
            if len(parts) >= 16:
                satellites.append(float(num_satellites))
        elif sentence[3:6] == 'RMC':
            # Parse the GPRMC sentence for validity status
            validity_status = parts[2]
            if parts[2] == 'A':
                countA += 1 
            else:
                countV += 1
        elif sentence[3:6] == 'GSV'and len(parts) >= 8:
            try:
                snr = int(parts[7])
                snr_values.append(snr)
            except ValueError:
                pass
            
    # Determine the result based on parsed information
    validity_status = 'A' if countA > 1.75 * countV else 'V'
    avg_snr = sum(snr_values) / len(snr_values) if len(snr_values) > 0 else 0
    avg_num_satellites = sum(satellites) / len(satellites) if len(satellites) > 0 else 0
    avg_fix = sum(fix_values) / len(fix_values) if len(fix_values) > 0 else 0
    fix = 0
    sat_num = 0
    sig_str = 0

    if avg_fix > 2 and validity_status == 'A':
        fix = color("3D", "green")
    elif avg_fix <= 2 and validity_status == 'A':
        fix = color("2D", "yellow")
    else:
        fix = color("No Fix", "red")

    if snr_values:
        if avg_snr >= 35:
            sig_str = color(f"{avg_snr:.2f}", "green")
        elif avg_snr >= 25:
            sig_str = color(f"{avg_snr:.2f}", "yellow")
        else:
            sig_str = color(f"{avg_snr:.2f}", "red")

    if num_satellites is not None:
        if avg_num_satellites >= 8:
            sat_num = color(f"{avg_num_satellites:.0f}", "green")
        elif avg_num_satellites >= 5:
            sat_num = color(f"{avg_num_satellites:.0f}", "yellow")
        else:
            sat_num = color(f"{avg_num_satellites:.0f}", "red")
    
    return fix, sig_str, sat_num
    
def chk_dial_modem():
    modem_command = 'ip addr | grep -ia ppp0'
    result, error=run_bash_command(modem_command)
    if(result != ''):
        return color(' ON ','green')
    else:
        return color(' OFF ','red')

def chk_wlan_interface():
    wlan_command = 'ip addr show wlan0'
    result, error = run_bash_command(wlan_command)
    if 'UP' in result:
        return color(' ON ','green')
    else:
        return color(' OFF ','red')

def chk_ethernet_interface():
    eth_command = 'ip addr show eth0'
    result, error = run_bash_command(eth_command)
    if 'UP' in result:
        return color(' ON ','green')
    else:
        return color(' OFF ','red')

def chk_ttyLTE():
    command = 'ls /dev/'
    result,error = run_bash_command(command)
    if 'ttyLTE' in result:
        return color('Mounted','green')
    else:
        return color('Unmouted','red')

def chk_ttyARD():
    command = 'ls /dev/'
    result,error = run_bash_command(command)
    if 'ttyARD' in result:
        return color('Mounted','green')
    else:
        return color('Unmouted','red')


def send_serial_command(command):
    try:
        ser = serial.Serial("/dev/ttyMDN", 115200)
        
        # Send the provided command
        ser.write(command)

        # Read lines with a timeout
        counter = 0
        response = ""

        while counter < 10:  # 10 seconds timeout (adjust as needed)
            bs = ser.readline()
            response += bs.decode()

            if "Error" in response:
                return "Error"
            elif "OK" in response:
                return response
            
            counter +=1

        print("Timeout reached. Exiting.")
        return "Timeout"
    except serial.SerialException as e:
        print(f"Error: {e}")
        return "Serial Exception"
    finally:
        # Always close the serial connection
        if ser.isOpen():
            ser.close()

def modem_signal():
    text_signal =b'AT+CSQ\r'
    result= send_serial_command(text_signal)
    result2= result.split("\n")[1].split(":")[1].strip()	    
    if len(result2)>0:
        signal_strength=float(result2.replace(',','.'))
        if(signal_strength==99):
            return color('No signal','magenta')
        elif(signal_strength>=31):
            return color(' Strong signal ','green')
        elif(signal_strength<31 and signal_strength>=2):
            return color(' Medium signal ','yellow')
        elif(signal_strength<2 and  signal_strength>=0):
            return color(' Low signal ','red')
    else:
        return 0

def modem_status():
    text_status =b'AT+CPAS\r'
    result = send_serial_command(text_status)
    result2 = result.split(":")[1].strip()
    if "ok" in result2.lower():
        return color(' OK ','green')
    elif "error" in result2.lower():
        return color(' NOK ','red')
    else:
        return "Undefined"
    
def get_ccid():
    command = b'AT+QCCID\r'
    result = send_serial_command(command)
    # print(result)
    ccid = result.split("\n")[1].split(" ")[1]
    if 'OK' in result and ccid:
        return color(f' Sim inserted - CCID: {ccid}', 'green')
    else:
        return color(' Sim not inserted', 'red')

#checa se é possivel tirar um frame com a camera para testar se ela esta funcionando
# def check_camera_status():
#    try:
#       subprocess.run(["raspistill", "-o", "/tmp/camera_test.jpg", "-w", "640", "-h", "480"], check=True,stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
#       return color(" OK ", "green")
#    except subprocess.CalledProcessError as e:
#       return color(f" ERROR({e.returncode})", "red")
   
#    inclusao de verificacao se camera está conectada e pronta para uso
def check_camera_status():
    try:
       subprocess.run(["raspistill", "-o", "/tmp/camera_test.jpg", "-w", "640", "-h", "480"], check=True,stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
       available = color(" YES ", "green")
    except subprocess.CalledProcessError as e:
       available = color(f" NO - error no:({e.returncode})", "red")
    
    command = "vcgencmd get_camera"
    output, error = run_bash_command(command)
    detected = color(" YES ", "green") if "detected=1" in output else color(" NO ", "red")
    connected = color(" YES ", "green") if "supported=1" in output else color(" NO ", "red")
        
    return detected, connected, available 

def swap_memory():
    command = "free -h | grep -iA 1 swap | tail -n 1 | awk '{printf \"%.2f%%\", ($3/$2)*100}'"
    output, error = run_bash_command(command)
    
    if error:
        return color(f" Error: {error} ", "red")
    else:
        return color(f" {output}", "green")
    

def usage_cpu():
    # command = "top -b -n 1 | awk '/%CPU/ {print 100 - $8"%"}'"
    command = "top -bn1 | grep '^%Cpu(s)' | awk '{print $8}'"                                                     
    output, error = run_bash_command(command)
    idle_time = float(output.strip().replace(',', '.'))
    usage = 100 - idle_time
    if error:
        return color(f" Error: {error} ", "red")
    else:
        if idle_time >= 80:
            return color(f" {usage}% ", "green")
        elif idle_time >= 50:
            return color(f" {usage}% ", "yellow")
        elif idle_time >= 30:
            return color(f" {usage}% ", "magenta")
        elif idle_time < 30:
            return color(f" {usage}% ", "red")
    

def main():
    log_file_path = f'/tmp/{daemon_name}.log'
    #clear_log_file(log_file_path)  # Apaga o conteúdo do arquivo de log ao iniciar
    #while True:
    with open(log_file_path, 'a') as file:
        current_time = time.strftime('\033[1;36;40m%Y-%m-%d %H:%M:%S\033[0m')
        total_size,free_size = get_machine_storage()
        fix, sig_str, sat_num = chk_gps3()
        # status_camera = check_camera_status()
        detected,connected,available = check_camera_status()
        conncetion_chk = check_internet()
        Process_modem = chk_dial_modem()
        imu = imu_check()
        # read_sim = get_ccid()
        signal = modem_signal()
        status = modem_status()
        swapa = swap_memory()
        cpu = usage_cpu()
        interface_e = chk_ethernet_interface()
        interface_wlan = chk_wlan_interface()
        Lte = chk_ttyLTE()
        Ard = chk_ttyARD()
        file.write(f'\n\033[1;34;40m---Driver_analytics Health---\033[0m\nDate:\n\t- {current_time} \n'
                    f'Connection Analysis:\n\t- connection internet: {conncetion_chk}\n\t- Modem IP:{Process_modem}\n\t- Signal: {signal} \n\t- Status: {status} \n'
                    f'SD Card Analysis:\n\t- Expanded:{total_size}\n\t- Free disk:{free_size} \n'
                    f'GPS Analysis:\n\t- GPS Fix: {fix}\n\t- Signal Strength: {sig_str}  \n\t- Avaible Satellites: {sat_num} \n'
                    # f'Camera Analysis:\n\t- Camera: {status_camera}\n'
                    f'Camera Analysis:\n\t- Detected: {detected}\n\t- Connected: {connected}\n\t- Available: {available}\n'
                    f'IMU Analysis:\n\t- Active: {imu}\n'
                    f'System Analysis:\n\t- Swap usage: {swapa} \n\t- CPU Usage: {cpu} \n\t- ETH0 Interface: {interface_e} \n\t- WLAN Interface: {interface_wlan}\n\t'
                    f'- USB LTE: {Lte} \n\t- USB ARD: {Ard}\n')
    print(color(" Log gerado! ", "green")) 
        #time.sleep(3)           


if __name__ == '__main__':
#     #daemon = Daemonize(app=daemon_name, pid=f'/tmp/{daemon_name}.pid', action=main)
#     #daemon.start()
    main()

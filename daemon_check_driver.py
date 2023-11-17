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

# This function runs a shell command specified as command and returns its standard output and standard error as strings.
def run_bash_command(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    return output.decode(), error.decode()


def imu_check():
    command2 = 'i2cdetect -y 1 | grep -ia 68'
    result, error=run_bash_command(command2)
    if (result != ''):
        return color(' ON ', 'green')
    else:
        return color(' OFF ', 'red')

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
        return color(' OK ', 'green')
    except OSError:
        return color(' NOK ', 'red')

# get_machine_storage(): This function calculates and returns the total and free storage space on the root filesystem. 
# If the total storage is less than 10 GB, it attempts to expand the root filesystem and requests a reboot.
def get_machine_storage():
    phrase = ''
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
        size_ok = color(' OK ', 'green')
    else:
        size_ok = color(' NOK ', 'red')

    if (free_size < 0.05 * total_size):
        free_size_ok = color(' NOK ', 'red')
    else:
        free_size_ok = color(' OK ', 'green')
    return size_ok, free_size_ok

# clear_log_file(log_file_path): This function clears the contents of a log file specified by log_file_path.
def clear_log_file(log_file_path):
    with open(log_file_path, 'w') as file:
        file.write("") 


# chk_gps(): This function checks the GPS status by running a command that reads data from the /dev/serial0
# device and checks if the first line contains the string "$GNGSA,A,3." It returns "GPS ON" if the condition
# is met, otherwise "GPS OFF."
def chk_gps():
    gps_command = 'timeout 1 cat /dev/serial0 | grep -ia gsa'
    linha1 = capture_first_line(gps_command)
    print(linha1)
    linha1 = linha1[:10]
    #print(f' info gps: {linha1}')
    if (linha1 == '$GNGSA,A,3' or linha1 == '$GNGSA,A,2'):
        return f"GPS {color(' OK ', 'green')}"
    else:
        return ' GPS\033[1;31;40m OFF \033[0m'
    
#Cheking gps health with bytes
def chk_gps2():
    gps_device_fd = "/dev/serial0"
    gps_device = os.open(gps_device_fd, os.O_RDWR)
    gps_data = ""
    danger =3
    phrase=''
    for i in range(1024):
        gps_data += os.read(gps_device, 2048).decode('utf-8') 
    if "$GNGSA,A,3" in gps_data or "$GNGSA,A,2" in gps_data:
        danger = color(' OK ', 'green')
        phrase = color(' INFO SATELLITE ', 'green')
    elif "$GPRMC" in gps_data or "$GNRMC" in gps_data:
        danger = color(' OK ', 'yellow')
        phrase = color(' INFO SATELLITE ', 'yellow')
    else:    
        danger = color(' NOK ', 'red')
        phrase = color(' ERROR ', 'red')
    return danger, phrase 


def chk_gps3():
    gps_device_fd = "/dev/serial0"
    gps_device = os.open(gps_device_fd, os.O_RDWR)
    gps_data = ""
    for _ in range(1024):
        gps_data += os.read(gps_device, 2048).decode('utf-8')
    validity_status = None
    num_satellites = None
    signal_strength = None
    
    nmea_sentences = gps_data.split('\n') # Split the GPS data into individual NMEA sentences
    gsa_counter = 0
    avg_signal_strength = 0
    avg_num_satellites = 0
    countA = 0
    countV = 0
    avg_fix = 0
    for sentence in nmea_sentences:
        if sentence[3:6] == 'GSA':
            # Parse the GNGSA sentence for fix mode, number of satellites, and signal strength
            parts = sentence.split(',')
            avg_fix += int(parts[2])
            num_satellites = len([s for s in parts[3:15] if s])
            if len(parts) >= 16:
                signal_strength = parts[16]
                if signal_strength:
                    avg_signal_strength += float(signal_strength)
                    avg_num_satellites += float(num_satellites)
            gsa_counter +=1
        elif sentence[3:6] == 'RMC':
            # Parse the GPRMC sentence for validity status
            parts = sentence.split(',')
            validity_status = parts[2]
            if parts[2] == 'A':
                countA += 1 
            else:
                countV += 1
    
    # Determine the result based on parsed information
    validity_status = 'A' if countA > 1.75 * countV else 'V'
    avg_signal_strength /= gsa_counter
    avg_num_satellites /= gsa_counter
    avg_fix /= gsa_counter
    fix = 0
    sat_num = 0
    sig_str = 0

    if avg_fix > 2 and validity_status == 'A':
        fix = color(' 3D ', 'green')
    elif avg_fix <= 2 and validity_status == 'A':
        fix = color(' 2D ', 'yellow')
    else:
        fix = color(' No Fix ', 'red')

    if signal_strength is not None:
        if avg_signal_strength > 0.5:
            sig_str = color(f"{avg_signal_strength:.2f}", 'green')
        elif avg_signal_strength > 0.5:
            sig_str = color(f"{avg_signal_strength:.2f}", 'yellow')
        else:
            sig_str = color(f"{avg_signal_strength:.2f}", 'red')

    if num_satellites is not None:
        if avg_num_satellites > 0.5:
            sat_num = color(f"{avg_num_satellites:.0f}", 'green')
        elif avg_num_satellites > 0.2:
            sat_num = color(f"{avg_num_satellites:.0f}", 'yellow')
        else:
            sat_num = color(f"{avg_num_satellites:.0f}", 'red')
    
    return fix, sig_str, sat_num
    
def chk_dial_modem():
    modem_command = 'ip addr | grep -ia ppp0'
    result, error=run_bash_command(modem_command)
    if(result != ''):
        return color(' ON ', 'green')
    else:
        return color(' OFF ', 'red')


def chk_wlan_interface():
    wlan_command = 'ip addr show wlan0'
    result, error = run_bash_command(wlan_command)
    if 'UP' in result:
        return color(' ON ', 'green')
    else:
        return color(' OFF ', 'red')

def chk_ethernet_interface():
    eth_command = 'ip addr show eth0'
    result, error = run_bash_command(eth_command)
    if 'UP' in result:
        return color(' ON ', 'green')
    else:
        return color(' OFF ', 'red')

def send_serial_command(command):
    try:
        ser = serial.Serial("/dev/ttyUSB4", 115200, timeout=5)
        
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
        if(signal_strength>20):
            return color(' Strong signal ', 'green')
        elif(signal_strength<=20 & signal_strength>15):
            return color(' Mediun signal ', 'yellow')
        else:
            return color(' Low signal ', 'red')
    else:
        return 0

def modem_status():
    text_status =b'AT+CPAS\r'
    result = send_serial_command(text_status)
    result2 = result.split(":")[1].strip()
    if "ok" in result2.lower():
        return color(' ON ', 'green')
    elif "error" in result2.lower():
        return color(' ERROR ', 'red')
    else:
        return "Undefined"
        
    #jeito alternativo
    # command_status='sudo timeout 2 cat /dev/ttyUSB4 & sudo stty -F /dev/ttyUSB4 raw -echo & sudo echo -e "AT+CPAS\r" > /dev/ttyUSB4'
    # result,error = run_bash_command(command_status)
    # if 'ERROR' in result:
    #     return '\033[1;31;40m Error\033[0m'
    # else:
    #     return '\033[1;32;40m Ok \033[0m'

def get_ccid():
    command = b'AT+QCCID\r'
    result = send_serial_command(command)
    ccid = result.split("\n")[1].split(" ")[1]
    if 'OK' in result and ccid:
        return color(f' Sim inserted - CCID: {ccid} ', 'green')
    else:
        return color(' Sim not inserted ', 'red')

#checa se é possivel tirar um frame com a camera para testar se ela esta funcionando
def check_camera_status():
   try:
      subprocess.run(["raspistill", "-o", "/tmp/camera_test.jpg", "-w", "640", "-h", "480"], check=True,stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
      return color(' OK ', 'green')
   except subprocess.CalledProcessError as e:
      return color(f' ERROR({e.returncode} ', 'red')

def swap_memory():
    command = "free -h | grep -iA 1 swap | tail -n 1 | awk '{printf \"%.2f%%\", ($3/$2)*100}'"
    output, error = run_bash_command(command)
    
    if error:
        return color(f' ERROR: {error} ', 'red')
    else:
        return color(f' {output} ', 'green')
    

# def Usage_cpu():
#     command = "top -b -n 1 | awk '/%Cpu/ {print 100 - $8"%"}'"
#     output, error = run_bash_command(command)
#     print(output)
#     if error:
#         return f"\033[1;31;40m Error: {error}\033[0m"
#     else:
#         return f"\033[1;32;40m {output}\033[0m"

"""
The main part of the script starts here.
It sets the log_file_path to a temporary directory and clears the log file's contents at the beginning.
The script enters an infinite loop where it repeatedly logs various system status information:
Current date and time.
Internet connection status.
Storage space on the root filesystem (expanded or not).
GPS status.
Camera status.
It writes this information to the log file and sleeps for 3 seconds before repeating the process.
"""
def main():
    log_file_path = f'/tmp/{daemon_name}.log'
    #clear_log_file(log_file_path)  # Apaga o conteúdo do arquivo de log ao iniciar
    #while True:
    with open(log_file_path, 'a') as file:
        current_time = time.strftime('\033[1;36;40m%Y-%m-%d %H:%M:%S\033[0m')
        c,d = get_machine_storage()
        #a,b=chk_gps2()
        fix, sig_str, sat_num = chk_gps3()
        status_camera=check_camera_status()
        conncetion_chk = check_internet()
        Process_modem = chk_dial_modem()
        imu = imu_check()
        read_sim= get_ccid()
        signal=modem_signal()
        status=modem_status()
        swapa = swap_memory()
        cpu = "Fazendo"
        interface_e= chk_ethernet_interface()
        interface_wlan= chk_wlan_interface()
        file.write(f'\n\033[1;34;40m---Driver_analytics Health---\033[0m\nDate:\n\t- {current_time} \n'
                    f'Analise conexao:\n\t- connection internet: {conncetion_chk}\n\t- Modem IP:{Process_modem}\n\t- Signal: {signal} \n\t- Status: {status} \n'
                    f'Analise Sd card:\n\t- Expanded:{c}\n\t- Free disk:{d} \n' 
                    f'Analise gps:\n\t- GPS Fix:{fix}\n\t- Signal Strength:{sig_str}  \n\t- Avaible Satellites: {sat_num} \n'
                    f'Analise Camera:\n\t- Camera: {status_camera}\n'
                    f'Analise IMU:\n\t- Active: {imu}\n'
                    f'Analise Sim card:\n\t- {read_sim}\n'
                    f'Analise Sistema:\n\t- Swap usage: {swapa} \n\t- CPU Usage: {cpu} \n\t- ETH0 Interface: {interface_e} \n\t- WLAN Interface: {interface_wlan}\n')
    print('\033[1;32;40m Log gerado!\033[0m') 
        #time.sleep(3)


if __name__ == '__main__':
#     #daemon = Daemonize(app=daemon_name, pid=f'/tmp/{daemon_name}.pid', action=main)
#     #daemon.start()
    main()

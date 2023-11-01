import time
import socket
#import psutil
import os
import subprocess

#from daemonize import Daemonize
daemon_name = 'chk_status'



# This function runs a shell command specified as command and returns its standard output and standard error as strings.
def run_bash_command(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    return output.decode(), error.decode()


def imu_check():
    command2 = 'i2cdetect -y 1 | grep -ia 68'
    result, error=run_bash_command(command2)
    if (result != ''):
        return 'On'
    else:
        return 'Off'
    # print(result)
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
def capture_first_line(command):
    first_line=''
    d=0
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        lines= process.stdout.readlines()
        process.terminate()  # Encerra o processo após ler a primeira linha
        if lines:
            for i in range(3):
                first_line+= lines[d].strip()
                d+=1
            return first_line
        else:
            return ''
    except Exception as e:
        return f"Erro ao executar o comando: {str(e)}"


# check_internet(): This function checks for internet connectivity by attempting to create a connection to 
# www.google.com. It returns True if the connection is successful and False otherwise.
def check_internet():
    try:
        # Tente fazer uma conexão com um servidor remoto (por exemplo, o Google)
        socket.create_connection(("www.google.com", 80))
        return True
    except OSError:
        return False

# get_machine_storage(): This function calculates and returns the total and free storage space on the root filesystem. 
# If the total storage is less than 10 GB, it attempts to expand the root filesystem and requests a reboot.
def get_machine_storage():
    command_expand = 'sudo raspi-config --expand-rootfs'
    reboot = 'sudo .driver_analytics/ask_for_reboot.sh'
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
        phrase = ' expandido'
    else:
        phrase = ' nao expandido'

    if (free_size < 0.1 * total_size):
        phrase += ' e com problema'
    else:
        phrase += ' e saudavel'
    return phrase

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
        return 'GPS ON'
    else:
        return 'GPS OFF'
    
#Cheking gps health
def chk_gps2():
    gps_device_fd = "/dev/serial0"
    gps_device = os.open(gps_device_fd, os.O_RDWR)
    gps_data = ""
    for i in range(1024):
        gps_data += os.read(gps_device, 2048)   
    if "$GNGSA,A,3" in gps_data or "$GNGSA,A,2" in gps_data:
        #print("GPS: OK");    
        #print("\033[1;32;40m GPS: OK \033[0;37;40m");
        return "\033[1;32;40m GPS: OK \033[0;37;40m"
    else:
        #print("GPS: ERROR");
        #print("\033[1;31;40m GPS: ERROR \033[0;37;40m");
        return "\033[1;31;40m GPS: ERROR \033[0;37;40m"

# chk_camera(): This function checks if a process named "camera" is running. If the process is running, 
# it returns "Camera On," otherwise "Camera OFF."
def chk_camera():
    camera_command = 'pgrep camera'
    result, error=run_bash_command(camera_command)
    if(result != ''):
        return 'Camera On'
    else:
        return 'Camera OFF'

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
    clear_log_file(log_file_path)  # Apaga o conteúdo do arquivo de log ao iniciar
    while True:
        with open(f'/tmp/{daemon_name}.log', 'a') as file:
            current_time = time.strftime('%Y-%m-%d %H:%M:%S')
            #gps_command = 'cat /dev/serial0 | grep -ia gsa'
            #linha1 = capture_first_line(gps_command)
            #partition = '/dev/root'
            #partition = '/boot/efi'
            size = get_machine_storage()
            status_gps=chk_gps()
            status_camera=chk_camera()
            if check_internet():
                conncetion_chk =  " Online"
            else:
                conncetion_chk = "Offline"
            imu = imu_check()
            file.write(f'{current_time} - Status conexao: {conncetion_chk} - Sd card: {size}  - {status_gps} - {status_camera} - IMU: {imu}\n')
            print('Gerando log...')
            imu_check()

        time.sleep(3)


if __name__ == '__main__':
#     #daemon = Daemonize(app=daemon_name, pid=f'/tmp/{daemon_name}.pid', action=main)
#     #daemon.start()
    main()

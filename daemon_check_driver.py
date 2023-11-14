import time
import socket
#import psutil
import os
import subprocess
import serial

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
        return '\033[1;32;40m ON \033[0m'
    else:
        return '\033[1;31;40m Off \033[0m'
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
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        lines= process.stdout.readlines()
        process.terminate()  # Encerra o processo após ler a primeira linha
        if lines:
            first_line= lines[0].strip()
            return first_line
        else:
            return ''
    except Exception as e:
        return f"Erro ao executar o comando: {str(e)}"
    
def read_iccid():
    command_icc='sudo timeout 2 cat /dev/ttyUSB4 & sudo stty -F /dev/ttyUSB4 raw -echo & sudo echo -e "AT+CCID\r" > /dev/ttyUSB4'
    result, error=run_bash_command(command_icc)
    print(error)
    if 'OK' in result:
        return '\033[1;32;40mSim inserted\033[0m'
    else:
        return '\033[1;31;40mSim not inserted\033[0m'


# check_internet(): This function checks for internet connectivity by attempting to create a connection to 
# www.google.com. It returns True if the connection is successful and False otherwise.
def check_internet():
    try:
        # Tente fazer uma conexão com um servidor remoto (por exemplo, o Google)
        socket.create_connection(("www.google.com", 80))
        return '\033[1;32;40m Ok \033[0m'
    except OSError:
        return '\033[1;31;40m NOK \033[0m'

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
        phrase = '\033[1;32;40mOK\033[0m'
    else:
        phrase = '\033[1;31;40mNOK\033[0m'

    if (free_size < 0.05 * total_size):
        phrase2 = '\033[1;31;40m NOK \033[0m'
    else:
        phrase2 = '\033[1;32;40m OK\033[0m'
    return phrase, phrase2

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
        return 'GPS\033[1;32;40m ON \033[0m'
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
        danger="\033[1;32;40mOK\033[0m"
        phrase= "\033[1;32;40mINFO SATELLITE\033[0m"
    elif "$GPRMC" in gps_data or "$GNRMC" in gps_data:
        danger ="\033[1;33;40mOK\033[0m"
        phrase= "\033[1;33;40mNOINFO SATELLITE\033[0m"
    else:    
        danger="\033[1;31;40mNOK\033[0m"
        phrase= "\033[1;31;40mERROR\033[0m"
    return danger, phrase 
            
    
def chk_dial_modem():
    modem_command = 'ip addr | grep -ia ppp0'
    result, error=run_bash_command(modem_command)
    if(result != ''):
        return '\033[1;32;40m ON \033[0m'
    else:
        return '\033[1;31;40m OFF \033[0m'


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
            return "\033[1;32;40m Strong signal \033[0m"
        elif(signal_strength<=20 & signal_strength>15):
            return "\033[1;33;40m Mediun signal \033[0m"
        else:
            return "\033[1;31;40m Low signal \033[0m"
    else:
        return 0

def modem_status():
    text_status =b'AT+CPAS\r'
    result = send_serial_command(text_status)
    result2 = result.split(":")[1].strip()
    if "ok" in result2.lower():
        return "\033[1;32;40mOK\033[0m"
    elif "error" in result2.lower():
        "\033[1;31;40mERROR\033[0m"
    else:
        "Undefined"
    
    #jeito alternativo
    # command_status='sudo timeout 2 cat /dev/ttyUSB4 & sudo stty -F /dev/ttyUSB4 raw -echo & sudo echo -e "AT+CPAS\r" > /dev/ttyUSB4'
    # result,error = run_bash_command(command_status)
    # if 'ERROR' in result:
    #     return '\033[1;31;40m Error\033[0m'
    # else:
    #     return '\033[1;32;40m Ok \033[0m'

#checa se é possivel tirar um frame com a camera para testar se ela esta funcionando
def check_camera_status():
   try:
      subprocess.run(["raspistill", "-o", "/tmp/camera_test.jpg", "-w", "640", "-h", "480"], check=True,stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
      return"\033[1;32;40m OK\033[0m"
   except subprocess.CalledProcessError as e:
      return f"\033[1;31;40m ERROR({e.returncode})\033[0m"

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
        a,b=chk_gps2()
        status_camera=check_camera_status()
        conncetion_chk = check_internet()
        Process_modem = chk_dial_modem()
        imu = imu_check()
        read_sim= read_iccid()
        signal=modem_signal()
        status=modem_status()
        file.write(f'\n\033[1;34;40m---Driver_analytics Health---\033[0m\nDate:\n\t- {current_time} \n'
                    f'Analise conexao:\n\t- connection internet: {conncetion_chk}\n\t- Modem IP:{Process_modem}\n\t- Signal: {signal} \n\t- Status: {status} \n'
                    f'Analise Sd card:\n\t- Expanded:{c}\n\t- Free disk:{d} \n' 
                    f'Analise gps:\n\t- Health gps:{a} \n\t- Descriptiom: {b} \n'
                    f'Analise Camera:\n\t- Camera: {status_camera}\n'
                    f'Analise IMU:\n\t- Active: {imu}\n'
                    f'Analise Sim card:\n\t- {read_sim}\n')
    print('\033[1;32;40m Log gerado!\033[0m') 
    
        #time.sleep(3)


if __name__ == '__main__':
#     #daemon = Daemonize(app=daemon_name, pid=f'/tmp/{daemon_name}.pid', action=main)
#     #daemon.start()
    main()

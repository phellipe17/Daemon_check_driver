import time
import socket
import os
import subprocess
import serial
import json, requests
import sqlite3
import threading
from threading import Thread

# Caminho do diretório
directory_path = '/home/pi/.driver_analytics/logs/current/'
db_lock = threading.Lock()
r = requests.session()
DEBUG = True

#from daemonize import Daemonize
daemon_name = 'chk_status'

def color(msg, collor):
    coloring=False #False para não imprimir com cor, True para sair com cor
    
    if coloring==False:
        return msg
    else:
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
        return color(' 1 ','green')
    else:
        return color(' 1 ','red')

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
        return color(' 1 ','green')
    except OSError:
        return color(' 0 ','red')


def check_ip_connectivity(ip_address):
    try:
        # Tente fazer uma conexão com o IP fornecido na porta 80 (HTTP)
        socket.create_connection((ip_address, 80))
        return color(' 1 ','green') # Supondo que 'color()' é uma função que formata a saída com cores
    except OSError:
        return color(' 0 ','red')
 
# get_machine_storage(): This function calculates and returns the total and free storage space on the root filesystem. 
# If the total storage is less than 10 GB, it attempts to expand the root filesystem and requests a reboot.
def get_machine_storage():
    total_size_status = ''
    free_size_status = ''
    result=os.statvfs('/')
    block_size=result.f_frsize
    total_blocks=result.f_blocks
    free_blocks=result.f_bfree
    giga=1024*1024*1024
    # giga=1000*1000*1000
    total_size=total_blocks*block_size/giga
    free_size=free_blocks*block_size/giga
    total_size = round(total_size)
    free_size = round(free_size)
    if (total_size > 10):
        total_size_status = color(' 1 ','green')
    else:
        total_size_status = color(' 0 ','red')

    if (free_size < 0.05 * total_size):
        free_size_status = color(' 0 ','red')
    else:
        free_size_status = color(' 1 ','green')
    return total_size_status, free_size_status,total_size

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
        return color(' 1 ','green')
    else:
        return color(' 0 ','red')

def chk_wlan_interface():
    wlan_command = 'ip addr show wlan0'
    result, error = run_bash_command(wlan_command)
    if 'UP' in result:
        return color(' 1 ','green')
    else:
        return color(' 0 ','red')

def chk_ethernet_interface():
    eth_command = 'ip addr show eth0'
    result, error = run_bash_command(eth_command)
    if 'UP' in result:
        return color(' 1 ','green')
    else:
        return color(' 0 ','red')

def chk_ttyLTE():
    command = 'ls /dev/'
    result,error = run_bash_command(command)
    if 'ttyLTE' in result:
        return color('1','green')
    else:
        return color('0','red')

def chk_ttyARD():
    command = 'ls /dev/'
    result,error = run_bash_command(command)
    if 'ttyARD' in result:
        return color('1','green')
    else:
        return color('0','red')


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
            return color(' 0 ','magenta')
        elif(signal_strength>=31):
            return color(' 1 ','green')
        elif(signal_strength<31 and signal_strength>=2):
            return color(' 1 ','yellow')
        elif(signal_strength<2 and  signal_strength>=0):
            return color(' 0 ','red')
    else:
        return 0

def modem_status():
    text_status =b'AT+CPAS\r'
    result = send_serial_command(text_status)
    result2 = result.split(":")[1].strip()
    if "ok" in result2.lower():
        return color(' 1 ','green')
    elif "error" in result2.lower():
        return color(' 0 ','red')
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
    command_frame="tail -n10 /home/pi/.driver_analytics/logs/current/camera.log"
    result, error=run_bash_command(command_frame)
    available=color(" 1 ","green")
    if "Error opening the camera" in result:
        available = color(" 0 ", "red")
    else:
        last_log_line=run_bash_command('tail -n2 /home/pi/.driver_analytics/logs/current/camera.log')
        data_hora_ultima_msg_str = str(last_log_line).split(']')[0].strip('[')[-19:]
        timestamp_ultima_msg = time.mktime(time.strptime(data_hora_ultima_msg_str, '%d/%m/%Y %H:%M:%S'))
        # Calcular a diferença de tempo
        diferenca_tempo = time.time() - timestamp_ultima_msg
        if(diferenca_tempo>60):
            available=color(" 0 ","red")
        #print("Diferença de tempo:", round(diferenca_tempo), "segundos")

    command = "vcgencmd get_camera"
    output, error = run_bash_command(command)
    detected = color(" 1 ", "green") if "detected=1" in output else color(" 0 ", "red")
    
        
    return detected, available



def check_camera_status2():
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
    command = "free -h | grep -iA 1 swap | tail -n 1 | awk '{printf \"%.2f\", ($3/$2)*100}'"
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
        elif idle_time >= 20:
            return color(f" {usage}% ", "magenta")
        elif idle_time < 20:
            return color(f" {usage}% ", "red")
        
def temp_system():
    command = "cat /sys/class/thermal/thermal_zone0/temp"
    output, error = run_bash_command(command)
    tempe=round(int(output)/1000)
    if error:
        return color(f" Error: {error} ", "red")
    else:
        if tempe >= 80:
            return color(f"{tempe}°", "red")
        elif tempe >= 60 & tempe <80:
            return color(f"{tempe}°", "yellow")
        elif tempe<60:
            return color(f"{tempe}°", "green")

def get_mac():
    command = "ifconfig eth0 | grep -oE '([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}'"
    output,error= run_bash_command(command)
    return output

def log(s, value=None):
    if DEBUG:
        if (value==None):
            print(s)
        else:
            print(s, value)


#função para fazer login na api driveranalytics
def login(urlbase, url, user, password):
    global r
    params =    {
                    'username': user,
                    'password': password
                }

    urlApi = urlbase + url
    log(urlApi)
    log(user)
    log(password)

    try:
        r.headers.clear()
        r.cookies.clear()
        r = requests.post(urlApi, params=params, timeout=6.0)
    except (requests.exceptions.ConnectTimeout, requests.exceptions.HTTPError, requests.exceptions.ReadTimeout, requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        log("Connection error - try again")
        log(e)
        return 502, {}
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        log(e)
        log("error on login")
        return 500, {}

    ret_status_code = r.status_code
    log("[login] ret code", ret_status_code)

    response_json = {}

    if ret_status_code == 201:
        log("[login] Success! ")
        response_json = r.json()
        global company
        company = response_json['user']['company']['id']
        response_json = response_json['token']
    else:
        log("[login] Error")

    return ret_status_code, response_json

#função para fazer o post na api driveranalytics        
def postChekingHealth(urlbase, url, idVehicle, token):
    global r

    urlApi = urlbase + url + idVehicle + "/getConfigIni"

    log(urlApi)

    try:
        r.headers.clear()
        r.cookies.clear()
        # Enviar uma solicitação POST com os parâmetros necessários
        r = requests.post(urlApi, headers={"Authorization":"Bearer " + token, 'Cache-Control': 'no-cache' })
    except requests.exceptions.RequestException as e:  
        log(e)
        log("error on postVehicle")
        return 500, {}

    ret_status_code = r.status_code
    log("[postVehicle] ret code", ret_status_code)

    response_json = {}

    if ret_status_code == 200:
        log("[postVehicle] Success! ")
        response_json = r.json()  # Convertendo a resposta para JSON
    else:
        log("[postVehicle] Error")

    return ret_status_code, response_json

def ler_contador():
    with open("/home/pi/.monitor/counter.txt", "r") as arquivo:
        return int(arquivo.read().strip())

def escrever_contador(contador):
    with open("/home/pi/.monitor/counter.txt", "w") as arquivo:
        arquivo.write(str(contador))
    
def incrementar_contador_e_usar():
    contador = ler_contador()
    contador += 1
    # print("Contador atual:", contador)
    escrever_contador(contador)

def inicializar_contador():
    if not os.path.exists("/home/pi/.monitor/counter.txt"):
        with open("/home/pi/.monitor/counter.txt", "w") as arquivo:
            arquivo.write("0")
            return 0
    else:
        return ler_contador()

def checking_ignition():
    command="cat /dev/shm/IGNITION_IS_ON"
    output, error = run_bash_command(command)
    out=int(output)
    return out

def checking_mode():
    command="cat /home/pi/.driver_analytics/mode | grep -ia always | tail -c 2"
    output, error = run_bash_command(command)
    # print(output)
    # print(error)
    if output == "":
        out=0
    else:
        out=int(output)
    # print(out)
    return out

def current_time_pi():
    command="date +'%Y/%m/%d %H:%M:%S'"
    output,error = run_bash_command(command)
    return output

def verificar_e_criar_tabela():
    conn = sqlite3.connect('/home/pi/.driver_analytics/database/check_health.db')
    cursor=conn.cursor() 
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS health_device (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Data TEXT NOT NULL,
            ignition TEXT NOT NULL,
            mode_aways_on TEXT NOT NULL,
            connection_internet TEXT NOT NULL,
            Modem_IP TEXT NOT NULL,
            Signal_modem TEXT NOT NULL,
            Status_modem TEXT NOT NULL,
            connection_extra TEXT NOT NULL,
            connection_int TEXT NOT NULL,
            Expanded TEXT NOT NULL,
            Free_disk TEXT NOT NULL,
            Size_disk TEXT NOT NULL,
            GPS_Fix TEXT NOT NULL,
            Signal_Strength TEXT NOT NULL,
            Avaible_Satellites TEXT NOT NULL,
            Detected_camera TEXT NOT NULL,
            Available_camera TEXT NOT NULL,
            Active TEXT NOT NULL,
            Swap_usage TEXT NOT NULL,
            CPU_Usage TEXT NOT NULL,
            ETH0_Interface TEXT NOT NULL,
            WLAN_Interface TEXT NOT NULL,
            USB_LTE TEXT NOT NULL,
            USB_ARD TEXT NOT NULL,
            Temperature TEXT NOT NULL,
            Mac_Address TEXT NOT NULL
        )
    ''')
    conn.close()
    

def adicionar_dados(data):
    with db_lock:
        conn = sqlite3.connect('/home/pi/.driver_analytics/database/check_health.db')
        cursor=conn.cursor() 
        cursor.execute(f''' INSERT INTO health_device (Data, ignition, mode_aways_on, connection_internet, Modem_IP, Signal_modem, Status_modem, connection_extra, 
        connection_int, Expanded, Free_disk, Size_disk, GPS_Fix, Signal_Strength, Avaible_Satellites, Detected_camera, 
        Available_camera, Active, Swap_usage, CPU_Usage, ETH0_Interface, WLAN_Interface, USB_LTE, USB_ARD, Temperature, 
        Mac_Address) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ''', data)
        conn.commit()
        conn.close()

def ler_dados():    
        conn = sqlite3.connect('/home/pi/.driver_analytics/database/check_health.db')
        print("entrou no conn de ler dados")
        cursor=conn.cursor() 
        dados = cursor.execute("SELECT * FROM health_device").fetchall()
        conn.close()
        return dados

def enviar_para_api(url):
    response=''
    with db_lock:
        dados=ler_dados()
        if len(dados) != 0: 
            rows=transformar_em_json(dados)
            headers = {'Content-Type': 'application/json'}
            for linha in rows:
                json_data = json.dumps(linha)
                response = requests.post(url, data=json_data, headers=headers)
            print(response)
            if 200 == response.status_code:
                conn = sqlite3.connect('/home/pi/.driver_analytics/database/check_health.db')
                print("entrou no conn de deletar")
                cursor=conn.cursor() 
                cursor.execute("DELETE FROM health_device")
                conn.close()
    

def transformar_em_json(dados):
    resultado = []
    for linha in dados:
        json_linha = {
            "id": linha[0],
            "data": linha[1],
            "ignition": linha[2],
            "mode_aways_on": linha[3],
            "connection_internet": linha[4],
            "Modem_IP": linha[5],
            "Signal_modem": linha[6],
            "Status_modem": linha[7],
            "connection_extra": linha[8],
            "connection_int": linha[9],
            "Expanded": linha[10],
            "Free_disk": linha[11],
            "Size_disk": linha[12],
            "GPS_Fix": linha[13],
            "Signal_Strength": linha[14],
            "Avaible_Satellites": linha[15],
            "Detected_camera": linha[16],
            "Available_camera": linha[17],
            "Active": linha[18],
            "Swap_usage": linha[19],
            "CPU_Usage": linha[20],
            "ETH0_Interface": linha[21],
            "WLAN_Interface": linha[22],
            "USB_LTE": linha[23],
            "USB_ARD": linha[24],
            "Temperature": linha[25],
            "Mac_Address": linha[26]
        }
        resultado.append(json_linha)
    return resultado

def main():
    verificar_e_criar_tabela()
    url="https://e7e3-131-255-20-145.ngrok-free.app/heartbeat"
    api_thread = threading.Thread(target=enviar_para_api, args=(url,))
    api_thread.start()
    counter_ind=inicializar_contador()
    ip_extra="10.0.89.11"
    ip_interna="10.0.90.196"
    ig = checking_ignition()
    #clear_log_file(log_file_path)  # Apaga o conteúdo do arquivo de log ao iniciar
    current_time = current_time_pi()
    if(ig):
        connect_int = check_ip_connectivity(ip_interna)
    else:
        connect_int=0
    modee=checking_mode()
    total_size,free_size,size = get_machine_storage()
    fix, sig_str, sat_num = chk_gps3()
    detected,available = check_camera_status()
    conncetion_chk = check_internet()
    connect_ip= check_ip_connectivity(ip_extra)
    Process_modem = chk_dial_modem()
    imu = imu_check()
    signal = modem_signal()
    status = modem_status()
    swapa = swap_memory()
    cpu = usage_cpu()
    interface_e = chk_ethernet_interface()
    interface_wlan = chk_wlan_interface()
    Lte = chk_ttyLTE()
    Ard = chk_ttyARD()
    temperature= temp_system()
    macmac=get_mac()
    # with open(log_file_path, 'a') as file:
    #     # file.write(f'\n\033[1;34;40m---Driver_analytics Health---\033[0m\nDate:\n\t- {current_time} \n'
    #     file.write(f'\n---Driver_analytics Health---\nDate:\n\t- {current_time} \n'
    #                 f'Connection Analysis:\n\t- connection internet: {conncetion_chk}\n\t- Modem IP:{Process_modem}\n\t- Signal: {signal} \n\t- Status: {status} \n\t conection extra: {connect_ip} \n'
    #                 f'SD Card Analysis:\n\t- Expanded:{total_size}\n\t- Free disk:{free_size} \n'
    #                 f'GPS Analysis:\n\t- GPS Fix: {fix}\n\t- Signal Strength: {sig_str}  \n\t- Avaible Satellites: {sat_num} \n'
    #                 f'Camera Analysis:\n\t- Detected: {detected}\n\t- Available: {available}\n'
    #                 f'IMU Analysis:\n\t- Active: {imu}\n'
    #                 f'System Analysis:\n\t- Swap usage: {swapa} \n\t- CPU Usage: {cpu} \n\t- ETH0 Interface: {interface_e} \n\t- WLAN Interface: {interface_wlan}\n\t'
    #                 f'- USB LTE: {Lte} \n\t- USB ARD: {Ard}\n\t- Temperature: {temperature}\n\t- Mac Adress: {macmac}\n')
    
    
    
    data_values =(
        current_time.strip('\n'),
        ig, 
        modee,
        conncetion_chk,
        Process_modem, 
        signal,
        status,
        connect_ip,
        connect_int,
        total_size,
        free_size,
        size,
        fix, 
        sig_str,
        sat_num,
        detected,
        available,
        imu,
        swapa, 
        cpu, 
        interface_e,
        interface_wlan,
        Lte,
        Ard, 
        temperature,
        macmac.strip()
    )
    
    adicionar_dados(data_values)
        
    # json_data= json.dumps(data)
    # headers = {'Content-Type': 'application/json'}
    # url="https://523a-164-163-204-193.ngrok-free.app/heartbeat"
    # response = requests.post(url, data=json_data, headers=headers)
    # print(response)
               


if __name__ == '__main__':
#     #daemon = Daemonize(app=daemon_name, pid=f'/tmp/{daemon_name}.pid', action=main)
#     #daemon.start()
    main()

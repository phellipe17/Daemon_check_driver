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
ip_extra="10.0.89.11"
ip_interna="10.0.90.196"
ip_externa="10.0.90.195"



#from daemonize import Daemonize
daemon_name = 'chk_status'

# def color(msg, collor):
#     coloring=False #False para não imprimir com cor, True para sair com cor
    
#     if coloring==False:
#         return msg
#     else:
#         if collor == "green":
#             return f'\033[1;32;40m{msg}\033[0m'
#         elif collor == "red":
#             return f'\033[1;31;40m{msg}\033[0m'
#         elif collor == "yellow":
#             return f'\033[1;33;40m{msg}\033[0m'
#         elif collor == "magenta":
#             return f'\033[1;35;40m{msg}\033[0m'

# This function runs a shell command specified as command and returns its standard output and standard error as strings.
def run_bash_command(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    return output.decode(), error.decode()


def imu_check():
    command2 = 'cat /home/pi/.driver_analytics/logs/current/imu.log'
    result, error=run_bash_command(command2)
    if '' in result:
        return color(' 1 ','green')
    else:
        return color(' 0 ','red')

def check_internet():
    try:
        # Tente fazer uma conexão com um servidor remoto (por exemplo, o Google)
        socket.create_connection(("www.google.com", 80))
        # with socket.create_connection((ip_address, 80)) as connection:
        #     return ' 1 '
        return ' 1 '
    except OSError:
        return ' 0 '


def check_ip_connectivity(ip_address):
    try:
        # Tente fazer uma conexão com o IP fornecido na porta 80 (HTTP)
        socket.create_connection((ip_address, 80))
        # with socket.create_connection((ip_address, 80)) as connection:
        #     return ' 1 '
        return ' 1 '
    except OSError:
        return ' 0 '
 
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
    total_size=total_blocks*block_size/giga
    free_size=free_blocks*block_size/giga
    total_size = round(total_size)
    free_size = round(free_size)
    
    total_size_status = ' 1 ' if total_size > 10 else ' 0 '
    free_size_status = ' 1 ' if free_size < 0.05 * total_size else ' 0 '

    return total_size_status, free_size_status,total_size

# clear_log_file(log_file_path): This function clears the contents of a log file specified by log_file_path.
def clear_log_file(log_file_path):
    with open(log_file_path, 'w') as file:
        file.write("") 


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

    if avg_fix > 2 and validity_status == 'A':
        fix = "3D"
    elif avg_fix <= 2 and validity_status == 'A':
        fix = "2D"
    else:
        fix = "No Fix"

    sig_str = f"{round(avg_snr, 2)}" if snr_values else ' 0 '

    sat_num = f"{round(avg_num_satellites)}" if num_satellites is not None else ' 0 '
    
    return fix, sig_str, sat_num
    
def chk_dial_modem():
    modem_command = 'ip addr | grep -ia ppp0'
    result, error=run_bash_command(modem_command)
    return ' 1 ' if(result != '') else ' 0 '

def chk_wlan_interface():
    wlan_command = 'ip addr show wlan0'
    result, error = run_bash_command(wlan_command)
    return ' 1 ' if 'UP' in result else ' 0 '

def chk_ethernet_interface():
    eth_command = 'ip addr show eth0'
    result, error = run_bash_command(eth_command)
    return ' 1 ' if 'UP' in result else ' 0 '
    
def chk_ttyLTE():
    command = 'ls /dev/'
    result,error = run_bash_command(command)
    return ' 1 ' if 'ttyLTE' in result else ' 0 '

def chk_ttyARD():
    command = 'ls /dev/'
    result,error = run_bash_command(command)
    return ' 1 ' if 'ttyARD' in result else ' 0 '

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
    result = send_serial_command(text_signal)
    result2 = result.split("\n")[1].split(":")[1].strip()	    
    if len(result2) > 0:
        signal_strength=float(result2.replace(',','.'))
        if (signal_strength == 99):
            return ' 0 '
        elif (signal_strength >= 31):
            return ' 1 '
        elif (signal_strength < 31 and signal_strength >= 2):
            return ' 1 '
        elif (signal_strength < 2 and  signal_strength >= 0):
            return ' 0 '
    else:
        return ' 0 '

def modem_status():
    text_status =b'AT+CPAS\r'
    result = send_serial_command(text_status)
    result2 = result.split(":")[1].strip()
    if "ok" in result2.lower():
        return ' 1 '
    elif "error" in result2.lower():
        return ' 0 '
    else:
        return "Undefined"
    
# def get_ccid():
#     command = b'AT+QCCID\r'
#     result = send_serial_command(command)
#     ccid = result.split("\n")[1].split(" ")[1]
#     if 'OK' in result and ccid:
#         return color(f' Sim inserted - CCID: {ccid}', 'green')
#     else:
#         return color(' Sim not inserted', 'red')

def check_camera_status():
    command_frame="tail -n10 /home/pi/.driver_analytics/logs/current/camera.log"
    result, error=run_bash_command(command_frame)
    available = ' 1 '
    if "Error opening the camera" in result:
        available = ' 0 '
    else:
        last_log_line=run_bash_command('tail -n2 /home/pi/.driver_analytics/logs/current/camera.log')
        data_hora_ultima_msg_str = str(last_log_line).split(']')[0].strip('[')[-19:]
        timestamp_ultima_msg = time.mktime(time.strptime(data_hora_ultima_msg_str, '%d/%m/%Y %H:%M:%S'))
        # Calcular a diferença de tempo
        diferenca_tempo = time.time() - timestamp_ultima_msg
        if(diferenca_tempo > 60):
            available = ' 0 '

    command = "vcgencmd get_camera"
    output, error = run_bash_command(command)
    detected = ' 1 ' if "detected=1" in output else ' 0 '
    
        
    return detected, available

# def check_camera_status2():
#     try:
#        subprocess.run(["raspistill", "-o", "/tmp/camera_test.jpg", "-w", "640", "-h", "480"], check=True,stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
#        available = color(" YES ", "green")
#     except subprocess.CalledProcessError as e:
#        available = color(f" NO - error no:({e.returncode})", "red")
    
#     command = "vcgencmd get_camera"
#     output, error = run_bash_command(command)
#     detected = color(" YES ", "green") if "detected=1" in output else color(" NO ", "red")
#     connected = color(" YES ", "green") if "supported=1" in output else color(" NO ", "red")
        
#     return detected, connected, available  

def swap_memory():
    command = "free -h | grep -iA 1 swap | tail -n 1 | awk '{printf \"%.2f\", ($3/$2)*100}'"
    output, error = run_bash_command(command)
    
    if error:
        return color(f" Error: {error} ", "red")
    else:
        return color(f" {output}", "green")
    

def usage_cpu():
    command = "top -bn1 | grep '^%Cpu(s)' | awk '{print $8}'"                                                     
    output, error = run_bash_command(command)
    idle_time = float(output.strip().replace(',', '.'))
    usage = 100 - idle_time
    
    return f" {usage}% " if not error else f"Error: {error}"
            
def temp_system():
    command = "cat /sys/class/thermal/thermal_zone0/temp"
    output, error = run_bash_command(command)
    tempe=round(int(output)/1000)
    
    return f"{tempe}°" if not error else f"Error: {error}"

def get_mac():
    command = "ifconfig eth0 | grep -oE '([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}'"
    output,error= run_bash_command(command)
    
    return output if not error else f"Error: {error}"

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
    escrever_contador(contador)

def inicializar_contador():
    if not os.path.exists("/home/pi/.monitor/counter.txt"):
        with open("/home/pi/.monitor/counter.txt", "w") as arquivo:
            arquivo.write("0")
            return ' 0 '
    else:
        return ler_contador()

def checking_ignition():
    command="cat /dev/shm/IGNITION_IS_ON"
    output, error = run_bash_command(command)
    out=int(output)
    return out

# def checking_mode():
#     command="cat /home/pi/.driver_analytics/mode | grep -ia always | tail -c 2"
#     output, error = run_bash_command(command)
#     if output == "":
#         out=0
#     else:
#         out=int(output)
#     return out

def current_time_pi():
    command="date +'%Y/%m/%d %H:%M:%S'"
    output,error = run_bash_command(command)

    return output

def verificar_e_criar_tabela():
    conn = sqlite3.connect('/home/pi/.driver_analytics/database/check_health.db')
    cursor=conn.cursor() 
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS health_device (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            Data TEXT,
            ignition TEXT,
            mode_aways_on TEXT,
            connection_internet TEXT,
            Modem_IP TEXT,
            Signal_modem TEXT,
            Status_modem TEXT,
            connection_extra TEXT,
            connection_INT_EXT TEXT,
            Expanded TEXT,
            Free_disk TEXT,
            Size_disk TEXT,
            GPS_Fix TEXT,
            Signal_Strength TEXT,
            Avaible_Satellites TEXT,
            Detected_camera TEXT,
            Available_camera TEXT,
            Active_imu TEXT,
            Swap_usage TEXT,
            CPU_Usage TEXT,
            ETH0_Interface TEXT,
            WLAN_Interface TEXT,
            USB_LTE TEXT,
            USB_ARD TEXT,
            Temperature TEXT,
            Mac_Address TEXT
        )''')
    conn.close()
    

def adicionar_dados(data):
    with db_lock:
        conn = sqlite3.connect('/home/pi/.driver_analytics/database/check_health.db')
        cursor=conn.cursor() 
        cursor.execute(f''' INSERT INTO health_device (Data, ignition, mode_aways_on, connection_internet, Modem_IP, Signal_modem, Status_modem, connection_extra, 
        connection_INT_EXT, Expanded, Free_disk, Size_disk, GPS_Fix, Signal_Strength, Avaible_Satellites, Detected_camera, 
        Available_camera, Active_imu, Swap_usage, CPU_Usage, ETH0_Interface, WLAN_Interface, USB_LTE, USB_ARD, Temperature, 
        Mac_Address) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ''', data)
        conn.commit()
        conn.close()

def ler_dados():    
        conn = sqlite3.connect('/home/pi/.driver_analytics/database/check_health.db')
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
            for i in range(0, len(rows), 1000):  # Posta de 1000 em 1000 linhas
                batch = rows[i:i+1000]
                for linha in batch:
                    json_data = json.dumps(linha)
                    response = requests.post(url, data=json_data, headers=headers)
                print(response)
                if 200 == response.status_code:
                    conn = sqlite3.connect('/home/pi/.driver_analytics/database/check_health.db')
                    cursor=conn.cursor() 
                    cursor.execute("DELETE FROM health_device WHERE id <= ?", (batch[-1]['id'],))
                    conn.commit()
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
            "connection_int_ext": linha[9],
            "Expanded": linha[10],
            "Free_disk": linha[11],
            "Size_disk": linha[12],
            "GPS_Fix": linha[13],
            "Signal_Strength": linha[14],
            "Avaible_Satellites": linha[15],
            "Detected_camera": linha[16],
            "Available_camera": linha[17],
            "Active_imu": linha[18],
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

def load_config(filename):
    config = {}
    with open(filename) as f:
        for line in f:
            key, value = line.strip().split("=")
            config[key] = value
    return config

def main():
    filename="/home/pi/.driver_analytics/mode"
    config=load_config(filename) 
    
    # Guardando os valores das variavel mode em config
    AS1_BRIDGE_MODE = int(config.get("BRIDGE_MODE", ""))
    AS1_CAMERA_TYPE = int(config.get("CAMERA_TYPE", ""))
    AS1_NUMBER_OF_SLAVE_DEVICES = int(config.get("NUMBER_OF_SLAVE_DEVICES", ""))
    AS1_ALWAYS_ON_MODE = config.get("ALWAYS_ON_MODE", "") if config.get("ALWAYS_ON_MODE", "") != "" else 0
    
    verificar_e_criar_tabela() # Verifica se não existe banco e tabela e cria os mesmos
    url="https://6207-131-255-21-130.ngrok-free.app/heartbeat"
    api_thread = threading.Thread(target=enviar_para_api, args=(url,))
    api_thread.start() # Inicia a thread de postar na api
    ig = checking_ignition() # checa ignição
    current_time = current_time_pi() # busca data em que foi rodado o script
    total_size,free_size,size = get_machine_storage() #busca informações de armazenamento
    detected,available = check_camera_status() # detecta e verifica o camera
    conncetion_chk = check_internet() # verifica se tem conexão com a internet
    swapa = swap_memory() # Verifica se esta tendo swap de memoria
    cpu = usage_cpu() # % Verifica uso da cpu
    interface_e = chk_ethernet_interface() # Verifica se existe porta ethernet
    interface_wlan = chk_wlan_interface() # Verifica se o wifi esta funcional
    temperature= temp_system() # Verifica temperatura do sistema
    macmac=get_mac() # Verifica o mac adress
    
    # Verifica conexão com interna ou externa
    if AS1_CAMERA_TYPE == 0:
        connect_int_ext = check_ip_connectivity(ip_interna)
    elif AS1_CAMERA_TYPE ==1:
        connect_int_ext = check_ip_connectivity(ip_externa)
    else:
        connect_int_ext=None
    
    # Verifica modo ALWAYS ON
    modee=AS1_ALWAYS_ON_MODE if AS1_ALWAYS_ON_MODE != '' else 0
    
    # Verifica GPS
    if(AS1_CAMERA_TYPE==0):
        fix, sig_str, sat_num = chk_gps3()
    
    # Verifica Camera extra
    if AS1_NUMBER_OF_SLAVE_DEVICES >=2:
        connect_extra= check_ip_connectivity(ip_extra)
    else:
        connect_extra= None
    print(connect_extra)
    
    #Verifica processos do modem
    if AS1_BRIDGE_MODE == 0 or AS1_BRIDGE_MODE ==1: # 0 master com slave / 1 master sem slave / 2 e slave
        Process_modem = chk_dial_modem()
        imu = imu_check()
        signal = modem_signal()
        status = modem_status()
        Lte = chk_ttyLTE()
    else:
       Process_modem = None
       imu = None
       signal = None
       status = None
       Lte = None
    
    # Verifica Display
    if AS1_CAMERA_TYPE == 0:
        Ard = chk_ttyARD()
    else:
        Ard = None
    
    
    data_values=(
        current_time.strip('\n'),
        ig, 
        modee,
        conncetion_chk,
        Process_modem, 
        signal,
        status,
        connect_extra,
        connect_int_ext,
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
               


if __name__ == '__main__':
    main()

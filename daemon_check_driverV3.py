import time
import socket
import os
import subprocess
import serial
import json, requests
import sqlite3
from sqlite3 import Error
import threading
from threading import Thread
import psutil
import csv
import smtplib
from datetime import datetime, timedelta

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Caminho do diretório
flag = 1 # 0 create database and sent to api, 1 to create a csv file
directory_path = '/home/pi/.driver_analytics/logs/current/'
db_lock = threading.Lock()
r = requests.session()
DEBUG = True
ip_extra="10.0.89.11"
ip_interna="10.0.90.196"
ip_externa="10.0.90.195"
retry_time_in_seconds = int(60)
token = ""
pathe="/home/pi/.driver_analytics/database/check_health_e.db"
pathi="/home/pi/.driver_analytics/database/check_health_i.db"
pathdriver="/home/pi/.driver_analytics/database/driveranalytics.db"


def run_bash_command(command, timeout=10):
    try:
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate(timeout=timeout)
        return output.decode(), error.decode()
    except subprocess.TimeoutExpired:
        process.kill()
        return "", "Command timed out"



def imu_check():
    command2 = 'cat /home/pi/.driver_analytics/logs/current/imu.log'
    result, error=run_bash_command(command2)
    if 'MPU-9250 init complete' in result:
        return ' 1 '
    else:
        return ' 0 '

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

def open_serial_connection(port, baudrate):
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"Port {port} opened successfully")
        return ser
    except serial.SerialException as e:
        print(f"Error opening port {port}: {e}")
        return None

def close_serial_connection(ser):
    if ser.is_open:
        ser.close()
        print(f"Port {ser.port} closed successfully")

def set_gps_baudrate(ser, baudrate=115200):
    try:
        ser.write(f"$PMTK251,{baudrate}*1F\r\n".encode())
        time.sleep(1)  # Aguarde para que o comando seja processado
        ser.baudrate = baudrate
        print(f"Set GPS baudrate to: {baudrate} kbps")
    except serial.SerialException as e:
        print(f"Error setting GPS baudrate: {e}")

def set_gnss_mode(ser):
    try:
        ser.write(b"$PMTK353,1,1,1,1,0*2B\r\n")  # Comando para definir o modo GNSS
        time.sleep(1)  # Aguarde para que o comando seja processado
        print("Set GNSS mode")
    except serial.SerialException as e:
        print(f"Error setting GNSS mode: {e}")

def read_gps_data(ser, duration=2):
    start_time = time.time()
    gps_data = []
    
    while (time.time() - start_time) < duration:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                print(f"Received line: {line}")
                gps_data.append(line)
        except serial.SerialException as e:
            print(f"Error reading from serial port: {e}")
            break
    return gps_data

def parse_gps_data(gps_data):
    num_satellites = 0
    signal_quality = 0
    fix_status = "No Fix"  # Default status

    for line in gps_data:
        if line.startswith('Received line:'):
            line = line.split('Received line:')[1].strip()

        if line.startswith('$GPGSV'):
            parts = line.split(',')
            try:
                num_satellites = int(parts[3])
                for i in range(7, len(parts), 4):
                    if i < len(parts) and parts[i].isdigit():
                        signal_quality = max(signal_quality, int(parts[i]))
            except (ValueError, IndexError):
                continue
        elif line.startswith('$GPGGA'):
            parts = line.split(',')
            try:
                num_satellites = int(parts[7])
            except (ValueError, IndexError):
                continue
        elif line.startswith('$GPRMC'):
            parts = line.split(',')
            try:
                # Check fix status
                if parts[2] == 'A':
                    fix_status = "A"  # A for Active, V for Void
            except (ValueError, IndexError):
                continue
        elif line.startswith('$GNGSA'):
            parts = line.split(',')
            try:
                # Check fix type
                if parts[1] == 'A':  # A for Auto
                    fix_type = parts[2]
                    if fix_type == '1':
                        fix_status = "No fix"
                    elif fix_type == '2':
                        fix_status = "2D"
                    elif fix_type == '3':
                        fix_status = "3D"
            except (ValueError, IndexError):
                continue

    return num_satellites, signal_quality, fix_status
  

def chk_gps3():
    gps_device_fd = "/dev/serial0"
    gps_data = ""

    try:
        with subprocess.Popen(['cat', gps_device_fd], stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
            time.sleep(2)
            proc.terminate()
            stdout, stderr = proc.communicate()
            gps_data = stdout.decode('utf-8', errors='ignore')
        
            if stderr:
                print(f"Erro ao acessar o dispositivo serial: {stderr.decode('utf-8', errors='ignore')}")
                return "No Fix", "0", "0"

    except Exception as e:
        print(f"Erro ao executar o comando cat: {e}")
        return "No Fix", "0", "0"

    fix_status = "No Fix"
    num_satellites = 0
    signal_quality = 0
    countA = 0
    countV = 0

    nmea_sentences = gps_data.split('\n')  # Dividir os dados GPS em sentenças NMEA
    for sentence in nmea_sentences:
        parts = sentence.split(',')
        try:
            if sentence.startswith('$GPGGA') or sentence.startswith('$GNGGA'):
                # A sentença GGA fornece dados de fixação
                num_satellites = int(parts[7])
            elif sentence.startswith('$GPRMC') or sentence.startswith('$GNRMC'):
                # A sentença RMC fornece o status de validade
                if parts[2] == 'A':
                    countA += 1
                else:
                    countV += 1
            elif sentence.startswith('$GPGSV') or sentence.startswith('$GNGSV'):
                # A sentença GSV fornece a relação sinal-ruído
                for i in range(7, len(parts), 4):
                    snr = parts[i]
                    if snr.isdigit():
                        signal_quality = max(signal_quality, int(snr))
            elif sentence.startswith('$GNGSA'):
                # A sentença GSA fornece o tipo de fix
                if parts[2] == '1':
                    fix_status = "1D"
                elif parts[2] == '2':
                    fix_status = "2D"
                elif parts[2] == '3':
                    fix_status = "3D"
        except (IndexError, ValueError) as e:
            print(f"Erro ao analisar a sentença: {sentence}, Erro: {e}")
            continue

    return fix_status, str(signal_quality), str(num_satellites)


    
def check_modem():
    interfaces = psutil.net_if_stats()
    return "1" if "ppp0" in interfaces and interfaces["ppp0"].isup else "0"

def check_wlan_interface():
    interfaces = psutil.net_if_stats()
    return "1" if "wlan0" in interfaces and interfaces["wlan0"].isup else "0"

def check_ethernet_interface():
    interfaces = psutil.net_if_stats()
    return "1" if "eth0" in interfaces and interfaces["eth0"].isup else "0"
    
def check_ttyLTE():
    return "1" if os.path.exists('/dev/ttyLTE') else "0"

def check_ttyARD():
    return "1" if os.path.exists('/dev/ttyARD') else "0"

def check_ttyMDN():
    return "1" if os.path.exists('/dev/ttyMDN') else "0"

def send_serial_command(command):
    if check_ttyMDN() == "1":
        ser = None
        try:
            ser = serial.Serial("/dev/ttyMDN", 115200, timeout=1)  # Set a 1 second read timeout

            # Send the provided command
            ser.write(command)

            # Read lines with a timeout
            response = ""
            for _ in range(10):  # Try for up to 10 seconds
                bs = ser.readline()
                response += bs.decode()

                if "Error" in response:
                    return "Error"
                elif "OK" in response:
                    return response

            print("Timeout reached. Exiting.")
            return "Error"
        except serial.SerialException as e:
            print(f"Error: {e}")
            return "Error"
        finally:
            # Always close the serial connection
            if ser and ser.isOpen():
                ser.close()
    else:
        return "Error"
    
def modem_signal():
    text_signal = b'AT+CSQ\r'
    result = send_serial_command(text_signal)
    if result != "Error":
        try:
            signal_strength = float(result.split("\n")[1].split(":")[1].strip().replace(',', '.'))
            if signal_strength == 99:
                return '0'
            elif signal_strength >= 2:
                return '1'
            else:
                return '0'
        except (IndexError, ValueError) as e:
            print(f"Parsing error: {e}")
            return '0'
    else:
        return '0'

def modem_status():
    text_status = b'AT+CPAS\r'
    result = send_serial_command(text_status)
    if result != "Error":    
        try:
            result2 = result.split(":")[1].strip().lower()
            if "ok" in result2:
                return '1'
            elif "error" in result2:
                return '0'
            else:
                return '0'
        except IndexError as e:
            print(f"Parsing error: {e}")
            return '0'
    else:
        return '0'

    
# def get_ccid():
#     command = b'AT+QCCID\r'
#     result = send_serial_command(command)
#     ccid = result.split("\n")[1].split(" ")[1]
#     if 'OK' in result and ccid:
#         return color(f' Sim inserted - CCID: {ccid}', 'green')
#     else:
#         return color(' Sim not inserted', 'red')

def verificar_horario_camera():
    answer=0
    caminho_arquivo = "/home/pi/.driver_analytics/logs/current/camera.log"
    try:
        with open(caminho_arquivo, "r") as file:
            for linha in file:
                if "bridge_handler: Data atualizada" in linha:
                    answer=1
    except FileNotFoundError:
        # print(f"O arquivo {caminho_arquivo} não foi encontrado.")
        answer=0
    except Exception as e:
        # print(f"Um erro ocorreu ao tentar ler o arquivo: {str(e)}")
        answer=0
    return answer

def find_last_camera_alive_line(log_file_path):
    last_camera_alive_line,error = run_bash_command(log_file_path)
    return last_camera_alive_line

# def parse_log_line(line):
#     # Example line: [20/08/2024 13:57:50] main: Camera is alive: 20/08/2024 14:10:00 {as1_camera_main.cpp:1147}
#     parts = line.split("Camera is alive uptime:")
#     if len(parts) > 1:
#         timestamp_str = parts[1].strip().split(" ")[0] + " " + parts[1].strip().split(" ")[1]
#         timestamp = datetime.strptime(timestamp_str, "%d/%m/%Y %H:%M:%S")
#         return timestamp
#     return None

# def check_camera_alive(log_path):
#     with open(log_path, 'r') as file:
#         lines = file.readlines()

#     last_check_time = None

#     for line in reversed(lines):
#         if "Camera is alive" in line:
#             last_check_time = parse_log_line(line)
#             break

#     if last_check_time is None:
#         print("Warning: No 'Camera is alive' log found.")
#         return False

#     now = datetime.now()
#     if (now - last_check_time).total_seconds() > 90:
#         print(f"Warning: The camera might be down! Last 'Camera is alive' log was at {last_check_time}.")
#         return False
#     else:
#         print(f"Camera is alive. Last checked at {last_check_time}.")
#         return True

def check_camera_status(mode): # é passado o mode que é para verificar na camera interna no log, somente camra interna descreve isso no log
    logpath = "/home/pi/.driver_analytics/logs/current/camera.log"
    updated=0
    available = ' 1 '
    if mode == 2:
        updated = verificar_horario_camera()
    command_frame=f"tail -n10 {logpath}"  
    result, error=run_bash_command(command_frame)
    if "Error opening the camera" in result:
        available = ' 0 '
    else:
        acurracy_line = f"tail -n5 {logpath} | grep -ia 'Camera is alive'"
        last_log_line,error2=run_bash_command(acurracy_line)
        data_hora_ultima_msg_str = str(last_log_line).split(']')[0].strip('[')[-19:]
        timestamp_ultima_msg = time.mktime(time.strptime(data_hora_ultima_msg_str, '%d/%m/%Y %H:%M:%S'))
        
        # Calcular a diferença de tempo
        diferenca_tempo = time.time() - timestamp_ultima_msg
        if(diferenca_tempo > 300 and updated == 0):
            available = ' 0 '
        elif (diferenca_tempo > 300 and updated == 1):
            first_try = find_last_camera_alive_line(acurracy_line)
            time.sleep(90)
            second_try = find_last_camera_alive_line(acurracy_line)
            if first_try == second_try:
                available = ' 0 '
            else:
                available = ' 1 '
        # else:
        #     available = ' 0 '

    command = "vcgencmd get_camera"
    output, error = run_bash_command(command)
    detected = ' 1 ' if "detected=1" in output else ' 0 '
    
        
    return detected, available

def check_camera_status2():
    try:
        subprocess.run(
            ["raspistill", "-o", "/tmp/camera_test.jpg", "-w", "640", "-h", "480", "-q", "1", "-n"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if not os.path.exists("/tmp/camera_test.jpg"):
            raise RuntimeError("Foto não foi criada apesar do comando ter sido executado com sucesso.")
        available = "1"
        print("Foi possível tirar a foto, a câmera está disponível")
    except subprocess.CalledProcessError:
        available = "0"
        print("Não foi possível tirar a foto, a câmera não está disponível")
    except FileNotFoundError:
        available = "0"
        print("O comando 'raspistill' não foi encontrado.")
    except Exception as e:
        available = "0"
        print(f"Ocorreu um erro inesperado: {e}")
    
    command = "vcgencmd get_camera"
    output, error = run_bash_command(command)
    detected = "1" if "detected=1" in output else "0"
    # connected = "1" if "supported=1" in output else "0"
        
    return detected, available  

def swap_memory():
    swap = psutil.swap_memory()
    return round(swap.percent,2)
    

def usage_cpu():
    cpuz=psutil.cpu_percent(interval=1)
    return round(cpuz,2)
            
def temp_system():
    command = "cat /sys/class/thermal/thermal_zone0/temp"
    output, error = run_bash_command(command)
    tempe=round(int(output)/1000)
    
    return tempe if not error else 0

def get_mac():
    command = "ifconfig wlan0 | awk '/ether/ {print $2}'"
    output,error= run_bash_command(command)
    
    return output if not error else f"Error: {error}"

def log(s, value=None):
    if DEBUG:
        if (value==None):
            print(s)
        else:
            print(s, value)


def checking_ignition():
    command="cat /dev/shm/IGNITION_IS_ON"
    output, error = run_bash_command(command)
    out=int(output)
    return out

def current_time_pi():
    command="date +'%Y/%m/%d'"
    output,error = run_bash_command(command)
    return output

def current_timestamp():
    command="uptime"
    output,error = run_bash_command(command)
    uptime_info = output.split("up")[0].strip()
    current_time = uptime_info.split()[-1]
        
    return current_time

def verificar_e_criar_tabela(path):
    conn = create_connection(path)
    cursor=conn.cursor() 
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS health_device (
            id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            Data TEXT,
            timestamp TEXT,
            uptime TEXT,
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
            Mac_Address TEXT,
            Bytes_Sent TEXT,
            Bytes_Received TEXT,
            Voltage TEXT,
            Disk_Read_Count TEXT,
            Disk_Write_Count TEXT,
            Disk_Read_Bytes TEXT,
            Disk_Write_Bytes TEXT,
            Disk_Read_Time_ms TEXT,
            Disk_Write_Time_ms TEXT
        )''')
    conn.close()
    

def adicionar_dados(data,path):
    with db_lock:
        conn = create_connection(path)
        cursor=conn.cursor() 
        cursor.execute(''' INSERT INTO health_device (
            Data,timestamp,uptime, ignition, mode_aways_on, connection_internet, Modem_IP, Signal_modem, Status_modem, connection_extra, 
            connection_INT_EXT, Expanded, Free_disk, Size_disk, GPS_Fix, Signal_Strength, Avaible_Satellites, Detected_camera, 
            Available_camera, Active_imu, Swap_usage, CPU_Usage, ETH0_Interface, WLAN_Interface, USB_LTE, USB_ARD, Temperature, 
            Mac_Address, Bytes_Sent, Bytes_Received, Voltage, Disk_Read_Count, Disk_Write_Count, Disk_Read_Bytes, 
            Disk_Write_Bytes, Disk_Read_Time_ms, Disk_Write_Time_ms) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)
        conn.commit()
        conn.close()

def ler_dados(patho):    
        conn = create_connection(patho)
        cursor=conn.cursor() 
        dados = cursor.execute("SELECT * FROM health_device").fetchall()
        conn.close()
        return dados

#funciton to catch info com database    
def select_field_from_table(conn, field, table):
    cur = conn.cursor()

    command_sql = "SELECT " + field +  " from " + table + " LIMIT 1"

    cur.execute(command_sql)

    value = cur.fetchone()

    log(value[0])

    user_ret = value[0]

    log(type(user_ret))

    if (type(user_ret) is str):
        log("type is string")
    elif (type(user_ret) is bytes):
        log("type is bytes")
        user_ret = user_ret.decode("utf-8")
    else:
        user_ret = str(user_ret)        

    return user_ret

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
def postChekingHealth(urlbase, url, idVehicle, token, database):
    global r

    urlApi = urlbase + url + "heartbeat/" + idVehicle

    log(urlApi)

    with db_lock:
        dados=ler_dados(database)
        if len(dados) != 0: 
            rows=transformar_em_json(dados)
            for i in range(0, len(rows), 1000):  # Posta de 1000 em 1000 linhas
                batch = rows[i:i+1000]
                for linha in batch:
                    json_data = json.dumps(linha)
                    try:
                        r.headers.clear()
                        r.cookies.clear()
                        # Enviar uma solicitação POST com os parâmetros necessários
                        r = requests.post(urlApi, headers={"Authorization":"Bearer " + token, 'Cache-Control': 'no-cache'},data=json_data)
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

#function to get information about vehicle, maybe necessery change to search by mac
def getVehicle(urlbase, url, mac, token):
    global r

    urlApi = urlbase + url + "?mac_address=" + mac

    log(urlApi)

    # content = "\"content-type\":\"Bearer " + token + "\""
    # log(content)

    try:
        r.headers.clear()
        r.cookies.clear()
        r = requests.get(urlApi, headers={"Authorization":"Bearer " + token, 'Cache-Control': 'no-cache' })
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        log(e)
        log("error on getVehicle")
        return 500, {}

    ret_status_code = r.status_code
    log("[getVehicle] ret code", ret_status_code)

    response_json = {}

    if ret_status_code == 200:
        log("[getVehicle] Success! ")
        response_json = r.json()
    else:
        log("[getVehicle] Error")

    return ret_status_code, response_json


def enviar_para_api(path,path_o):
    global token
    response=''
    # create a database connection
    #comunicate with db getting macadress to search in api
    conn = create_connection(path_o)
    conn1= create_connection(path)
    # catch some data to struct api comunication
    with conn:
        api_user = select_field_from_table(conn, "user", "api_config")
        log(api_user)

        api_pass = select_field_from_table(conn, "password", "api_config")
        log(api_pass)

        api_url = select_field_from_table(conn, "url", "api_config")
        log(api_url)

        vehicle_plate = select_field_from_table(conn, "placa", "vehicle_config")
        
        log(vehicle_plate)
    
    print("pegou dados no banco")
    with conn1:
        vehicle_mac = select_field_from_table(conn1, "Mac_Address", "health_device")
    
    if not vehicle_mac:
        print("Endereço MAC não encontrado. Abortando o envio para a API.")
        return   
        
    
    #login
    code = None
    while (code != 201):
        code, token = login(api_url, "auth/local", str(api_user), str(api_pass))
        if (code != 201):
            time.sleep(retry_time_in_seconds)
    
    log("Login Token: ", token)
    
    # get vehicle
    while (code != 200):
        code, vehicleJson = getVehicle(api_url, "vehicles/", vehicle_mac, token)
        if (code != 200):
            time.sleep(retry_time_in_seconds)
        if (code == 401):
            codeLogin = None
            while (codeLogin != 201):
                codeLogin, token = login(api_url, "auth/local", api_user, api_pass)
                if (codeLogin != 201):
                    time.sleep(retry_time_in_seconds)
    
    count = vehicleJson['count']
    print("achou o veiculo e logou no portal")
    log(count)
    vehicleId = None
    if (code == 200 and count != 0):
        vehicleId = vehicleJson['rows'][0]['id']
    else:
        #create Vehicle
        log("Vehicle Not Found")
        exit()
    log("vehicleId", vehicleId)
    # get vehicle end
    print("achou o id")
    # url="https://6207-131-255-21-130.ngrok-free.app/heartbeat"
    
    response,jotason=postChekingHealth(api_url,"vehicles/",vehicleId,token,path)
    print(response)
    # url= api_url+"/devices/?mac_address="+vehicle_mac # url construida para comunicar no veiculo correto
    # with db_lock:
    #     dados=ler_dados(path)
    #     if len(dados) != 0: 
    #         rows=transformar_em_json(dados)
    #         headers = {'Content-Type': 'application/json'}
    #         for i in range(0, len(rows), 1000):  # Posta de 1000 em 1000 linhas
    #             batch = rows[i:i+1000]
    #             for linha in batch:
    #                 json_data = json.dumps(linha)
    #                 response = requests.post(url, data=json_data, headers=headers)
    #             print(response)
    #             if 200 == response.status_code:
    #                 conn = create_connection(path)
    #                 cursor=conn.cursor() 
    #                 cursor.execute("DELETE FROM health_device WHERE id <= ?", (batch[-1]['id'],))
    #                 conn.commit()
    #                 conn.close()

    
def transformar_em_json(dados):
    resultado = []
    for linha in dados:
        json_linha = {
            "id": linha[0],
            "data": linha[1],
            "timestamp": linha[2],
            "uptime(sec)": linha[3],
            "ignition": linha[4],
            "mode_aways_on": linha[5],
            "connection_internet": linha[6],
            "Modem_IP": linha[7],
            "Signal_modem": linha[8],
            "Status_modem": linha[9],
            "connection_extra": linha[10],
            "connection_int_ext": linha[11],
            "Expanded": linha[12],
            "Free_disk": linha[13],
            "Size_disk": linha[14],
            "GPS_Fix": linha[15],
            "Signal_Strength": linha[16],
            "Avaible_Satellites": linha[17],
            "Detected_camera": linha[18],
            "Available_camera": linha[19],
            "Active_imu": linha[20],
            "Swap_usage": linha[21],
            "CPU_Usage": linha[22],
            "ETH0_Interface": linha[23],
            "WLAN_Interface": linha[24],
            "USB_LTE": linha[25],
            "USB_ARD": linha[26],
            "Temperature": linha[27],
            "Mac_Address": linha[28],
            "Bytes_Sent": linha[29],
            "Bytes_Received": linha[30],
            "Voltage": linha[31],
            "Disk_Read_Count": linha[32],
            "Disk_Write_Count": linha[33],
            "Disk_Read_Bytes": linha[34],
            "Disk_Write_Bytes": linha[35],
            "Disk_Read_Time_ms": linha[36],
            "Disk_Write_Time_ms": linha[37]
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

# function to create a connection with database
def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by the db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        log(e)

    return conn

def initialize_and_read_gps(port, baudrate, final_baudrate):
    ser = None
    try:
        ser = open_serial_connection(port, baudrate)
        if ser:
            set_gps_baudrate(ser, final_baudrate)
            set_gnss_mode(ser)
            close_serial_connection(ser)
            time.sleep(1)
            ser = open_serial_connection(port, final_baudrate)
        if ser:
            gps_data = read_gps_data(ser, duration=3)
            num_satellites, signal_quality, fix_status = parse_gps_data(gps_data)
            return fix_status, signal_quality, num_satellites
    except Exception as e:
        print(f"Erro ao inicializar e ler dados do GPS: {e}")
    finally:
        if ser:
            close_serial_connection(ser)
    return "No Fix", "0", "0"

def check_central_enable():
    command = "pgrep central"
    output, error = run_bash_command(command)
    if output != "":
        return 1
    else:
        return 0

def ler_contador():
    with open("/home/pi/.health_monitor/counter.txt", "r") as arquivo:
        return int(arquivo.read().strip())

def escrever_contador(contador):
    with open("/home/pi/.health_monitor/counter.txt", "w") as arquivo:
        arquivo.write(str(contador))
    
def incrementar_contador_e_usar():
    contador = ler_contador()
    contador += 1
    # print("Contador atual:", contador)
    escrever_contador(contador)

def inicializar_contador():
    if not os.path.exists("/home/pi/.health_monitor/counter.txt"):
        with open("/home/pi/.health_monitor/counter.txt", "w") as arquivo:
            arquivo.write("0")
            return 0
    else:
        return ler_contador()

def read_diskstats():
    diskstats_path = '/proc/diskstats'
    with open(diskstats_path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        parts = line.split()
        if 'mmcblk0' in parts or 'sdb' in parts:  # Substitute 'mmcblk0' or 'sda' with your disk identifier
            read_count = int(parts[3])
            write_count = int(parts[7])
            read_sectors = int(parts[5])
            write_sectors = int(parts[9])
            read_time = int(parts[6])
            write_time = int(parts[10])
            sector_size = 512  # Typically 512 bytes per sector
            
            read_bytes = read_sectors * sector_size
            write_bytes = write_sectors * sector_size
            
            read_mb = read_bytes / (1024 * 1024)
            write_mb = write_bytes / (1024 * 1024)
            
            read_mb=round(read_mb, 2)
            write_mb=round(write_mb, 2)
    return read_mb, write_mb, read_count, write_count, read_time, write_time

def get_network_usage():
    net_io = psutil.net_io_counters()
    return {'bytes_sent': net_io.bytes_sent, 'bytes_recv': net_io.bytes_recv}

def check_voltage():
    try:
        voltage_output = subprocess.check_output(['vcgencmd', 'measure_volts']).decode()
        voltage = float(voltage_output.split('=')[1].strip('V\n'))
        return voltage
    except:
        return None

def get_system_uptime():
    uptime_seconds = os.popen('awk \'{print $1}\' /proc/uptime').read().strip()
    uptime_seconds = float(uptime_seconds)
    return round(uptime_seconds, 2)

def check_dmesg_for_errors():
    vet2 = []
    command = "dmesg | grep -ia 'usb cable is bad'"
    output, error = run_bash_command(command)
    if output:
        vet2.append("Maybe USB cable is bad")
    try:
        result = subprocess.run(['dmesg'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        dmesg_output = result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar dmesg: {e}")
        return []
    errors = {
        # "Under-voltage detected!": "Under-voltage",
        # "Over-current detected!": "Over-current",
        "I/O error": "I/O Error",
        "device descriptor read/64, error": "USB Device Error",
        "Out of memory:": "Out of Memory",
        "EXT4-fs error": "Filesystem Corruption",
        "Failed to start": "Service Start Failure",
        "Kernel panic": "Kernel Panic"
    }
    for line in dmesg_output.splitlines():
        for key, value in errors.items():
            if key in line:
                vet2.append(value)
    return vet2
    
def send_email_message(placa, problema, csv_file_path, mode="cdl", error_message=None):

    try:
        text_type = 'plain'
        text = "[PKG] O veículo de placa " + placa + " apresentou o problema " 
        if mode == "api":
            text = "[API] O veículo de placa " + placa + " apresentou o problema "  
        if mode == "cdl":
            text = "[CDL] O veículo de placa " + placa + ": "+ problema 
        if mode == "calib":
            text = "[CALIB] O veículo de placa " + placa + " apresentou o problema " 

        if error_message:
            text += f"\n\nErro detectado: {error_message}"

        msg = MIMEMultipart()
        msg.attach(MIMEText(text, text_type, 'utf-8'))

        subject = "[PKG] Veículo com placa " + placa + " está online!"
        if mode == "api":
            subject = "[API] Veículo " + placa + " Trocar acesso da empresa!"
        if mode == "cdl":
            subject = "[CDL] Veículo com placa " + placa + " apresentou o problema "
        if mode == "calib":
            subject = "[CALIB] Veículo com placa " + placa + " está online! Checar calibração!"

        msg['Subject'] = subject
        msg['From'] = "cco@motora.ai"
        msg['To'] = "joao.guimaraes@motora.ai, phellipe.santos@motora.ai, luiz@motora.ai"

        if csv_file_path:
            part = MIMEBase('application', 'octet-stream')
            with open(csv_file_path, 'rb') as file:
                part.set_payload(file.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(csv_file_path)}')
            msg.attach(part)

        mailserver = smtplib.SMTP('smtp.office365.com', 587)
        mailserver.ehlo()
        mailserver.starttls()
        password = "1Q@w3e4r"
        mailserver.login("cco@motora.ai", password)
        mailserver.send_message(msg)
        mailserver.quit()
        return True
    except Exception as e:
        return False

def check_rfid_log():
    # Command to verify if the RFID log contains the string 'no rfid found'
    command = "cat /home/pi/.driver_analytics/logs/current/rfid.log | grep -ia 'no rfid found'"
    
    try:
        # Execute the command and capture the output
        result,error = run_bash_command(command)
        
        # Verify if the output contains the string 'no rfid found'
        if result != "":
            print("RFID log contains 'no rfid found'")
            return 1
        else:
            print("RFID log does not contain 'no rfid found'")
            return 0
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        return 0

def create_directory_if_not_exists(directory_path):
    # Expande o caminho do diretório (caso haja '~' no caminho)
    expanded_path = os.path.expanduser(directory_path)
    
    # Verifica se o diretório existe, se não, cria o diretório
    if not os.path.exists(expanded_path):
        os.makedirs(expanded_path)
        print(f"Diretório {expanded_path} criado com sucesso.")
    else:
        print(f"Diretório {expanded_path} já existe.")

def registrar_problemas(var, caminho_arquivo):
    data=current_time_pi() + current_timestamp()
    
    if len(var) > 0:
        with open(caminho_arquivo, "a") as file:
            file.write(f"{data}\n")
            for item in var:
                file.write(f"{item}\n")
            

def ler_problemas_registrados(caminho_arquivo):
    try:
        with open(caminho_arquivo, "r") as file:
            problemas = file.readlines()
        
        # Concatena todas as linhas em uma única string
        problemas_como_string = "".join(problemas)
        return problemas_como_string
    
    except FileNotFoundError:
        return "0"
    
# Função para ler o conteúdo do arquivo de problemas
def ler_conteudo_arquivo(caminho):
    if os.path.exists(caminho):
        with open(caminho, "r") as file:
            return file.read()
    return ""

# Função para comparar se o conteúdo atual já foi enviado anteriormente
def verificar_envio_previo(problems_path, sent_path):
    ultimo_conteudo = ler_conteudo_arquivo(sent_path)
    conteudo_atual = ler_conteudo_arquivo(problems_path)
    return ultimo_conteudo.strip() == conteudo_atual.strip()

# Função para verificar se há novos problemas na lista
def verificar_novos_problemas(problems_path, sent_path):
    ultimo_conteudo = ler_conteudo_arquivo(sent_path)
    conteudo_atual = ler_conteudo_arquivo(problems_path)
    return conteudo_atual.strip() != ultimo_conteudo.strip()

# Função para registrar o envio bem-sucedido
def registrar_envio_sucesso(sent_path, conteudo_atual):
    with open(sent_path, "w") as file:
        file.write(conteudo_atual)
        file.write(f"\nEnviado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Função principal de envio de e-mail
def enviar_email_com_logica(var, vehicle_plate, problems_path, sent_path):
    conncetion_chk = check_internet()
    registrar_problemas(var, problems_path)
    conteudo_atual = ler_conteudo_arquivo(problems_path)
    if verificar_envio_previo(problems_path, sent_path):
        print("Conteúdo já foi enviado anteriormente. Verificando o tempo.")
        with open(sent_path, "r") as file:
            linhas = file.readlines()
            if linhas:
                ultima_linha = linhas[-1]
                if "Enviado em:" in ultima_linha:
                    ultima_data_envio = datetime.strptime(ultima_linha.split(": ")[1].strip(), '%Y-%m-%d %H:%M:%S')
                    if datetime.now() - ultima_data_envio < timedelta(hours=1):
                        if not verificar_novos_problemas(problems_path, sent_path):
                            print("Conteúdo idêntico foi enviado na última hora. Aguardando para reenviar.")
                            return
                        else:
                            print("Novos problemas detectados. Enviando e-mail imediatamente.")
    
    if conncetion_chk:
        sucesso = send_email_message(vehicle_plate, "Problemas detectados", problems_path, error_message=None)
        if sucesso:
            registrar_envio_sucesso(sent_path, conteudo_atual)
        else:
            with open(sent_path, "w") as file:
                file.write("0")
    else:
        print("Sem conexão com a internet. Tentando novamente em 1 minuto...")
        time.sleep(60)  # Espera 1 minuto
        if check_internet():
            print("Conexão restaurada. Tentando enviar o e-mail novamente...")
            sucesso = send_email_message(vehicle_plate, "Problemas detectados", problems_path, error_message=None)
            if sucesso:
                registrar_envio_sucesso(sent_path, conteudo_atual)
            else:
                with open(sent_path, "w") as file:
                    file.write("0")
        else:
            print("Falha ao enviar o e-mail após 2 tentativas. Deixando para a próxima execução.") 

def main():
    directory_path = '/home/pi/.driver_analytics/health/'
    # print("Passei aqui inicio..." + current_time_pi())
    problems_path = '/home/pi/.driver_analytics/health/problems.txt'
    sent_path = '/home/pi/.driver_analytics/health/sent.txt'
    port = '/dev/serial0'
    baudrate = 9600  # Inicialmente abrir com 9600 para enviar comandos
    final_baudrate = 115200  # Baudrate desejado
    path_e=''
    filename="/home/pi/.driver_analytics/mode"
    config=load_config(filename) 
    global token
    var=[]
    
    # Guardando os valores das variavel mode em config
    AS1_BRIDGE_MODE = int(config.get("BRIDGE_MODE", ""))
    AS1_CAMERA_TYPE = int(config.get("CAMERA_TYPE", ""))
    # AS1_NUMBER_OF_SLAVE_DEVICES = int(config.get("NUMBER_OF_SLAVE_DEVICES", ""))
    AS1_ALWAYS_ON_MODE = config.get("ALWAYS_ON_MODE", "") if config.get("ALWAYS_ON_MODE", "") != "" else 0
    AS1_NUMBER_OF_EXTRA_CAMERAS = int(config.get("NUMBER_OF_EXTRA_CAMERAS", "")) if config.get("NUMBER_OF_EXTRA_CAMERAS", "") != "" else 0   
    
    if flag == 0:
        if AS1_CAMERA_TYPE == 0:
            verificar_e_criar_tabela(pathe)
            path_e=pathe
        elif AS1_CAMERA_TYPE ==1:
            verificar_e_criar_tabela(pathi)
            path_e=pathi
        api_thread = threading.Thread(target=enviar_para_api, args=(path_e,pathdriver))
        api_thread.start() # Inicia a thread de postar na api
        # Verifica se não existe banco e tabela e cria os mesmos
        
    elif flag == 1:
        create_directory_if_not_exists(directory_path)
        current_date = datetime.now().strftime('%Y%m%d')
        counter_id=inicializar_contador()
        if AS1_BRIDGE_MODE == 0 or AS1_BRIDGE_MODE == 1:
            filename = f"/home/pi/.driver_analytics/health/driver_analytics_health_e_{current_date}.csv"
        elif AS1_BRIDGE_MODE == 2:
            filename = f"/home/pi/.driver_analytics/health/driver_analytics_health_i_{current_date}.csv"
    
    if check_rfid_log() ==1:
        var.append("RFID não detectado")
    
    ig = checking_ignition() # checa ignição
    date = current_time_pi() # busca data em que foi rodado o script
    timestamp=current_timestamp() # busca timestamp
    total_size,free_size,size = get_machine_storage() #busca informações de armazenamento
    read_mb, write_mb, read_count, write_count, read_time, write_time = read_diskstats()        
    conncetion_chk = check_internet() # verifica se tem conexão com a internet
    swapa = swap_memory() # Verifica se esta tendo swap de memoria
    cpu = usage_cpu() # % Verifica uso da cpu
    interface_e = check_ethernet_interface() # Verifica se existe porta ethernet
    interface_wlan = check_wlan_interface() # Verifica se o wifi esta funcional
    temperature= temp_system() # Verifica temperatura do sistema
    # if temperature > 90:
    #     var.append("Temperatura Alta\n")
    macmac=get_mac() # Verifica o mac adress
    network_usage = get_network_usage()
    voltage=check_voltage()
    uptime=get_system_uptime()
    
    # Verify internal and external connection
    if AS1_CAMERA_TYPE == 0:
        connect_int_ext = check_ip_connectivity(ip_interna)
    elif AS1_CAMERA_TYPE ==1:
        connect_int_ext = check_ip_connectivity(ip_externa)
    else:
        connect_int_ext=None
        var.append("Erro na conexão interna e externa")
    
    # Verify always on mode
    modee=AS1_ALWAYS_ON_MODE if AS1_ALWAYS_ON_MODE != '' else 0
    
    # Verify extra cameras
    if AS1_NUMBER_OF_EXTRA_CAMERAS >0:
        connect_extra= check_ip_connectivity(ip_extra)
    else:
        connect_extra= None
    
    # Verify modem process
    if AS1_BRIDGE_MODE == 0 or AS1_BRIDGE_MODE ==1: # 0 master sem slave / 1 master com slave / 2 e slave
        Process_modem = check_modem()
        imu = imu_check()
        signal = modem_signal()
        status = modem_status()
        Lte = check_ttyLTE()
    else:
       Process_modem = None
       imu = None
       signal = None
       status = None
       Lte = None
    
    # Verify Arduino
    if AS1_CAMERA_TYPE == 0:
        Ard = check_ttyARD()
        if int(Ard) == 0:
            var.append("Arduino não detectado")
    else:
        Ard = None
    
    #Verify central status and read camera and gps
    teste = check_central_enable() 
    if teste == 1:
        print("Central ligado, verificado de forma normal...")
        detected,available = check_camera_status(AS1_BRIDGE_MODE) # detecta e verifica o camera
        if int(available) == 0:
            var.append("Erro na camera")
        # Verifica GPS
        if AS1_BRIDGE_MODE == 0 or AS1_BRIDGE_MODE ==1:
            fix, sig_str, sat_num = chk_gps3() # modificado para teste
        else:
            fix, sig_str, sat_num = None,None,None
               
    elif teste == 0:
        print("Central desligado, checando foto com raspistill e gps...")
        comandext = "sudo pkill camera"
        out1=run_bash_command(comandext)
        detected,available = check_camera_status2() # detecta e verifica o camera
        if int(available) == 0:
            var.append("Erro na camera")
        if AS1_BRIDGE_MODE == 0 or AS1_BRIDGE_MODE ==1: # Verifica GPS
            fix, sig_str, sat_num = initialize_and_read_gps(port, baudrate, final_baudrate)
        else:
            fix, sig_str, sat_num = None,None,None
    
    # Verify flag to create a database or create a csv file
    if flag == 0:
        data_values=(
            date,
            timestamp,
            uptime,
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
            str(temperature),
            macmac.strip(),
            network_usage["bytes_sent"],
            network_usage["bytes_recv"],
            voltage,
            read_count,
            write_count,
            read_mb,
            write_mb,
            read_time,
            write_time
        ) 

        if AS1_CAMERA_TYPE == 0:
            adicionar_dados(data_values,pathe) 
        elif AS1_CAMERA_TYPE ==1:
            adicionar_dados(data_values,pathi)
    elif flag == 1:
        conn = create_connection(pathdriver)
        with conn:
            vehicle_plate = select_field_from_table(conn, "placa", "vehicle_config")
        answer = ""
        data = [
            ["counter", counter_id],
            ["Data", date],
            ["timestamp", timestamp],
            ["Uptime(sec)", uptime],
            ["ignition", ig],
            ["mode_aways_on", modee],
            ["connection_internet", conncetion_chk],
            ["Modem_IP", Process_modem], 
            ["Signal_modem", signal],
            ["Status_modem", status],
            ["connection_extra", connect_extra],
            ["connection_int_ext", connect_int_ext],
            ["Expanded", total_size],
            ["Free_disk", free_size],
            ["Size_disk", size],
            ["GPS_Fix", fix], 
            ["Signal_Strength", sig_str],
            ["Avaible_Satellites", sat_num],
            ["Detected_camera", detected],
            ["Available_camera", available],
            ["Active", imu],
            ["Swap_usage(%)", swapa], 
            ["CPU_Usage(%)", cpu], 
            ["ETH0_Interface", interface_e],
            ["WLAN_Interface", interface_wlan],
            ["USB-LTE", Lte],
            ["USB_ARD", Ard], 
            ["Temperature", temperature],
            ["Mac_Adress", macmac.strip()],
            ["Bytes_Sent", network_usage["bytes_sent"]],
            ["Bytes_Received", network_usage["bytes_recv"]],
            ["Voltage", voltage],
            ["Disk_Read_Count", read_count],
            ["Disk_Write_Count", write_count],
            ["Disk_Read_Bytes_mb", read_mb],
            ["Disk_Write_Bytes_mb", write_mb],
            ["Disk_Read_Time (ms)", read_time],
            ["Disk_Write_Time (ms)", write_time]
        ]
        
        with open(filename, mode='a', newline='') as file:  # Use mode='a' para adicionar ao arquivo existente
            # Verificar se o arquivo está vazio para escrever o cabeçalho
            if os.stat(filename).st_size == 0:
                fieldnames = [att[0] for att in data]
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()

            writer = csv.writer(file)

            stats = [val[1] for val in data]

            writer.writerow(stats)
        incrementar_contador_e_usar()
    
        if check_dmesg_for_errors() != None:
            var.extend(check_dmesg_for_errors())
        # print(f"tamanho do vetor var:  {len(var)}")
        
        if len(var) > 0:
            # enviar_email_com_logica(var, vehicle_plate, problems_path, sent_path)
            for item in var:
                answer += f"{item}\n"
            send_email_message(vehicle_plate,answer, filename, error_message=None)
        # if(len(var) > 0):
        #     registrar_problemas(var, problems_path)
        #     if conncetion_chk:
        #         sen = send_email_message(vehicle_plate,"Problemas detectados", problems_path, error_message=None)
        #         if sen:
        #             with open(sent_path, "w") as file:
        #                 file.write("1")
        #                 file.write(f"{timestamp} + {date}")
        #         else:
        #             with open(sent_path, "w") as file:
                        
        #                 file.write("0")
        #     else:
        #         contador = 0
        #         while contador < 5:
        #             time.sleep(20)
        #             rede = check_internet()
        #             print("Tentando enviar email...")
        #             if rede:
        #                 send_email_message(vehicle_plate,"Problemas detectados", problems_path, error_message=None)
        #                 contador=5
        #             contador += 1
                
            
            
          
        
        # send_email_message(vehicle_plate,answer, filename, error_message=None)  
            #sending csv----------------------------------------
            # url="https://e50e-131-255-23-67.ngrok-free.app/heartbeat"
            # response = send_csv_to_api(filename, url, answer)
            # print(response)
            
            #sending Json--------------------------------------    
            # json_data= json.dumps(data_jotason)
            # print(json_data)
            # headers = {'Content-Type': 'application/json'}
            # url="https://9a61-131-255-22-153.ngrok-free.app/heartbeat"
            # response = requests.post(url, data=json_data, headers=headers)
            # print(response)
            #----------------------------------------------------
    
    print("Passei aqui no final.." + current_time_pi())           


if __name__ == '__main__':
    main()

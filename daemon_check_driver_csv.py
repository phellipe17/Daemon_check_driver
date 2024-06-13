import time
import socket
import psutil
import os
import subprocess
import serial
import json, requests
import csv
import smtplib
import sqlite3
from sqlite3 import Error

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Caminho do diretório
directory_path = '/home/pi/.driver_analytics/logs/current/'
r = requests.session()
DEBUG = False
pathdriver="/home/pi/.driver_analytics/database/driveranalytics.db"

#from daemonize import Daemonize
daemon_name = 'chk_status'

problems_list = []

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
    return output.decode().strip(), error.decode().strip()



def imu_check():
    log("Testando imu")
    command2 = 'i2cdetect -y 1 | grep -ia 68'
    result, error=run_bash_command(command2)
    if (result != ''):
        return ' 1 '
    else:
        problems_list.append("Problema na IMU")
        return '0'
        

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

# Verificações de Hardware ------------------------------------------------------------------------------

def get_cpu_usage():
    return psutil.cpu_percent(interval=1)

def get_memory_usage():
    mem = psutil.virtual_memory()
    return mem.percent

def get_disk_usage():
    disk = psutil.disk_usage('/')
    return disk.percent

def get_disk_io():
    disk_io = psutil.disk_io_counters()
    return {'read_bytes': disk_io.read_bytes, 'write_bytes': disk_io.write_bytes}

def get_temperature():
    try:
        temp_output = subprocess.check_output(['vcgencmd', 'measure_temp']).decode()
        temp = float(temp_output.split('=')[1].split("'")[0])
        return temp
    except:
        return None

def get_network_usage():
    net_io = psutil.net_io_counters()
    return {'bytes_sent': net_io.bytes_sent, 'bytes_recv': net_io.bytes_recv}

def get_system_uptime():
    uptime_seconds = os.popen('awk \'{print $1}\' /proc/uptime').read().strip()
    uptime_milliseconds = int(float(uptime_seconds) * 1000)
    return uptime_milliseconds 

def get_uptime_ms():
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            uptime_milliseconds = int(uptime_seconds * 1000)
            return uptime_milliseconds
    except Exception as e:
        print(f"Error reading uptime: {e}")
        return None

def check_voltage():
    try:
        voltage_output = subprocess.check_output(['vcgencmd', 'measure_volts']).decode()
        voltage = float(voltage_output.split('=')[1].strip('V\n'))
        return voltage
    except:
        return None

def get_disk_io():
    disk_io = psutil.disk_io_counters(nowrap=True)
    return {
        'read_count': disk_io.read_count,
        'write_count': disk_io.write_count,
        'read_bytes': disk_io.read_bytes,
        'write_bytes': disk_io.write_bytes,
        'read_time': disk_io.read_time,
        'write_time': disk_io.write_time
    }
#--------------------------------------------------------------------------------------------

# check_internet(): This function checks for internet connectivity by attempting to create a connection to 
# www.google.com. It returns True if the connection is successful and False otherwise.
def check_internet():
    log("testando internet")
    try:
        # Tente fazer uma conexão com um servidor remoto (por exemplo, o Google)
        socket.create_connection(("www.google.com", 80))
        return '1'
    except OSError:
        return '0'


def check_ip_connectivity(ip_address):
    log("testando conexao ip")
    try:
        # Tente fazer uma conexão com o IP fornecido na porta 80 (HTTP)
        socket.create_connection((ip_address, 80))
        return '1'
    except OSError:
        return '0'
     
# get_machine_storage(): This function calculates and returns the total and free storage space on the root filesystem. 
# If the total storage is less than 10 GB, it attempts to expand the root filesystem and requests a reboot.
def get_machine_storage():
    log("teste size")
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
        total_size_status =' 1 '
    else:
        total_size_status = ' 0 '
        problems_list.append("Armazenamento total inferior a 10")

    if (free_size < 0.05 * total_size):
        free_size_status = ' 0 '
        problems_list.append("Pouco espaço disponível em disco")
    else:
        free_size_status = ' 1 '
    return total_size_status, free_size_status,total_size

# clear_log_file(log_file_path): This function clears the contents of a log file specified by log_file_path.
def clear_log_file(log_file_path):
    with open(log_file_path, 'w') as file:
        file.write("") 

    
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
    log("teste gps")
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
        fix= "3D"
    elif avg_fix <= 2 and validity_status == 'A':
        fix= "2D"
    else:
        fix = "No Fix"
        problems_list.append("GPS: Sem fix")
        

    if snr_values:
        if avg_snr >= 35:
            sig_str = f"{avg_snr:.2f}"
        elif avg_snr >= 25:
            sig_str = f"{avg_snr:.2f}"
        else:
            sig_str = f"{avg_snr:.2f}"
            problems_list.append("GPS: Sinal de GPS fraco")

    if num_satellites is not None:
        if avg_num_satellites >= 8:
            sat_num = f"{avg_num_satellites:.0f}"
        elif avg_num_satellites >= 5:
            sat_num =f"{avg_num_satellites:.0f}"
        else:
            sat_num = f"{avg_num_satellites:.0f}"
            problems_list.append("GPS: Poucos satélites disponíveis")
    
    return fix, sig_str, sat_num
    
def chk_dial_modem():
    log("teste modem")
    modem_command = 'ip addr | grep -ia ppp0'
    result, error=run_bash_command(modem_command)
    if(result != ''):
        return ' 1 '
    else:
        problems_list.append(f"Erro no modem: {error}")
        return ' 0 '

def chk_wlan_interface():
    log("teste wlan")
    wlan_command = 'ip addr show wlan0'
    result, error = run_bash_command(wlan_command)
    if 'UP' in result:
        return ' 1 '
    else:
        problems_list.append(f"Erro no wlan: {error}")
        return ' 0 '

def chk_ethernet_interface():
    log("teste ethernet")
    eth_command = 'ip addr show eth0'
    result, error = run_bash_command(eth_command)
    if 'UP' in result:
        return ' 1 '
    else:
        problems_list.append(f"Erro no ethernet: {error}")
        return ' 0 '

def chk_ttyLTE():
    log("teste conexao modem")
    command = 'ls /dev/'
    result,error = run_bash_command(command)
    if 'ttyLTE' in result:
        return '1'
    else:
        problems_list.append(f"Erro de conexão modem: {error}")
        return '0'

def chk_ttyARD():
    log("teste display")
    command = 'ls /dev/'
    result,error = run_bash_command(command)
    if 'ttyARD' in result:
        return '1'
    else:
        problems_list.append(f"Erro no display: {error}")
        return '0'


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
    log("teste sinal modem")
    text_signal =b'AT+CSQ\r'
    result= send_serial_command(text_signal)
    result2= result.split("\n")[1].split(":")[1].strip()	    
    if len(result2)>0:
        signal_strength=float(result2.replace(',','.'))
        if(signal_strength==99):
            return '0'
        elif(signal_strength>=31):
            return ' 1 '
        elif(signal_strength<31 and signal_strength>=2):
            return ' 1 '
        elif(signal_strength<2 and  signal_strength>=0):
            return ' 0 '
    else:
        return 0

def modem_status():
    log("teste status modem")
    text_status =b'AT+CPAS\r'
    result = send_serial_command(text_status)
    result2 = result.split(":")[1].strip()
    if "ok" in result2.lower():
        return ' 1 '
    elif "error" in result2.lower():
        problems_list.append(f"Erro no modem: {result2}")
        return ' 0 '
    else:
        problems_list.append("Status modem indefinido")
        return "Undefined"
    
def get_ccid():
    command = b'AT+QCCID\r'
    result = send_serial_command(command)
    # print(result)
    ccid = result.split("\n")[1].split(" ")[1]
    if 'OK' in result and ccid:
        return f' Sim inserted - CCID: {ccid}'
    else:
        problems_list.append("Cartão sim não inserido")
        return ' Sim not inserted'

def check_camera_status():
    command_frame="tail -n10 /home/pi/.driver_analytics/logs/current/camera.log"
    result, error=run_bash_command(command_frame)
    available= " 1 "
    if "Error opening the camera" in result:
        available = " 0 "
        problems_list.append("Erro ao abrir a camera")
    else:
        last_log_line=run_bash_command('tail -n2 /home/pi/.driver_analytics/logs/current/camera.log')
        data_hora_ultima_msg_str = str(last_log_line).split(']')[0].strip('[')[-19:]
        timestamp_ultima_msg = time.mktime(time.strptime(data_hora_ultima_msg_str, '%d/%m/%Y %H:%M:%S'))
        # Calcular a diferença de tempo
        diferenca_tempo = time.time() - timestamp_ultima_msg
        if(diferenca_tempo>60):
            available=" 0 "
            problems_list.append("Camera não detectada")

    command = "vcgencmd get_camera"
    output, error = run_bash_command(command)
    detected =" 1 " if "detected=1" in output else " 0 "
    
        
    return detected, available

# def check_camera_status2():
#     try:
#        subprocess.run(["raspistill", "-o", "/tmp/camera_test.jpg", "-w", "640", "-h", "480"], check=True,stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
#        available = " YES "
#     except subprocess.CalledProcessError as e:
#        available = f" NO - error no:({e.returncode})"
    
#     command = "vcgencmd get_camera"
#     output, error = run_bash_command(command)
#     detected = " YES ", "green" if "detected=1" in output else " NO "
#     connected = " YES " if "supported=1" in output else " NO "
        
#     return detected, connected, available  

def swap_memory():
    log("teste swap memoria")
    command = "free -h | grep -iA 1 swap | tail -n 1 | awk '{printf \"%.2f\", ($3/$2)*100}'"
    output, error = run_bash_command(command)
    
    if error:
        problems_list.append(f"Erro no swap de memória: {error}")
        return f" Error: {error} "
    else:
        return f"{output}%"
    

def usage_cpu():
    command = "top -bn1 | grep '^%Cpu(s)' | awk '{print $8}'"                                                     
    output, error = run_bash_command(command)
    idle_time = float(output.strip().replace(',', '.'))
    usage = 100 - idle_time
    if error:
        problems_list.append(f"Erro ao obter uso da CPU: {error}")
    
    return f" {usage:.2f}% " if not error else f"Error: {error}"
        
def temp_system():
    command = "cat /sys/class/thermal/thermal_zone0/temp"
    output, error = run_bash_command(command)
    tempe=round(int(output)/1000)
    if error:
        problems_list.append(f"Erro ao obter temperatura: {error}")
        return f" Error: {error} "
    else:
        if tempe >= 80:
            return f"{tempe}°"
        elif tempe >= 60 & tempe <80:
            return f"{tempe}°"
        elif tempe<60:
            return f"{tempe}°"

def get_mac():
    command = "ifconfig eth0 | grep -oE '([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}'"
    output,error= run_bash_command(command)
    if error:
        problems_list.append(f"Erro ao obter endereço mac: {error}")
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
    if error:
        problems_list.append(f"Erro ao verificar ignição: {error}")
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

def check_error_dmesg():
    
    # command = "dmesg | grep -ia "+comandodo
    command="dmesg | grep -ia error"
    command2="dmesg | grep -ia over-current"
    command3="dmesg | grep -ia Under-voltage"
    command4="dmesg | grep -ia 'usb-bad cable'"
    output, error = run_bash_command(command)
    output2, error2 = run_bash_command(command2)
    output3, error3 = run_bash_command(command3)
    output4, error4 = run_bash_command(command4)
    
    if output != "":
        problems_list.append(f"Erro dmesg: {error}")
        return 1
    elif output2 != "":
        problems_list.append(f"Erro dmesg: {error2}")
        return 1
    elif output3 != "":
        problems_list.append(f"Erro dmesg: {error3}")
        return 1
    elif output4 != "":
        problems_list.append(f"Erro dmesg: {error4}")
        return 1
    else:
        return 0
    
# def send_csv_to_api(file_path, url,message):
#     with open(file_path, 'rb') as file:
#         files = {'file': file}
#         data = {'message': message}
#         response = requests.post(url, files=files, data=data)
#         return response

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

# function to select a field from a database    
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

def load_config(filename):
    config = {}
    with open(filename) as f:
        for line in f:
            key, value = line.strip().split("=")
            config[key] = value
    return config
        
def send_email_message(placa, problems_list, csv_file_path, data_str, error_message=None):

    text_type = 'plain'

    text = f"""Foram encontrados os seguintes problemas no dispositivo {placa}:

        {problems_list}

Os últimos dados coletados foram:

        {data_str}

"""

    if error_message:
        text += f"\n\nErro detectado: {error_message}"

    msg = MIMEMultipart()
    msg.attach(MIMEText(text, text_type, 'utf-8'))

    subject = "Problema(s) no Veículo com placa " + placa + "!"

    msg['Subject'] = subject
    msg['From'] = "cco@motora.ai"
    msg['To'] = "joao.guimaraes@motora.ai, phellipe.santos@motora.ai"
    # msg['To'] = "joao.guimaraes@motora.ai"

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
    
        

def main():
    problema=0
    #log_file_path = f'/home/pi/.monitor/logs/current/{daemon_name}.log'
    # log_file_path = '/var/log/checking_health.log'
    answer=""
    conn = create_connection(pathdriver)
    filename2="/home/pi/.driver_analytics/mode"
    vehicle_plate = ""
    # filename = "/home/pi/.driver_analytics/logs/driver_analytics_health.csv"
    config=load_config(filename2) 
    counter_id=inicializar_contador()
    ip_extra="10.0.89.11"
    ip_interna="10.0.90.196"
    ip_externa="10.0.90.195"
    
    # Saving the configuration parameters
    AS1_BRIDGE_MODE = int(config.get("BRIDGE_MODE", ""))
    AS1_CAMERA_TYPE = int(config.get("CAMERA_TYPE", ""))
    # AS1_NUMBER_OF_SLAVE_DEVICES = int(config.get("NUMBER_OF_SLAVE_DEVICES", ""))
    AS1_ALWAYS_ON_MODE = config.get("ALWAYS_ON_MODE", "") if config.get("ALWAYS_ON_MODE", "") != "" else 0
    AS1_NUMBER_OF_EXTRA_CAMERAS = int(config.get("NUMBER_OF_EXTRA_CAMERAS", "")) if config.get("NUMBER_OF_EXTRA_CAMERAS", "") != "" else 0
    
    #Create table csv identifing extern and intern cameras
    
    if AS1_BRIDGE_MODE == 0 or AS1_BRIDGE_MODE == 1:
        filename = "/home/pi/.driver_analytics/logs/driver_analytics_health_e.csv"
    elif AS1_BRIDGE_MODE == 2:
        filename = "/home/pi/.driver_analytics/logs/driver_analytics_health_i.csv"
    
    #Connect to database and get the vehicle plate
    with conn:
         vehicle_plate = select_field_from_table(conn, "placa", "vehicle_config")
    
    
    # Verify GPS
    if(AS1_BRIDGE_MODE == 0 or AS1_BRIDGE_MODE ==1):
        fix, sig_str, sat_num = chk_gps3()
        if fix == None or sig_str == None or sat_num == None:
            problema=1
    else:
        fix, sig_str, sat_num = None,None,None
    
    # Verify connection between internal and external cameras
    if AS1_CAMERA_TYPE == 0:
        connect_int_ext = check_ip_connectivity(ip_interna)
    elif AS1_CAMERA_TYPE ==1:
        connect_int_ext = check_ip_connectivity(ip_externa)
    else:
        connect_int_ext=None
        
    # Verify always on mode
    modee=AS1_ALWAYS_ON_MODE if AS1_ALWAYS_ON_MODE != '' else 0
    
    # Verify connection between extra cameras
    if AS1_NUMBER_OF_EXTRA_CAMERAS >0:
        connect_extra= check_ip_connectivity(ip_extra)
    else:
        connect_extra= '0'
    
    
    #Verify modem and signal
    if AS1_BRIDGE_MODE == 0 or AS1_BRIDGE_MODE ==1: # 0 master sem slave / 1 master com slave / 2 e slave
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
    
    # Verify ARD
    if AS1_CAMERA_TYPE == 0:
        Ard = chk_ttyARD()
        if int(Ard) == 0:
            problema=1
            
    else:
        Ard = None
    
    # Verify general health
    current_time2=current_time_pi()#Pega a hora atual
    ig = checking_ignition()#Verifica se a ignição esta ligada
    modee=checking_mode()#Identifica o modo de operação
    total_size,free_size,size = get_machine_storage()#Verifica info do disco
    conncetion_chk = check_internet() # verifica se tem conexão com a internet
    swapa = swap_memory() # Verifica se esta tendo swap de memoria
    cpu = usage_cpu() # % Verifica uso da cpu
    interface_e = chk_ethernet_interface() # Verifica se existe porta ethernet
    interface_wlan = chk_wlan_interface() # Verifica se o wifi esta funcional
    temperature= temp_system() # Verifica temperatura do sistema
    macmac=get_mac() # Verifica o mac adress
    detected,available = check_camera_status()
    if int(available) == 0:
        problema=1
    temperature= temp_system()
    macmac=get_mac()
    network_usage = get_network_usage()
    voltage = check_voltage()
    disk_io = get_disk_io()
    uptime = get_system_uptime()
    #clear_log_file(log_file_path)  # Apaga o conteúdo do arquivo de log ao iniciar
    # current_time = time.strftime('%Y-%m-%d %H:%M:%S')
    
    data = [
        ["counter", counter_id],
        ["Data", current_time2.strip('\n')],
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
        ["Swap_usage", swapa], 
        ["CPU_Usage", cpu], 
        ["ETH0_Interface", interface_e],
        ["WLAN_Interface", interface_wlan],
        ["USB-LTE", Lte],
        ["USB_ARD", Ard], 
        ["Temperature", temperature],
        ["Mac_Adress", macmac.strip()],
        ["Bytes_Sent", network_usage["bytes_sent"]],
        ["Bytes_Received", network_usage["bytes_recv"]],
        ["Voltage", voltage],
        ["Disk_Read_Count", disk_io['read_count']],
        ["Disk_Write_Count", disk_io['write_count']],
        ["Disk_Read_Bytes", disk_io['read_bytes']],
        ["Disk_Write_Bytes", disk_io['write_bytes']],
        ["Disk_Read_Time (ms)", disk_io['read_time']],
        ["Disk_Write_Time (ms)", disk_io['write_time']],
        ["Uptime (ms)", uptime]
    ]
    with open(filename, mode='a', newline='') as file:
   
        if os.stat(filename).st_size == 0:
            fieldnames = []
            for att in data:
                fieldnames.append(att[0])
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()           

        writer = csv.writer(file)
        
        stats = []
        for val in data:
            stats.append(val[1])
        
        writer.writerow(stats)
    incrementar_contador_e_usar()
    
    var = check_error_dmesg()
    if(var >= 0 or problema == 1):
        #sending Json--------------------------------------    
        # json_data= json.dumps(data_jotason)
        # print(json_data)
        # headers = {'Content-Type': 'application/json'}
        # url="https://9a61-131-255-22-153.ngrok-free.app/heartbeat"
        # response = requests.post(url, data=json_data, headers=headers)
        # print(response)
        #----------------------------------------------------
        if(var == 1):
            answer=" General Error in dmesg"
        elif(var == 2):
            answer=" Over-current in dmesg"
        elif(var == 3):
            answer=" Under-voltage in dmesg"
        elif(var == 4):
            answer=" Bad cable in dmesg" # Cannot enable. Maybe the USB cable is bad?
            
        if problems_list:
            tretas = "\n\t".join(problems_list)
            data_str = "\n\t".join([f"{item[0]}: {item[1]}" for item in data])
            send_email_message(vehicle_plate, tretas, filename, data_str, error_message=None)

        #sending csv----------------------------------------
        # url="https://e50e-131-255-23-67.ngrok-free.app/heartbeat"
        # response = send_csv_to_api(filename, url, answer)
        # print(response)
        #----------------------------------------------------
               


if __name__ == '__main__':
#     #daemon = Daemonize(app=daemon_name, pid=f'/tmp/{daemon_name}.pid', action=main)
#     #daemon.start()
    main()

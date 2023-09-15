import time
import socket
#import psutil
import os
import subprocess

#from daemonize import Daemonize

daemon_name = 'chk_status'

def run_bash_command(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    return output.decode(), error.decode()

def capture_first_line(command):
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
        lines= process.stdout.readlines()
        process.terminate()  # Encerra o processo após ler a primeira linha
        if lines:
            first_line = lines[0].strip()
            return first_line
        else:
            return ''
    except Exception as e:
        return f"Erro ao executar o comando: {str(e)}"


def check_internet():
    try:
        # Tente fazer uma conexão com um servidor remoto (por exemplo, o Google)
        socket.create_connection(("www.google.com", 80))
        return True
    except OSError:
        return False

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
    #print('total_size = %s' % total_size)
    #print('free_size = %s' % free_size)
    if total_size<10:
            run_bash_command(command_expand)
            run_bash_command(reboot)
            phrase= 'Expandiu'
    else:
        #phrase= f' total-size: {total_size} free-space: {free_size} '
        #phrase= f'total-size: {total_size}'
        phrase = total_size
    return phrase

def clear_log_file(log_file_path):
    with open(log_file_path, 'w') as file:
        file.write("") 

# def check_disk_space(partition):
#     disk_usage = psutil.disk_usage(partition)
    
#     total_size = disk_usage.total
#     free_space = disk_usage.free
#     used_space = disk_usage.used
    
#     formatted_info = (
#         f"Disk Information for {partition}: "
#         f"Total Size: {total_size / (1024 ** 3):.2f} GB + "
#         f"Used Space: {used_space / (1024 ** 3):.2f} GB + "
#         f"Free Space: {free_space / (1024 ** 3):.2f} GB"
#     )
    
#     return formatted_info

# Exemplo de uso
# partition = '/' Pode ser a partição que desejar
# disk_info = check_disk_space(partition)
# print(disk_info)

def chk_gps():
    gps_command = 'timeout 1 cat /dev/serial0 | grep -ia gsa'
    linha1 = capture_first_line(gps_command)
    linha1 = linha1[:10]
    print(f' info gps: {linha1}')
    if ( linha1 == '$GNGSA,A,3' ):
        return 'GPS ON'
    else:
        return 'GPS OFF'

def chk_camera():
    camera_command = 'pgrep camera'
    result, error=run_bash_command(camera_command)
    if(result != ''):
        return 'Camera On'
    else:
        return 'Camera OFF'


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
            if(size > 10):
                size = 'Expandido'
            if check_internet():
                conncetion_chk =  " Online"
            else:
                conncetion_chk = "Offline"
            file.write(f'{current_time} - Status conexao: {conncetion_chk} - Sd card: {size}  - {status_gps} - {status_camera}\n')
            print('Gerando log...')
            #print(linha1[:10])
        time.sleep(3)


if __name__ == '__main__':
    #daemon = Daemonize(app=daemon_name, pid=f'/tmp/{daemon_name}.pid', action=main)
    #daemon.start()
    main()

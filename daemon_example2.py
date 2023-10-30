import time
import socket
import os
import subprocess

#from daemonize import Daemonize

current_time = time.strftime('%Y-%m-%d %H:%M:%S')
current_time_name=time.strftime('%Y%m%d')
daemon_name = 'chk_status_driver'
caminho_completo = '/tmp/{current_time_name}-{daemon_name}.log'

def run_bash_command(command):
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = process.communicate()
    return output.decode(), error.decode()
#roda comandos no bash do equipamento

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
#roda o bash


def check_internet():
    try: 
        socket.create_connection(("www.google.com", 80))
        return True
    except OSError:
        return False
# Tente fazer uma conexão com um servidor remoto (por exemplo, o Google)

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
#mostra o tamanho do disco

def clear_log_file(log_file_path):
    with open(log_file_path, 'w') as file:
        file.write("")
#apaga os arquivos de log passados 


def chk_gps():
    gps_command = 'timeout 1 cat /dev/serial0 | grep -ia gsa'
    linha1 = capture_first_line(gps_command)
    linha1 = linha1[:10]
    print(f' info gps: {linha1}')
    if ( linha1 == '$GNGSA,A,3' ):
        return 'GPS ON'
    else:
        return 'GPS OFF'
#checa o gps a partir da primeira linha verificado se tiver A,3 tem gps e apresentando algo diferente disso esta sem sinal de gps

def chk_camera():
    camera_command = 'pgrep camera'
    result, error=run_bash_command(camera_command)
    if(result != ''):
        return 'Camera On'
    else:
        return 'Camera OFF'
#Checa se a camera esta funcionando partindo do principio que checa se existe um numero de processo que identifica modulo de camera online

def chk_name_log():
    if os.path.exists(caminho_completo):
        nome_do_arquivo = os.path.basename(caminho_completo)
        print(f'O arquivo {nome_do_arquivo} existe.')
    else:
        print(f'O arquivo {caminho_completo} não existe.')

def main():
    log_file_path = f'/tmp/{current_time_name}-{daemon_name}.log'
    clear_log_file(log_file_path)  # Apaga o conteúdo do arquivo de log ao iniciar
    while True:
        with open(f'/tmp/{current_time_name}-{daemon_name}.log', 'a') as file:
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
            chk_name_log()
        time.sleep(3)


if __name__ == '__main__':
    #daemon = Daemonize(app=daemon_name, pid=f'/tmp/{daemon_name}.pid', action=main)
    #daemon.start()
    main()

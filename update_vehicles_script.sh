#!/bin/bash

# Caminho do arquivo a ser sincronizado
FILE_PATH="/home/phellipe/Downloads/Daemon_chk_analytics/daemon_check_driverV3.py" # modificar o path aonde esta no seu computador
REMOTE_PATH="/home/pi/.health_monitor/"

# Defina as listas de veículos
veiculos_camera_extra=("RQR3A52" "RIP1D52" "RKN4D25" "LTW8H87" "LTY6J39" "RJM4I07" "LVE5J59" "rqr5i94" "RJM5A53")
veiculos_5_cameras=("RVQ4B26" "RTW2B44" "RVN3E40" "RTP7A11")

# Função para sincronizar o arquivo com um veículo específico
sync_veiculo5() {
    local placa="$1"
    local ssh_host="pi@${placa}_externa_ssh.frps.driveranalytics.com.br"
    local ssh_host2="pi@${placa}_interna_ssh.frps.driveranalytics.com.br"
    local ssh_host3="pi@${placa}_extra_ssh.frps.driveranalytics.com.br"
    
    echo "Sincronizando com o veículo: $placa"
    rsync -rcv "$FILE_PATH" "$ssh_host:$REMOTE_PATH"
    rsync -rcv "$FILE_PATH" "$ssh_host2:$REMOTE_PATH"
    rsync -rcv "$FILE_PATH" "$ssh_host3:$REMOTE_PATH"

    if [ $? -eq 0 ]; then
        echo "Sincronização com o veículo $placa concluída com sucesso."
    else
        echo "Erro ao sincronizar com o veículo $placa."
    fi
}

sync_veiculo1(){
    local placa="$1"
    local ssh_host="pi@${placa}_externa_ssh.frps.driveranalytics.com.br"
    local ssh_host2="pi@${placa}_interna_ssh.frps.driveranalytics.com.br"
    
    echo "Sincronizando com o veículo: $placa"
    rsync -rcv "$FILE_PATH" "$ssh_host:$REMOTE_PATH"
    rsync -rcv "$FILE_PATH" "$ssh_host2:$REMOTE_PATH"

    if [ $? -eq 0 ]; then
        echo "Sincronização com o veículo $placa concluída com sucesso."
    else
        echo "Erro ao sincronizar com o veículo $placa."
    fi
}

# Solicita ao usuário a escolha do grupo de veículos
echo "Selecione a opção de atualização:"
echo "1 - Veículos com uma câmera extra"
echo "2 - Veículos com cinco câmeras extras"
echo "3 - um único veiculo"
read -p "Digite o número da opção desejada: " opcao

# Executa a sincronização com base na opção escolhida
case $opcao in
    1)
        echo "Sincronizando veículos com uma câmera extra..."
        for veiculo in "${veiculos_camera_extra[@]}"; do
            sync_veiculo1 "$veiculo"
        done
        ;;
    2)
        echo "Sincronizando veículos com cinco câmeras extras..."
        for veiculo in "${veiculos_5_cameras[@]}"; do
            sync_veiculo5 "$veiculo"
        done
        ;;
    3)
        read -p "Digite a placa do veículo que deseja sincronizar: " placa
        read -p "Digite o número 0 se não tiver camera extra 1 para 1 camera ou 5 para 5 cameras: " cameras
        
        if [ "$cameras" -eq 1 ]; then
            sync_veiculo1 "$placa"
        elif [ "$cameras" -eq 5 ]; then
            sync_veiculo5 "$placa"
        elif [ "$cameras" -eq 0 ]; then
            sync_veiculo1 "$placa"
        else
            echo "Número de câmeras inválido. Saindo do script."
            exit 1
        fi
        ;;
    *)
        echo "Opção inválida. Saindo do script."
        exit 1
        ;;
esac

echo "Sincronização concluída."

HOME_PATH="/home/pi"
HEALTH_MONITOR_PATH=$HOME_PATH"/.health_monitor"

check_udev_rules() {
    if [ -f /etc/udev/rules.d/40-usb-serial.rules ]; then
        if grep -q "ttyMDN" /etc/udev/rules.d/40-usb-serial.rules; then
            echo "ttyMDN* exists"
        else
            echo -e '#info modem \nKERNEL=="ttyUSB*", KERNELS=="1-1.5:1.3", SYMLINK="ttyMDN", MODE="0777"' | sudo tee -a /etc/udev/rules.d/40-usb-serial.rules >> /dev/null
            sudo udevadm control --reload-rules
            if [ $? -eq 0 ]; then
                echo "Regras UDEV recarregadas"
            else
                echo "Erro ao recarregar regras UDEV" >&2
            fi
        fi
    else
        echo "File does not exist"
    fi
}

# check_pyserial() {
#     if python3 -c "import serial" &>/dev/null; then
#         echo "pyserial is already installed."
#     else
#         echo "pyserial is not installed."
#         sudo pip3 install pyserial
#     fi
# }

# check_pip3() {
#     if python3 -c "import pip" &>/dev/null; then
#         echo "pip3 is already installed."
#     else
#         echo "pip3 is not installed."
#         sudo apt-get install python3-pip
#     fi
# }

check_health_daemon_systemd(){
    # [Unit]
    # Description=CHECKING_HEALTH
    # After=network.target
    # StartLimitIntervalSec=60
    # StartLimitBurst=5
    # [Service]
    # Type=simple
    # Restart=always
    # RestartSec=300
    # ExecStart=/usr/bin/sudo /usr/bin/python3 /home/pi/.health_monitor/daemon_check_driver.py
    # StandardOutput=file:/var/log/checking_health.log
    # StandardError=file:/var/log/checking_health.err
    
    # [Install]
    # WantedBy=multi-user.target

    echo "Checando configuração daemon health monitor" #>> $LOG_FILE

    HEALTH_MONITOR_SYSTEMD_FILE_CONFIG_DESIRED_CONTENT="[Unit]\nDescription=CHECKING_HEALTH\nAfter=network.target\nStartLimitIntervalSec=60\nStartLimitBurst=5\n[Service]\nType=simple\nRestart=always\nRestartSec=300\nExecStart=/usr/bin/sudo /usr/bin/python3 /home/pi/.health_monitor/daemon_check_driverV3.py\nStandardOutput=file:/var/log/checking_health.log\nStandardError=file:/var/log/checking_health.err\n\n[Install]\nWantedBy=multi-user.target"

    echo -en $HEALTH_MONITOR_SYSTEMD_FILE_CONFIG_DESIRED_CONTENT #>> $LOG_FILE

    HEALTH_MONITOR_SYSTEMD_FILE_CONFIG_DESIRED_CONTENT_AS_STRING=`echo -en "$HEALTH_MONITOR_SYSTEMD_FILE_CONFIG_DESIRED_CONTENT"`

    healthMonitorSystemdFilePath="/etc/systemd/system/checking_health.service"
    healthMonitorSystemdFilePathAsString="$(<$healthMonitorSystemdFilePath)"

    if [ -f "$healthMonitorSystemdFilePath" ]; then
        healthMonitorSystemdFilePathAsString=$(<$healthMonitorSystemdFilePath)
        if [ "$HEALTH_MONITOR_SYSTEMD_FILE_CONFIG_DESIRED_CONTENT_AS_STRING" == "$healthMonitorSystemdFilePathAsString" ]; then
            echo -e "\nArquivo de $healthMonitorSystemdFilePath está na versão correta" #>> $LOG_FILE
        else
            echo "Atualizando arquivo $healthMonitorSystemdFilePath" #>> $LOG_FILE
            sudo touch $healthMonitorSystemdFilePath
            sudo bash -c "echo -en '$HEALTH_MONITOR_SYSTEMD_FILE_CONFIG_DESIRED_CONTENT' >$healthMonitorSystemdFilePath"
	    	sudo systemctl daemon-reload
	    	sudo systemctl enable checking_health.service
	    	sudo service checking_health restart
        fi
    else
        echo "Criando arquivo $healthMonitorSystemdFilePath" #>> $LOG_FILE
        sudo touch $healthMonitorSystemdFilePath
        sudo bash -c "echo -en '$HEALTH_MONITOR_SYSTEMD_FILE_CONFIG_DESIRED_CONTENT' >$healthMonitorSystemdFilePath"
        sudo systemctl daemon-reload
        sudo systemctl enable checking_health.service
        sudo service checking_health restart
    fi
}

# check_pyserial

check_python_serial(){
    if dpkg -l | grep -q python3-serial; then
        echo "python3-serial is already installed."
    else
        echo "python3-serial is not installed."
        sudo apt-get install python3-serial
    fi
}



check_udev_if_needed(){
    if [ -f $HOME_PATH"/.driver_analytics/mode" ]; then
        if grep -q "BRIDGE_MODE=2" $HOME_PATH"/.driver_analytics/mode"; then
            echo "BRIDGE_MODE=2 exists"
            echo "Não precisa modificar regras UDEV"
        else
            check_udev_rules
        fi
    else
        echo "File does not exist"
    fi
}

check_pip3_installed() {
    if python3 -c "import pip" &>/dev/null; then
        echo "pip3 is already installed."
    else
        echo "pip3 is not installed."
        sudo apt-get update
        sudo apt-get install -y python3-pip
    fi
}

check_psutil_installed(){
    if python3 -c "import psutil" &>/dev/null; then
        echo "psutil is already installed."
    else
        echo "psutil is not installed."
        sudo pip3 install --upgrade psutil
    fi
}


cp_daemon_check_driver(){
    if [ -f $HEALTH_MONITOR_PATH"/daemon_check_driverV3.py" ]; then
        echo "daemon_check_driverV3.py exists"
    else
        if [ -f $HEALTH_MONITOR_PATH]; then
            echo "Folder exists"
        else
            echo "Creating folder"
            mkdir $HEALTH_MONITOR_PATH
        fi
        echo "daemon_check_driverV3.py does not exist"
        sudo cp $HOME_PATH"/daemon_check_driverV3.py" $HEALTH_MONITOR_PATH
    fi
}

ask_user_create_daemon(){
    echo "Deseja criar o daemon de monitoramento de saúde do sistema?"
    echo "1 - Sim"
    echo "2 - Não"
    read -p "Escolha uma opção: " option
    case $option in
        1)
            check_health_daemon_systemd
            ;;
        2)
            echo "Daemon não será criado"
            ;;
        *)
            echo "Opção inválida"
            ;;
    esac
}

check_udev_if_needed

check_python_serial

check_pip3_installed

check_psutil_installed

ask_user_create_daemon

cp_daemon_check_driver

exit 1


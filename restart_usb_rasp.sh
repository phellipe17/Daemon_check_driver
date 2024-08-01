
#Turn off all connections usb on raspberry pi

echo '1-1' | sudo tee /sys/bus/usb/drivers/usb/unbind

echo 'Foi desligado os dispositivos USB'

sleep 5

#turn on all connections usb on raspberry pi

echo '1-1' | sudo tee /sys/bus/usb/drivers/usb/bind

echo 'Foi ligado os dispositivos USB'
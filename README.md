# Daemon_check_driver
Um daemon em python para checar status do equipamento Driver.

A ideia é que o daemon rode quando o equipamento iniciar, antes de se iniciar os processos, ou antes de ser totalmente desligado após checar que a ignição estiver desligada.

Caso queira deixar o daemon rodando é necessário deixar as linhas finais assim:

```
  if __name__ == '__main__':
    daemon = Daemonize(app=daemon_name, pid=f'/tmp/{daemon_name}.pid', action=main)
    daemon.start()
```

Caos queria apensar rodar como um código em python para fazer um diagnóstico imediado é só modificar as ultimas linhas para:

```
if __name__ == '__main__':
  main()
```

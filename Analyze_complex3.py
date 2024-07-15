import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os
from matplotlib.ticker import (MultipleLocator, AutoMinorLocator, FuncFormatter)


def plot_disk_cpu_temp(file_path, interval_minutes):
    # Carregar o arquivo CSV
    df = pd.read_csv(file_path)

    # df['TimeData'] = df['Data'].astype(str) + ' ' + df['timestamp'].astype(str)
    df['TimeData'] = df['timestamp'].astype(str)

    # construindo um counter de zero até o tamanho das leituras do arquivo
    df['Time'] = range(1, df['Time_diff'].size + 1)
        
    df_grouped = df.groupby('Time').agg({
        'Disk_write_mb': 'sum',
        'Disk_read_mb': 'sum',
        'Temperature': 'mean',
        'CPU_Usage(%)': 'mean'
    }).reset_index()

    # Plotar os gráficos
    fig, ax1 = plt.subplots(figsize=(16,9))#tamanho da imagem

    # Função formatadora para os rótulos do eixo X, substituindo apenas a cada 100 valores
    def format_func(value, tick_number):
        index = int(value)
        if 0 <= index < len(df) and index % 100 == 0:  # Substituir rótulos a cada 100 valores
            return df['TimeData'].iloc[index]
        return ''


    color = 'tab:red'
    ax1.set_xlabel('Time')
    ax1.set_ylabel('Disk Write/Read MB', color=color)
    ax1.set_ylim(0, 100)
    ax1.plot(df_grouped['Time'], df_grouped['Disk_write_mb'], color='tab:red', label='Disk Write MB')
    ax1.plot(df_grouped['Time'], df_grouped['Disk_read_mb'], color='tab:blue', label='Disk Read MB')
    ax1.tick_params(axis='y', labelcolor=color)
    

    ax1.xaxis.set_major_locator(MultipleLocator(100))#limitadores do eixo x
    ax1.xaxis.set_minor_locator(MultipleLocator(10))#limitadores de intervalos menores
    ax1.xaxis.set_major_formatter(FuncFormatter(format_func))

    ax1.legend(loc='upper left')

    ax2 = ax1.twinx()
    color = 'tab:green'
    ax2.set_ylabel('Temperature (°C)', color=color)
    ax2.plot(df_grouped['Time'], df_grouped['Temperature'], color=color, label='Temperature (°C)')
    ax2.tick_params(axis='y', labelcolor=color)
    ax2.legend(loc='lower left')

    ax3 = ax1.twinx()
    color = 'tab:orange'
    ax3.set_ylabel('CPU Usage (%)', color=color)
    ax3.plot(df_grouped['Time'], df_grouped['CPU_Usage(%)'], color=color, label='CPU Usage (%)')
    ax3.tick_params(axis='y', labelcolor=color)
    ax3.spines['right'].set_position(('outward', 60))
    ax3.legend(loc='lower right')

    # Adicionar linhas verticais tracejadas para reinicializações
    reboots = df[df['Time_diff'] == 0]
    for i, row in reboots.iterrows():
        plt.axvline(x=row['Time'], color='k', linestyle='--', label='Reboot')

    plt.title('Disk IO, Temperature and CPU Usage Over Time')
    fig.tight_layout()

    # Rotacionar rótulos do eixo X em 45 graus
    plt.xticks(rotation=45)
    
    
    # Salvar o gráfico como imagem
    directory = os.path.dirname(file_path)
    output_file = os.path.join(directory, os.path.basename(file_path).replace('.csv', '_combined_metrics_per_hour.png'))
    plt.savefig(output_file,dpi=300)

    # Mostrar o gráfico
    plt.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Plot disk IO, temperature and CPU usage over time.')
    parser.add_argument('file_path', type=str, help='Path to the CSV file')
    parser.add_argument('--interval', type=int, default=30, help='Interval in minutes for aggregating data')
    args = parser.parse_args()

    plot_disk_cpu_temp(args.file_path, args.interval)

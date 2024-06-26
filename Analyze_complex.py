import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os

def calculate_hourly_metrics(file_path):
    # Carregar o arquivo CSV
    df = pd.read_csv(file_path)

    # Verificar se as colunas necessárias existem
    required_columns = ['Data', 'Disk_write_mb_s', 'Disk_read_mb_s', 'CPU_Usage(%)', 'Temperature']
    for col in required_columns:
        if col not in df.columns:
            print("Colunas disponíveis no DataFrame:")
            print(df.columns)
            raise KeyError(f"'{col}' coluna não encontrada no arquivo CSV.")

    # Converter a coluna 'Data' para datetime com o formato especificado
    df['Data'] = pd.to_datetime(df['Data'], format='%Y/%m/%d %H:%M:%S')

    # Converter as colunas para float
    df['Disk_write_mb_s'] = df['Disk_write_mb_s'].astype(float)
    df['Disk_read_mb_s'] = df['Disk_read_mb_s'].astype(float)
    df['CPU_Usage(%)'] = df['CPU_Usage(%)'].astype(float)
    df['Temperature'] = df['Temperature'].astype(float)

    # Extrair a hora da coluna 'Data'
    df['Hour'] = df['Data'].dt.hour

    # Agrupar por hora e calcular a média dos valores
    hourly_stats = df.groupby('Hour').agg({
        'Disk_write_mb_s': 'mean',
        'Disk_read_mb_s': 'mean',
        'CPU_Usage(%)': 'mean',
        'Temperature': 'mean'
    }).reset_index()

    # Plotar o gráfico combinado
    fig, ax1 = plt.subplots(figsize=(12, 6))

    ax1.set_xlabel('Hora do Dia')
    ax1.set_ylabel('MB/s', color='blue')
    ax1.plot(hourly_stats['Hour'], hourly_stats['Disk_write_mb_s'], label='Escrita (MB/s)', color='blue')
    ax1.plot(hourly_stats['Hour'], hourly_stats['Disk_read_mb_s'], label='Leitura (MB/s)', color='cyan')
    ax1.tick_params(axis='y', labelcolor='blue')

    ax2 = ax1.twinx()
    ax2.set_ylabel('Uso de CPU (%)', color='red')
    ax2.plot(hourly_stats['Hour'], hourly_stats['CPU_Usage(%)'], label='Uso de CPU (%)', color='red')
    ax2.tick_params(axis='y', labelcolor='red')

    # Adicionar o terceiro eixo y para temperatura
    ax3 = ax1.twinx()
    ax3.spines['right'].set_position(('outward', 60))
    ax3.set_ylabel('Temperatura (°C)', color='green')
    ax3.plot(hourly_stats['Hour'], hourly_stats['Temperature'], label='Temperatura (°C)', color='green')
    ax3.tick_params(axis='y', labelcolor='green')

    fig.tight_layout()
    fig.legend(loc='upper left', bbox_to_anchor=(0.1, 0.9))

    # Obter o diretório do arquivo CSV
    directory = os.path.dirname(file_path)
    # Definir o nome do arquivo de saída com o mesmo diretório
    output_file = os.path.join(directory, os.path.basename(file_path).replace('.csv', '_combined_metrics_per_hour.png'))

    # Salvar o gráfico como imagem
    plt.savefig(output_file)

    # Mostrar o gráfico
    plt.show()

    print(f"Gráfico salvo em: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerar gráfico combinado de escrita/leitura, uso de CPU e temperatura por hora do dia a partir de um arquivo CSV")
    parser.add_argument("file_path", type=str, help="Caminho para o arquivo CSV")
    args = parser.parse_args()

    calculate_hourly_metrics(args.file_path)

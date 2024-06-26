import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os

def calculate_hourly_cpu_usage(file_path):
    # Carregar o arquivo CSV
    df = pd.read_csv(file_path)

    # Converter a coluna 'Data' para datetime com o formato especificado
    df['Data'] = pd.to_datetime(df['Data'], format='%Y/%m/%d %H:%M:%S')

    # Converter a coluna 'CPU_Usage' para float
    df['CPU_Usage(%)'] = df['CPU_Usage(%)'].astype(float)

    # Extrair a hora da coluna 'Data'
    df['Hour'] = df['Data'].dt.hour

    # Agrupar por hora e calcular a média do uso da CPU
    hourly_stats = df.groupby('Hour')['CPU_Usage(%)'].mean().reset_index()

    # Plotar o gráfico
    plt.figure(figsize=(12, 6))
    plt.plot(hourly_stats['Hour'], hourly_stats['CPU_Usage(%)'], label='Uso de CPU (%)', color='purple')
    plt.xlabel('Hora do Dia')
    plt.ylabel('Uso de CPU (%)')
    plt.title('Uso de CPU por Hora do Dia')
    plt.legend()
    plt.grid(True)
    plt.xticks(hourly_stats['Hour'])
    plt.tight_layout()

    # Obter o diretório do arquivo CSV
    directory = os.path.dirname(file_path)
    # Definir o nome do arquivo de saída com o mesmo diretório
    output_file = os.path.join(directory, os.path.basename(file_path).replace('.csv', '_cpu_usage_per_hour.png'))

    # Salvar o gráfico como imagem
    plt.savefig(output_file)

    # Mostrar o gráfico
    plt.show()

    print(f"Gráfico salvo em: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerar gráfico de uso de CPU por hora do dia a partir de um arquivo CSV")
    parser.add_argument("file_path", type=str, help="Caminho para o arquivo CSV")
    args = parser.parse_args()

    calculate_hourly_cpu_usage(args.file_path)

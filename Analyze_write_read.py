import pandas as pd
import matplotlib.pyplot as plt
import argparse
import os

def plot_read_write(file_path):
    # Carregar o arquivo CSV
    df = pd.read_csv(file_path)

    # Converter a coluna 'Data' para datetime com o formato especificado
    df['Data'] = pd.to_datetime(df['Data'], format='%Y/%m/%d %H:%M:%S')

    # Extrair a hora da coluna 'Data'
    df['Hour'] = df['Data'].dt.hour

    # Agrupar por hora e somar os valores de leitura e escrita em MB/s
    hourly_stats = df.groupby('Hour')[['Disk_write_mb_s', 'Disk_read_mb_s']].sum().reset_index()

    # Plotar o gráfico
    plt.figure(figsize=(12, 6))
    plt.plot(hourly_stats['Hour'], hourly_stats['Disk_read_mb_s'], label='Leitura (MB/s)', color='blue')
    plt.plot(hourly_stats['Hour'], hourly_stats['Disk_write_mb_s'], label='Escrita (MB/s)', color='red')
    plt.xlabel('Hora do Dia')
    plt.ylabel('MB/s')
    plt.title('Quantidade de Escrita e Leitura por Hora do Dia')
    plt.legend()
    plt.grid(True)
    plt.xticks(hourly_stats['Hour'])
    plt.tight_layout()

    # Obter o diretório do arquivo CSV
    directory = os.path.dirname(file_path)
    # Definir o nome do arquivo de saída com o mesmo diretório
    output_file = os.path.join(directory, os.path.basename(file_path).replace('.csv', '_disk_io_per_hour.png'))

    # Salvar o gráfico como imagem
    plt.savefig(output_file)

    # Mostrar o gráfico
    plt.show()

    print(f"Gráfico salvo em: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerar gráfico de leitura e escrita por hora do dia a partir de um arquivo CSV")
    parser.add_argument("file_path", type=str, help="Caminho para o arquivo CSV")
    args = parser.parse_args()

    plot_read_write(args.file_path)

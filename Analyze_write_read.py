import pandas as pd
import argparse
import os

# Função para calcular as novas colunas
def calculate_io_speed(df):
    # Inicializar as novas colunas com 0
    df['Disk_write_mb_s'] = 0
    df['Disk_read_mb_s'] = 0
    df['Time_diff'] = 0

    for i in range(1, len(df)):
        # Calcular a diferença entre linhas consecutivas para escrita
        write_bytes_diff = df.loc[i, 'Disk_Write_Bytes'] - df.loc[i - 1, 'Disk_Write_Bytes']
        read_bytes_diff = df.loc[i, 'Disk_Read_Bytes'] - df.loc[i - 1, 'Disk_Read_Bytes']
        
        # Converter bytes para megabytes
        write_mb_diff = write_bytes_diff / (1024 * 1024)
        read_mb_diff = read_bytes_diff / (1024 * 1024)
        
        # Calcular a diferença de tempo em segundos
        time_diff = (df.loc[i, 'Uptime (ms)'] - df.loc[i - 1, 'Uptime (ms)']) / 1000
        
        # Calcular a taxa de escrita e leitura em MB/s
        df.loc[i, 'Disk_write_mb_s'] = write_mb_diff / time_diff if time_diff > 0 else 0
        df.loc[i, 'Disk_read_mb_s'] = read_mb_diff / time_diff if time_diff > 0 else 0
        df.loc[i, 'Time_diff'] = time_diff if time_diff > 0 else 0

    return df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcular a taxa de leitura e escrita em MB/s a partir de um arquivo CSV")
    parser.add_argument("file_path", type=str, help="Caminho para o arquivo CSV")
    args = parser.parse_args()

    # Carregar o arquivo CSV
    df = pd.read_csv(args.file_path)

    # Calcular as novas colunas
    df = calculate_io_speed(df)

    # Definir o nome do arquivo de saída
    directory = os.path.dirname(args.file_path)
    base_filename = os.path.basename(args.file_path).replace('.csv', '_updated.csv')
    output_file_path = os.path.join(directory, base_filename)

    # Salvar o resultado em um novo arquivo CSV
    df.to_csv(output_file_path, index=False)

    print(f"Arquivo salvo em: {output_file_path}")

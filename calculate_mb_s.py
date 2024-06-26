import pandas as pd
import argparse
import os

# Função para calcular a quantidade de MB escritos e lidos
def calculate_io_in_mb(df):
    # Inicializar as novas colunas com 0
    df['Disk_write_mb'] = 0
    df['Disk_read_mb'] = 0
    df['Time_diff'] = 0 

    for i in range(1, len(df)):
        # Calcular a diferença entre linhas consecutivas para escrita e leitura
        write_bytes_diff = df.loc[i, 'Disk_Write_Bytes'] - df.loc[i - 1, 'Disk_Write_Bytes']
        read_bytes_diff = df.loc[i, 'Disk_Read_Bytes'] - df.loc[i - 1, 'Disk_Read_Bytes']
        
        # Converter bytes para megabytes
        write_mb_diff = write_bytes_diff / (1024 * 1024)
        read_mb_diff = read_bytes_diff / (1024 * 1024)
        
        # Calcular a diferença de tempo em segundos
        time_diff = (df.loc[i, 'Uptime (ms)'] - df.loc[i - 1, 'Uptime (ms)']) / 1000
        
        # Atualizar as novas colunas
        df.loc[i, 'Disk_write_mb'] = write_mb_diff if write_mb_diff > 0 else 0
        df.loc[i, 'Disk_read_mb'] = read_mb_diff if read_mb_diff > 0 else 0
        df.loc[i, 'Time_diff'] = time_diff if time_diff > 0 else 0

    return df

def process_file(file_path):
    # Carregar o arquivo CSV
    df = pd.read_csv(file_path)

    # Calcular as novas colunas
    df = calculate_io_in_mb(df)

    # Salvar o resultado em um novo arquivo CSV
    output_file_path = file_path.replace('.csv', '_updated.csv')
    df.to_csv(output_file_path, index=False)

    print(f"Arquivo salvo em: {output_file_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcular a quantidade de MB escritos e lidos e adicionar ao arquivo CSV")
    parser.add_argument("file_path", type=str, help="Caminho para o arquivo CSV")
    args = parser.parse_args()

    process_file(args.file_path)

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
        write_bytes_mb = df.loc[i, 'Disk_Write_Bytes_mb'] - df.loc[i - 1, 'Disk_Write_Bytes_mb']
        read_bytes_mb = df.loc[i, 'Disk_Read_Bytes_mb'] - df.loc[i - 1, 'Disk_Read_Bytes_mb']
        
        # Converter bytes para megabytes
        write_mb_mb = write_bytes_mb 
        read_mb_mb = read_bytes_mb
        
        # Calcular a diferença de tempo em segundos
        time_diff = (df.loc[i, 'Uptime(sec)'] - df.loc[i - 1, 'Uptime(sec)'])
        
        # Atualizar as novas colunas
        df.loc[i, 'Disk_write_mb'] = write_mb_mb if write_mb_mb > 0 else 0
        df.loc[i, 'Disk_read_mb'] = read_mb_mb if read_mb_mb > 0 else 0
        df.loc[i, 'Time_diff'] = time_diff if time_diff > 0 else 0

    return df

def process_file(file_path):
    # Carregar o arquivo CSV
    df = pd.read_csv(file_path)

    # Calcular as novas colunas
    df = calculate_io_in_mb(df)

    # Salvar o resultado em um novo arquivo CSV
    output_file_path = file_path.replace('.csv', '_updated.csv')
    df.to_csv(output_file_path, index=False, float_format='%.2f')

    print(f"Arquivo salvo em: {output_file_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcular a quantidade de MB escritos e lidos e adicionar ao arquivo CSV")
    parser.add_argument("file_path", type=str, help="Caminho para o arquivo CSV")
    args = parser.parse_args()

    process_file(args.file_path)

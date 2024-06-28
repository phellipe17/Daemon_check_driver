import psutil
import time

def read_diskstats():
    diskstats_path = '/proc/diskstats'
    with open(diskstats_path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        parts = line.split()
        print(parts)
        print(parts[0])
        print(parts[1])
        print(parts[2])
        print(parts[3])
        print(parts[4])
        print(parts[5])
        print(parts[6])
        print(parts[7])
        print(parts[8])
        print(parts[9])
        print(parts[10])
        
        if 'mmcblk0' in parts or 'sdb' in parts:  # Substitute 'mmcblk0' or 'sda' with your disk identifier
            device = parts[2]
            read_count = int(parts[3])
            write_count = int(parts[7])
            read_sectors = int(parts[5])
            write_sectors = int(parts[9])
            read_time = int(parts[6])
            write_time = int(parts[10])
            sector_size = 512  # Typically 512 bytes per sector
            
            read_bytes = read_sectors * sector_size
            write_bytes = write_sectors * sector_size
            
            read_mb = read_bytes / (1024 * 1024)
            write_mb = write_bytes / (1024 * 1024)
            
            read_mb=round(read_mb, 2)
            write_mb=round(write_mb, 2)

            print(f"Device: {device}")
            print(f"Read Count: {read_count}")
            print(f"Write Count: {write_count}")
            print(f"Read Time: {read_time} ms")
            print(f"Write Time: {write_time} ms")
            print(f"Read MB: {read_mb}")
            print(f"Write MB: {write_mb}")
            print()


psutil.disk_io_counters.cache_clear()
while True:
    # disk_io = psutil.disk_io_counters(nowrap=True, perdisk=True)["sda"]
    # print(disk_io)
    # print()
    read_diskstats()
    time.sleep(1)



    
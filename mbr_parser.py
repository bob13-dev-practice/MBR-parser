import struct
import sys

_PTE_STRUCT = "<1s3s1s3sII"
_EBR_STRUCT = "<446s16s16s16s16s2s"
SECTOR_SIZE = 512
PARTITION_TABLE_OFFSET = 446

PARTITION_TYPES  = {
    "NTFS" : b'\x07',
    "Extend" : b'\x05',
    "FAT32" : [b'\0B', b'\0C']
}

def read_partition_entry(entry):
    partition_table_entry = struct.unpack(_PTE_STRUCT, entry)
    partition_type = partition_table_entry[2]  # 파티션 타입
    start_sector = partition_table_entry[4]  # 시작 주소
    size = partition_table_entry[5]  # 크기

    return partition_type, start_sector, size

def get_filesystem_type(partition_type):
    if partition_type in PARTITION_TYPES["FAT32"]:
        return "FAT32"
    elif partition_type == PARTITION_TYPES["NTFS"]:
        return "NTFS"
    return None

def read_mbr(file_path):
    with open(file_path, 'rb') as f:
        mbr = f.read(SECTOR_SIZE)
        partition_entries = []

        for i in range(4):  # 최대 4개의 파티션 엔트리
            entry = mbr[PARTITION_TABLE_OFFSET + i * 16: PARTITION_TABLE_OFFSET + (i + 1) * 16]
            partition_type, start_sector, size = read_partition_entry(entry)

            fs_type = get_filesystem_type(partition_type)

            if fs_type:
                partition_entries.append((fs_type, start_sector, size))
            elif partition_type == PARTITION_TYPES["Extend"]:
                logical_partitions = read_ebr(file_path, start_sector)
                partition_entries.extend(logical_partitions)

        return partition_entries

def read_ebr(file_path, start_sector):
    logical_partitions = []
    base_sector = start_sector

    with open(file_path, 'rb') as f:
        f.seek(start_sector * SECTOR_SIZE)
        while True:
            ebr = f.read(SECTOR_SIZE)
            if not ebr or len(ebr) < SECTOR_SIZE:
                break

            EBR = struct.unpack(_EBR_STRUCT, ebr)
            partition1 = EBR[1]
            partition2 = EBR[2]

            partition_type, fs_relative_start_sector, size = read_partition_entry(partition1)

            fs_type = get_filesystem_type(partition_type)
            if fs_type:
                fs_start_sector = start_sector + fs_relative_start_sector
                logical_partitions.append((fs_type, fs_start_sector, size))

            next_ebr_relative_start_sector = read_partition_entry(partition2)[1]
            if next_ebr_relative_start_sector == 0:
                break
            
            start_sector = base_sector + next_ebr_relative_start_sector   
            f.seek(start_sector * SECTOR_SIZE)

    return logical_partitions


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 mbr_parser.py <evidence_image>")
        sys.exit(1)

    evidence_image = sys.argv[1]
    partitions = read_mbr(evidence_image)

    for fs_type, start_sector, size in partitions:
        print(f"{fs_type} {start_sector} {size}")


if __name__ == "__main__":
    main()

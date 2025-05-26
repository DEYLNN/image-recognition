import csv

with open('Free_Proxy_List.txt', 'r', encoding='utf-8') as infile, open('proxy_clean.txt', 'w', encoding='utf-8') as outfile:
    reader = csv.DictReader(infile)
    for row in reader:
        ip = row['ip'].replace('"','')
        port = row['port'].replace('"','')
        protocol = row['protocols'].replace('"','')
        # Ambil protokol pertama saja kalau ada koma
        protocol = protocol.split(',')[0]
        proxy_url = f"{protocol}://{ip}:{port}"
        outfile.write(proxy_url + '\n')

print("Sudah jadi! Lihat file proxy_clean.txt")

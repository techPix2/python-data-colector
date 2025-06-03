import os
import platform
import socket
import subprocess
import json
import re
from database import *
so = platform.system().lower()
version = platform.release()

def formatSize(bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024:
            return f"{bytes:.2f}"
        bytes /= 1024
    return f"{bytes:.2f}"

def getMobuId(so):
    try:
        if so == "windows":
            mobuId = subprocess.check_output(["powershell", "-Command",
                                                      "Get-WmiObject Win32_BaseBoard | Select-Object -ExpandProperty SerialNumber"],
                                                     shell=True).decode().strip()
            if not mobuId:
                mobuId = "UUID não encontrado"
        elif so == "linux":
            mobuId = subprocess.check_output("sudo dmidecode -s system-uuid", shell=True).decode().strip()
        else:
            mobuId = "Desconhecido"
        return mobuId
    except Exception as e:
        print(f"Erro ao obter ID da placa-mãe: {str(e)}")
        return None

def getHostname(so):
    try:
        hostname = socket.gethostname()

        if so == 'linux' and not hostname:
            hostname = os.uname().nodename

        elif so == 'windows' and not hostname:
            hostname = os.popen('hostname').read().strip()

        return hostname

    except Exception as e:

        print(f"Erro ao obter hostname: {e}")
        return None

def getMacAddress(system):
    if system == "windows":
        try:
            output = subprocess.check_output(
                "getmac /v /FO list",
                shell=True,
                text=True,
                stderr=subprocess.DEVNULL
            )
            mac_match = re.search(r"([0-9A-F]{2}[:-]){5}([0-9A-F]{2})", output, re.IGNORECASE)
            if mac_match:
                return mac_match.group(0).upper()
        except:
            pass

    elif system == "linux":
        try:
            output = subprocess.check_output(
                "ip link show | grep 'link/ether' | head -n 1",
                shell=True,
                text=True,
                stderr=subprocess.DEVNULL
            )
            mac_match = re.search(r"([0-9a-f]{2}[:]){5}([0-9a-f]{2})", output.lower())
            if mac_match:
                return mac_match.group(0)
        except:
            try:
                output = subprocess.check_output(
                    "ifconfig | grep 'ether' | head -n 1",
                    shell=True,
                    text=True,
                    stderr=subprocess.DEVNULL
                )
                mac_match = re.search(r"([0-9a-f]{2}[:]){5}([0-9a-f]{2})", output.lower())
                if mac_match:
                    return mac_match.group(0)
            except:
                pass

    return None

def getDiscos(so):
    disks_info = []

    if so == "windows":
        try:
            command = "Get-Volume | Where-Object {$_.DriveLetter -ne $null} | Select-Object DriveLetter, Size | ConvertTo-Json"
            result = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True)
            volumes = json.loads(result.stdout)

            if isinstance(volumes, dict):
                volumes = [volumes]

            for vol in volumes:
                disks_info.append({
                    'name': f"{vol['DriveLetter']}:",
                    'type': 'Disk',
                    'description': formatSize(vol['Size'])
                })

        except Exception as e:
            print(f"❌ Erro ao obter discos no Windows: {str(e)}")

    elif so == "linux":
        try:
            command = "lsblk -b -dn -o NAME,SIZE,TYPE -J"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            data = json.loads(result.stdout)
            for device in data.get("blockdevices", []):
                if device['type'] == 'disk':
                    disks_info.append({
                        'name': f"/dev/{device['name']}",
                        'type': 'Disk',
                        'description': formatSize(int(device['size']))
                    })
        except Exception as e:
            print(f"❌ Erro ao obter discos no Linux: {str(e)}")

    return disks_info

def getRam(so):
    try:
        if so == "windows":
            cmd = 'wmic memorychip get capacity'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                total_bytes = sum(int(num) for num in re.findall(r'\d+', result.stdout))
                return formatSize(total_bytes)

        elif so == "linux":
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
                match = re.search(r'MemTotal:\s+(\d+)\s+kB', meminfo)
                if match:
                    return int(match.group(1)) * 1024
    except Exception as e:
        print(f"Erro ao obter RAM")

def getCpu(so):
    try:
        if so == "windows":
            command = 'wmic cpu get name'
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                cpu_name = [line.strip() for line in result.stdout.split('\n') if line.strip()][1]
                return cpu_name
        elif so == "linux":
            command = "cat /proc/cpuinfo | grep 'model name' | uniq | cut -d ':' -f 2 | xargs"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()

    except Exception as e:
        print(f"Erro ao obter informações da CPU: {str(e)}")

    return "Informação não disponível"

def get_system_components(so):
    components = []

    # Discos
    components.extend(getDiscos(so))

    # Memória RAM
    ram_size = getRam(so)
    components.append({
        'name': 'Memoria Ram',
        'type': 'Ram',
        'description': ram_size
    })

    # CPU
    cpu_name = getCpu(so)
    components.append({
        'name': cpu_name,
        'type': 'Cpu',
        'description': None
    })

    return components

def sync_components(fkServer, so):
    try:
        if not fkServer:
            print("❌ ID do servidor inválido para sincronização.")
            return []

        current_components = get_system_components(so)
        print(f"Componentes atuais encontrados: {len(current_components)}")

        current_names = {comp['name'] for comp in current_components}
        component_ids = []

        response = get_componentes(fkServer)
        if "error" in response:
            print(f"Erro ao buscar componentes via API: {response['error']}")
            return []

        db_components = response.get("components") if isinstance(response, dict) else response
        if not isinstance(db_components, list):
            print("❌ Formato inesperado ao listar componentes.")
            return []

        db_name_map = {comp['name']: comp for comp in db_components}

        for current_comp in current_components:
            current_desc = str(current_comp.get('description') or "")

            if current_comp['name'] in db_name_map:
                db_comp = db_name_map[current_comp['name']]
                needs_update = (
                    db_comp['type'] != current_comp['type'] or
                    str(db_comp.get('description') or "") != current_desc
                )

                if needs_update:
                    update_res = atualizar_componente(
                        idComponent=db_comp['idComponent'],
                        type=current_comp['type'],
                        description=current_desc,
                        fkServer=fkServer
                    )
                    if update_res.get("success"):
                        print(f"[ATUALIZADO] Componente: {current_comp['name']}")
                    else:
                        print(f"[ERRO AO ATUALIZAR] {current_comp['name']}: {update_res}")
                component_ids.append(db_comp['idComponent'])

            else:
                register_res = registrar_componente(
                    name=current_comp['name'],
                    type=current_comp['type'],
                    description=current_desc,
                    fkServer=fkServer
                )
                if register_res.get("success"):
                    print(f"[INSERIDO] Novo componente: {current_comp['name']}")
                    inserted_id = register_res.get("idComponent")
                    if inserted_id:
                        component_ids.append(inserted_id)
                else:
                    print(f"[ERRO AO INSERIR] {current_comp['name']}: {register_res}")

        print(f"✅ Sincronização concluída. IDs encontrados: {component_ids}")
        return component_ids if component_ids else []

    except Exception as e:
        print(f"❌ Erro inesperado durante sincronização: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return []

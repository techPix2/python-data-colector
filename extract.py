import time
import os
import psutil
import csv
import requests
from datetime import datetime
from setup import getDiscos
import random
import base64
from database import registrar_processo, buscar_maquina

def cpuData():
    freq = psutil.cpu_freq()
    return {
        'Uso (%)': psutil.cpu_percent(interval=1),
        'Frequência (MHz)': freq.current
    }

def ramData():
    mem = psutil.virtual_memory()
    return {
        'Uso (%)': mem.percent,
        'Usado (GB)': round(mem.used / (1024**3), 2),
        'Disponível (GB)': round(mem.available / (1024**3), 2)
    }

def obter_top_processos_cpu():
    processos = []

    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        try:
            proc.cpu_percent(interval=None)
            processos.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    time.sleep(1)  # Espera para capturar o uso real de CPU

    resultados = []

    for proc in processos:
        try:
            cpu = proc.cpu_percent(interval=None)
            if cpu > 0 and proc.info['name'] != "System Idle Process":
                resultados.append({
                    'pid': proc.info['pid'],
                    'name': proc.info['name'],
                    'cpu_percent': cpu
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    top_processos = sorted(resultados, key=lambda x: x['cpu_percent'], reverse=True)[:10]
    return top_processos

def netData():
    io = psutil.net_io_counters()
    return {
        'Pacotes Enviados': io.packets_sent,
        'Pacotes Recebidos': io.packets_recv
    }

def tempoData():
    boot_time = psutil.boot_time()
    uptime_seconds = time.time() - boot_time
    uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime_seconds))
    return uptime_str

def coletar_dados_disco(path=None):
    # Define a partição padrão, caso não tenha sido passada
    if not path:
        path = 'C:\\' if os.name == 'nt' else '/'

    # Coleta dados completos (bytes usados e %)
    diskUsed, diskPercent = diskData(path)

    # Coleta dados resumidos (partição + uso %)
    resumo = obter_metricas_disco()

    # Dados completos para CSV
    dados_completos = {
        'particao': path,
        'bytes_usados': diskUsed,
        'uso_percentual': diskPercent
    }

    # Dados para envio via POST (mais simples)
    dados_para_post = resumo

    return dados_completos, dados_para_post

def obter_metricas_disco():
    disco_principal = 'C:\\' if os.name == 'nt' else '/'
    uso = psutil.disk_usage(disco_principal)
    return {
        'Partição': disco_principal,
        'Uso (%)': uso.percent
    }

def diskData(path):
    diskUsed = psutil.disk_usage(path).used
    diskPercent = psutil.disk_usage(path).percent
    return diskUsed, diskPercent

def coletar_todas_metricas():
    return {
        'cpu': cpuData(),
        'ram': ramData(),
        'disk': obter_metricas_disco(),
        'network': netData(),
        'top_processos': obter_top_processos_cpu()
    }

def verificar_e_executar_comandos(mobu_id, url_process, fk_company):
    """
    Consulta comandos pendentes para a máquina, executa e registra se forem concluídos com sucesso.
    """
    try:
        url = f"{url_process}/comandos/{mobu_id}"
        response = requests.get(url)

        if response.status_code != 200:
            print(f"[ERRO] Falha ao buscar comandos: {response.status_code}")
            return

        resposta = response.json()
        comandos = resposta.get("comandos", [])

        if not comandos:
            return  # Nenhum comando pendente

        # Buscar o machineId real no banco
        maquina_info = buscar_maquina(mobu_id, fk_company)
        machine_id = maquina_info.get("idServer")

        if not machine_id:
            print("[ERRO] machineId não encontrado para registrar processo.")
            return

        for comando in comandos:
            acao = comando.get("acao")

            if acao == "encerrar_processo":
                pid = comando.get("pid")
                nome = comando.get("nome")
                cpu_percent = comando.get("cpu_percent", 0)

                print("apagando processo", machine_id, cpu_percent, nome)

                if encerrar_processo(pid, nome):
                    registrar_processo(nome, machine_id, cpu_percent)

        # Após executar todos os comandos, envia requisição para limpar
        requests.delete(url)

    except Exception as e:
        print(f"[EXCEÇÃO] Erro ao processar comandos: {e}")

def encerrar_processo(pid, nome=None):
    """
    Encerra o processo com o PID informado, opcionalmente checando o nome.
    Retorna True se o processo foi encerrado com sucesso, False caso contrário.
    """
    try:
        proc = psutil.Process(pid)
        if nome and proc.name().lower() != nome.lower():
            print(f"[IGNORADO] Processo com PID {pid} não é '{nome}', é '{proc.name()}'")
            return False
        proc.terminate()
        proc.wait(timeout=5)
        print(f"[✔️] Processo {pid} ({proc.name()}) encerrado com sucesso.")
        return True
    except psutil.NoSuchProcess:
        print(f"[❌] Processo PID {pid} não encontrado.")
        return False
    except psutil.AccessDenied:
        print(f"[⚠️] Sem permissão para encerrar o processo PID {pid}.")
        return False
    except Exception as e:
        print(f"[ERRO] Falha ao encerrar processo PID {pid}: {e}")
        return False

def criar_issue_jira(titulo, descricao):
    JIRA_DOMAIN = 'techpix.atlassian.net'
    PROJECT_KEY = 'TECH'
    JIRA_EMAIL = 'techpix.sptech@gmail.com'
    JIRA_API_TOKEN = 'ATATT3xFfGF0633uV3Ia8PHiXys7NGu0Q1GEekwjkJRncW4NHaXNpiH4ZrzW5dChG0_XDMvABd-JWlM-eCTy3hIGNXX6ttVeZT8SDc_6_mjAxKTw5ba_n14vbGT5v-tbgwul4zp5duLoyDVQjoAPKf8SMNuV9xS_W_W8-YOtGLxa06v3Iq_vOLU=03A2E16C'

    url = f'https://{JIRA_DOMAIN}/rest/api/2/issue'

    funcionarios_jira = [
        "712020:8349e0d3-1a5a-4456-80e8-2f2f1abe2d7a",
        "712020:ecd4b728-f3d2-421d-b828-c7e5abe5761b",
        "712020:715b3d34-6e3c-4ec1-b564-0b1025cf74d1"
    ]

    escolhido = random.choice(funcionarios_jira)

    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": titulo,
            "description": descricao,
            "issuetype": {"name": "[System] Incident"},
            "priority": {"name": "High"},
            "assignee": {"accountId": escolhido}
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Basic " + base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 201:
            print("[JIRA] Issue criada com sucesso:", response.json()['key'])
        else:
            print("[JIRA] Erro ao criar issue:", response.status_code)
            print(response.text)
    except Exception as e:
        print(f"[JIRA] Exceção ao criar issue: {e}")

def send_file_to_api(file_path, api_url):
    try:
        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file)}
            response = requests.post(api_url, files=files)

        if response.status_code == 200:
            print(f"Arquivo {file_path} enviado com sucesso para a API")
            os.remove(file_path)
            return True
        else:
            print(f"Erro ao enviar arquivo: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Falha ao enviar arquivo {file_path} para a API: {str(e)}")
        return False

def monitorar_e_enviar(companyName, mobuID, api_url_arquivos, api_url_json, so, api_url_process, fkCompany):
    record_count = 0
    current_file = None
    current_process_file = None
    discos = None

    def criar_novos_arquivos():
        nonlocal current_file, current_process_file, discos, record_count

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{companyName}_{mobuID}_{timestamp}.csv"
        process_file = f"{companyName}_{mobuID}_{timestamp}_process.csv"

        discos = getDiscos(so)

        with open(output_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            headers = ['data_hora', 'cpu_freq', 'cpu_percent', 'ram_used', 'ram_percent', 'sendPackages', 'receivePackages']
            for disco in discos:
                path_safe = disco['name'].replace('/', '_').replace('\\', '_').replace(':', '')
                headers.extend([f'disco_{path_safe}_used', f'disco_{path_safe}_percent'])
            writer.writerow(headers)

        with open(process_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['data_hora', 'process_name', 'memory_percent', 'cpu_percent', 'vms'])

        record_count = 0

        print(f"\n📁 Novos arquivos de monitoramento criados:")
        print(f" - {output_file}")
        print(f" - {process_file}")

        return output_file, process_file, discos

    current_file, current_process_file, discos = criar_novos_arquivos()

    while True:
        try:
            metricas = coletar_todas_metricas()

            verificar_e_executar_comandos(mobuID, api_url_process, fkCompany)

            now = datetime.now()
            data_hora = now.strftime('%d/%m/%Y %H:%M:%S')

            cpu_freq = metricas['cpu'].get('Frequência (MHz)', 0)
            cpu_percent = metricas['cpu'].get('Uso (%)', 0)
            ram_percent = metricas['ram'].get('Uso (%)', 0)
            ram_used = metricas['ram'].get('Usado (GB)', 0)
            send_packages = metricas['network'].get('Pacotes Enviados', 0)
            receive_packages = metricas['network'].get('Pacotes Recebidos', 0)

            row = [data_hora, cpu_freq, cpu_percent, ram_used, ram_percent, send_packages, receive_packages]

            for disco in discos:
                try:
                    disk_used, disk_percent = diskData(disco['name'])
                    row.extend([disk_used, disk_percent])
                except Exception as e:
                    print(f"Erro ao acessar disco {disco['name']}: {e}")
                    row.extend([None, None])

            with open(current_file, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(row)

            processes = metricas.get('top_processos', [])
            with open(current_process_file, mode='a', newline='') as file:
                writer = csv.writer(file)
                for proc in processes:
                    writer.writerow([
                        data_hora,
                        proc.get('name', ''),
                        proc.get('memory_percent', 0),
                        proc.get('cpu_percent', 0),
                        proc.get('vms', 0)
                    ])

            if cpu_percent > 80:
                criar_issue_jira(
                    titulo="⚠️ Alerta: CPU acima de 80%",
                    descricao=f"O uso da CPU atingiu {cpu_percent}%."
                )

            if ram_percent > 80:
                criar_issue_jira(
                    titulo="⚠️ Alerta: RAM acima de 80%",
                    descricao=f"O uso de RAM atingiu °{ram_percent}%."
                )

            for disco in discos:
                try:
                    _, percent = diskData(disco['name'])
                    if percent > 90:
                        criar_issue_jira(
                            titulo="⚠️ Alerta: Disco acima de 90%",
                            descricao=f"O uso do disco em {disco['name']} atingiu {percent}%."
                        )
                except Exception as e:
                    print(f"Erro ao verificar uso do disco {disco['name']} para alerta JIRA: {e}")

            payload = {
                "machineId": mobuID,
                "timestamp": now.isoformat(),
                "data": metricas
            }

            try:
                response = requests.post(api_url_json, json=payload)
                if response.status_code == 200:
                    print("✅ Dados JSON enviados com sucesso.")
                else:
                    print(f"❌ Erro ao enviar JSON: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"❌ Erro ao enviar JSON: {e}")

            record_count += 1
            if record_count >= 100:
                print("📤 Enviando arquivos CSV para API...")
                send_file_to_api(current_file, api_url_arquivos)
                send_file_to_api(current_process_file, api_url_arquivos)
                current_file, current_process_file, discos = criar_novos_arquivos()

            time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n⛔ Monitoramento encerrado pelo usuário.")
            send_file_to_api(current_file, api_url_arquivos)
            send_file_to_api(current_process_file, api_url_arquivos)
            break

        except Exception as e:
            print(f"❌ Erro durante monitoramento: {e}")
            time.sleep(0.1)


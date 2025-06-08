import os
import time
from extract import *
from database import *
from setup import *
import platform

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def login():
    clear_screen()
    print("=== TechPix - Autenticação ===")

    while True:
        email = input("\nEmail:")
        senha = input("Senha:")
        resposta = login_maquina(email, senha)

        if resposta.get("companyId"):
            print("\n✅ Login realizado com sucesso.")
            return resposta.get("companyId")
        else:
            print("\nCredenciais inválidas. Tente novamente.")

def register_machine(company_id):
    clear_screen()
    print("=== Validação de Máquina ===")

    hostname = getHostname(so)
    mac_address = getMacAddress(so)
    mobu_id = getMobuId(so)

    print(f"\nDetectamos os seguintes dados da sua máquina:")
    print(f"Hostname: {hostname}")
    print(f"Endereço MAC: {mac_address}")
    print(f"ID da Placa-Mãe: {mobu_id}")

    resposta_busca = buscar_maquina(mobu_id, company_id)
    machine_id = resposta_busca.get("idServer")

    if not machine_id:
        print("\nEsta máquina não está cadastrada no sistema.")
        confirm = input("Deseja cadastrá-la agora? (S/N): ").strip().upper()

        if confirm == 'S':
            resp_cadastro = cadastrar_maquina(hostname, mac_address, mobu_id, company_id)
            if resp_cadastro["status"] != 201:
                print("❌ Falha ao cadastrar a máquina.")
                return None, []
            print("✅ Máquina cadastrada com sucesso!")
            resposta_busca = buscar_maquina(mobu_id, company_id)
            machine_id = resposta_busca.get("idServer")
        else:
            print("⚠️ O cadastro da máquina é necessário para continuar.")
            time.sleep(2)
            return register_machine(company_id)

    componentes_ids = sync_components(machine_id, so)
    print(f"Componentes sincronizados: {componentes_ids}")
    return machine_id, componentes_ids

def main():
    api_url_arquivos = "http://44.208.193.41:5000/s3/raw/upload"
    api_url_json = 'http://44.208.193.41:80/realtime/'
    api_url_process = 'http://44.208.193.41:80/process/'
    so = platform.system().lower()

    try:
        # Login e identificação
        company_id = login()
        company_info = buscar_nome_empresa(company_id)
        company_name = company_info.get('name', 'Empresa Desconhecida') if isinstance(company_info, dict) else 'Empresa Desconhecida'

        print(company_name)
        # Cadastro da máquina (só registra se não existir)
        machine_id, componentes_ids = register_machine(company_id)

        # Sincronizar componentes (CPU, RAM, discos etc.) - COMPARAÇÕES SÃO FEITAS AQUI
        sync_components(machine_id, so)

        # Identificador da máquina para nome de arquivos
        mobu_id = getMobuId(so)

        clear_screen()
        print(f"=== Monitoramento Ativo - {company_name} ===")

        # Iniciar monitoramento e envio
        monitorar_e_enviar(
            companyName=company_name,
            mobuID=mobu_id,
            api_url_arquivos=api_url_arquivos,
            api_url_json=api_url_json,
            so=so,
            api_url_process=api_url_process,
            fkCompany=company_id
        )

    except KeyboardInterrupt:
        print("\nMonitoramento encerrado pelo usuário.")
    except Exception as e:
        print(f"\nErro durante o monitoramento: {str(e)}")
        raise

if __name__ == "__main__":
    main()

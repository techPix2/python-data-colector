import requests

API_URL = "http://44.208.193.41:80/machine"
API_URL_PROCESSO = "http://44.208.193.41:80/process"
def login_maquina(email, password):
    url = f"{API_URL}/login"
    payload = {
        "email": email,
        "password": password
    }

    try:
        response = requests.post(url, json=payload)
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}

print(login_maquina('joao.silva@techpix.com', 'senha123'))

def cadastrar_maquina(hostname, macAddress, mobuId, fkCompany):
    url = f"{API_URL}/register"
    payload = {
        "hostname": hostname,
        "macAddress": macAddress,
        "mobuId": mobuId,
        "fkCompany": fkCompany
    }

    try:
        response = requests.post(url, json=payload)
        return {
            "status": response.status_code,
            "data": response.json()
        }
    except requests.RequestException as e:
        return {"error": str(e)}

def buscar_nome_empresa(companyId):
    url = f"{API_URL}/getCompanyName"
    payload = {
        "companyId": companyId
    }

    try:
        response = requests.post(url, json=payload)
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}

def get_componentes(fkServer):
    url = f"{API_URL}/getComponents/{fkServer}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # força exceção se status != 200
        return response.json()       # parse para JSON
    except requests.RequestException as e:
        return {"error": str(e)}
    except ValueError as ve:
        return {"error": f"Erro ao decodificar JSON: {str(ve)}"}

def atualizar_componente(idComponent, type, description, fkServer):
    url = f"{API_URL}/updateComponent"
    payload = {
        "idComponent": idComponent,
        "type": type,
        "description": description,
        "fkServer": fkServer
    }

    try:
        response = requests.put(url, json=payload)
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}

def registrar_componente(name, type, description, fkServer):
    url = f"{API_URL}/registerComponent"
    payload = {
        "name": name,
        "type": type,
        "description": description,
        "fkServer": fkServer
    }

    try:
        response = requests.post(url, json=payload)
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}

def buscar_maquina(mobuId, fkCompany):
    url = f"{API_URL}/getMachineId"
    payload = {
        "mobuId": mobuId,
        "fkCompany": fkCompany
    }

    try:
        response = requests.post(url, json=payload)
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}

def registrar_processo(nameProcess, machineId, cpu_percent):
    url = f"{API_URL_PROCESSO}/cadastrar"
    payload = {
        "nameProcess": nameProcess,
        "machineId": machineId,
        "cpu_percent": cpu_percent
    }

    print(payload)

    try:
        response = requests.post(url, json=payload)
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}


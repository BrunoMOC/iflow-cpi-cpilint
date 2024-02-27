import requests
from concurrent.futures import ThreadPoolExecutor
from lxml import etree
import subprocess

def get_bearer_token(auth_api_url, client_id, client_secret):
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }
    response = requests.post(auth_api_url, data=data)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print(f"Failed to authenticate. Status code: {response.status_code}")
        return None

def get_package_names(api_url_get_packs, bearer_token):
    headers = {"Authorization": f"Bearer {bearer_token}"}
    response = requests.get(api_url_get_packs, headers=headers)
    if response.status_code == 200:
        root = etree.fromstring(response.content)
        return [entry.text for entry in root.findall('.//d:Id', namespaces={'d': 'http://schemas.microsoft.com/ado/2007/08/dataservices'})]
    else:
        print("Error getting package names")
        return []

def get_iflows_names(package_id, api_url_get_iflow, bearer_token):
    headers = {"Authorization": f"Bearer {bearer_token}"}
    api_endpoint = api_url_get_iflow.format(id=package_id)
    response = requests.get(api_endpoint, headers=headers)
    if response.status_code == 200:
        root = etree.fromstring(response.content)
        return [entry.text for entry in root.findall('.//d:Id', namespaces={'d': 'http://schemas.microsoft.com/ado/2007/08/dataservices'})]
    else:
        print(f"Error getting iflows for package {package_id}")
        return []

def download_zip_file(api_url_download, id_value, version_value, bearer_token):
    api_endpoint = api_url_download.format(id=id_value, version=version_value)
    headers = {"Authorization": f"Bearer {bearer_token}"}
    response = requests.get(api_endpoint, headers=headers)
    if response.status_code == 200:
        with open(f"{id_value}.zip", "wb") as zip_file:
            zip_file.write(response.content)
        print("File downloaded successfully.")
    else:
        print(f"Failed to download file. Status code: {response.status_code}")

def run_cpi_lint(array_iflow_names, rules_xml_path):
    print("CPI LINT FUNCTION")
    for iflow_name in array_iflow_names:
        file_name = iflow_name + '.zip'
        command = f"cpilint -rules {rules_xml_path} -files {file_name}"
        print(command)
        with subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
            stdout, stderr = process.communicate()
            if "Inspecting 1 iflow resulted in 0 issues found." not in stdout:
                with open('output.txt', 'a') as output_file:
                    output_file.write(stdout)
                print(stdout)
            if stderr:
                print(stderr)

if __name__ == "__main__":
    print("Run this code in 'files' folder")
    auth_api_url = input("Enter the authentication API URL: ")
    client_id = input("Enter your client ID: ")
    client_secret = input("Enter your client secret: ")
    prefix_url = input("Enter the prefix for API URLs: ")
    rules_xml_path = input("Enter the path to the rules XML file: ")
    choise = input("Do you wanna run CPILint(Run this code in the folder with the iflows(files))? [y/n]: ")
    api_url_get_packs = prefix_url + "/api/v1/IntegrationPackages"
    api_url_get_iflow = prefix_url + "/api/v1/IntegrationPackages('{id}')/IntegrationDesigntimeArtifacts"
    api_url_download = prefix_url + "/api/v1/IntegrationDesigntimeArtifacts(Id='{id}',Version='{version}')/$value"
    version_value = "active"
    iflow_names_new = []

    bearer_token = get_bearer_token(auth_api_url, client_id, client_secret)

    if bearer_token:
        package_names = get_package_names(api_url_get_packs, bearer_token)
        with ThreadPoolExecutor(max_workers=5) as executor:
            for package_name in package_names:
                iflow_names = get_iflows_names(package_name, api_url_get_iflow, bearer_token)
                iflow_names_new.extend(iflow_names)
                for iflow_name in iflow_names:
                    executor.submit(download_zip_file, api_url_download, iflow_name, version_value, bearer_token)

        if choise == "y":
            run_cpi_lint(iflow_names_new, rules_xml_path)

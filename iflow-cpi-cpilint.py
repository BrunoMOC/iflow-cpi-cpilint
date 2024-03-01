import requests
from concurrent.futures import ThreadPoolExecutor
from lxml import etree
import subprocess
import base64
import time

def get_auth_header(auth_type, client_id, client_secret, s_user=None, password=None, auth_api_url=None):
    if auth_type == "client_credentials":
        data = {"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret}
        response = requests.post(auth_api_url, data=data)
    elif auth_type == "basic":
        credentials = f"{s_user}:{password}"
        credentials_b64 = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        headers = {'Authorization': 'Basic ' + credentials_b64}
        return headers
    if response.status_code == 200:
        return {"Authorization": f"Bearer {response.json().get('access_token')}"}
    else:
        print(f"Failed to authenticate. Status code: {response.status_code}")
        return {}


def get_package_names(api_url_get_packs, headers):
    response = requests.get(api_url_get_packs, headers=headers)
    if response.status_code == 200:
        root = etree.fromstring(response.content)
        return [entry.text for entry in root.findall('.//d:Id', namespaces={'d': 'http://schemas.microsoft.com/ado/2007/08/dataservices'})]
    else:
        print("Error getting package names")
        return []


def get_iflows_names(package_id, api_url_get_iflow, headers):
    api_endpoint = api_url_get_iflow.format(id=package_id)
    response = requests.get(api_endpoint, headers=headers)
    if response.status_code == 200:
        root = etree.fromstring(response.content)
        return [entry.text for entry in root.findall('.//d:Id', namespaces={'d': 'http://schemas.microsoft.com/ado/2007/08/dataservices'})]
    else:
        print(f"Error getting iflows for package {package_id}")
        return []


def download_zip_file(api_url_download, id_value, version_value, headers):
    api_endpoint = api_url_download.format(id=id_value, version=version_value)
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
    start_time = time.time()
    
    print("Run this code in 'files' folder")
    choose = input("Choose 1 to integration suite / Choose 2 to NEO CPI: ")
    if choose == "1":
        auth_type = "client_credentials"
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
        
        headers = get_auth_header(auth_type, client_id, client_secret, auth_api_url=auth_api_url)

        package_names = get_package_names(api_url_get_packs, headers)
        with ThreadPoolExecutor(max_workers=5) as executor:
            for package_name in package_names:
                iflow_names = get_iflows_names(package_name, api_url_get_iflow, headers)
                iflow_names_new.extend(iflow_names)
                for iflow_name in iflow_names:
                    executor.submit(download_zip_file, api_url_download, iflow_name, version_value, headers)

        if choise == "y":
            run_cpi_lint(iflow_names_new, rules_xml_path)

    elif choose == "2":
        auth_type = "basic"
        s_user = input("Enter your S-User: ")
        password = input("Enter your Password: ")
        tenant = input("Enter the Tenant URL: ")
        choise = input("Do you wanna run CPILint(Run this code in the folder with the iflows(files))? [y/n]: ")
        rules_xml_path = input("Enter the path to the rules XML file: ")

        api_url_get_packs = tenant + "/api/v1/IntegrationPackages"
        api_url_get_iflow = tenant + "/api/v1/IntegrationPackages('{id}')/IntegrationDesigntimeArtifacts"
        api_url_download = tenant + "/api/v1/IntegrationDesigntimeArtifacts(Id='{id}',Version='{version}')/$value"
        version_value = "active"
        iflow_names_new = []

        headers = get_auth_header(auth_type, client_id=None, client_secret=None, s_user=s_user, password=password)

        package_names = get_package_names(api_url_get_packs, headers)
        with ThreadPoolExecutor(max_workers=5) as executor:
            for package_name in package_names:
                iflow_names = get_iflows_names(package_name, api_url_get_iflow, headers)
                iflow_names_new.extend(iflow_names)
                for iflow_name in iflow_names:
                    executor.submit(download_zip_file, api_url_download, iflow_name, version_value, headers)

        #print(iflow_names_new)
        if choise == "y":
            run_cpi_lint(iflow_names_new, rules_xml_path)
            
    end_time = time.time()
    
    # Calculate the duration in seconds
    duration_seconds = end_time - start_time
    
    # Convert duration to hours and minutes
    duration_minutes, duration_seconds = divmod(duration_seconds, 60)
    duration_hours, duration_minutes = divmod(duration_minutes, 60)

    # Print start and end times
    print("Started at:", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time)))
    print("Finished at:", time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time)))

    # Print the duration
    print("Duration: %d hours, %d minutes, %d seconds" % (duration_hours, duration_minutes, duration_seconds))
import hashlib
import json
import os
import re
import subprocess
import requests
from datetime import datetime
import yaml

class manifest:
    def __init__(self):
        self.appid = self.get_property('appid')
        self.name = self.get_property('name')
    def get_property(prop):
        #!TODO: return json key:value
        return None

class SteamAppIDManager:
    url = "https://raw.githubusercontent.com/dgibbs64/SteamCMD-AppID-List/main/steamcmd_appid.json"
    cache_file = "steam_appid.json"
    def __init__(self):
        self.url = SteamAppIDManager.url #No reason for this not to be purely static, but here we are now  
        self.cache_file = os.path.join(os.getcwd(), SteamAppIDManager.cache_file)
        self.data = {}
        self._update_cache()

    def _update_cache(self):
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as f:
                raw_data = json.load(f)
                self.data = {str(app["appid"]): app["name"] for app in raw_data["applist"]["apps"]}

            headers = requests.head(self.url).headers
            if 'Last-Modified' in headers:
                last_modified = headers['Last-Modified']
                last_modified_server = datetime.strptime(last_modified, '%a, %d %b %Y %H:%M:%S GMT')
                last_modified_cache = datetime.fromtimestamp(os.path.getmtime(self.cache_file))

                if last_modified_server > last_modified_cache:
                    self._download_file()
        else:
            self._download_file()

    def _download_file(self):
        response = requests.get(self.url)
        data = response.json()

        self.data = {str(app["appid"]): app["name"] for app in data["applist"]["apps"]}

        with open(self.cache_file, 'w') as f:
            json.dump(self.data, f)

    def get_app_name(self, app_id):
        print(self.data)
        return self.data.get(str(app_id)) #str(app_id) & int(app_id) return None

    def get_app_id(self, app_name):
        for app_id, name in self.data.items():
            if name == app_name:
                return int(app_id)
        return None
    
class Muncher:
    LIBRARY_PATH_FILE = "steam_libs.yaml"
    def __init__(self):
        self.drives = self.get_disks()
        self.libaries = self.retrieve_libraries(self.drives)
        # self.manifests = self.load_manifests(self.drives)

    def get_disks(self): 
        '''['C:\\', 'D:\\']'''
        stdout_raw = subprocess.check_output(['fsutil', 'fsinfo', 'drives'])
        std_utf8 = stdout_raw.decode('utf-8')
        system_drives = [item.strip() for item in std_utf8.split() if re.match(r'[A-Za-z]{1}:\\', item) is not None]
        choice = input(f"Select a drive:\n" + 
                       '\n'.join([f'{index}: {item}' for index, item in enumerate(system_drives)]) 
                       + "\nDefault: All mounted drives (Enter)\n")
        if choice == '':
            return system_drives
        elif choice.isdigit():
            return [system_drives[int(choice)]]
        

    def find_libraries(self, drives):
        libraries = {}
        for drive in drives:
            steam_path = os.path.join(drive, 'Program Files (x86)', 'Steam', 'steamapps', 'common')
            if os.path.exists(steam_path):
                libraries[drive] = steam_path
            else:
                for root, dirs, files in os.walk(drive):
                    if 'Steam' in dirs:
                        possible_path = os.path.join(root, 'steamapps', 'common')
                        if os.path.exists(possible_path):
                            libraries[drive] = possible_path
                            break
        with open(self.LIBRARY_PATH_FILE, 'w') as f:
            yaml.dump(libraries, f)
        return libraries

    def retrieve_libraries(self, drives, update=False):
        if update:
            return self.find_libraries(drives)
        elif os.path.exists(self.LIBRARY_PATH_FILE):
            with open(self.LIBRARY_PATH_FILE, 'r') as f:
                return yaml.safe_load(f)
        else:
            return self.find_libraries(drives)
    
    def load_manifests(drives):
        #not implemented yet
        return 0
    
if __name__ == "__main__":
    muncher = Muncher()
    print(muncher.drives)

    steam_app_id_manager = SteamAppIDManager()


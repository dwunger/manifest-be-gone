import hashlib
import json
import os
import re
import subprocess
import requests
from datetime import datetime
import yaml

class SteamAppIDManager:
    #! Not used in production. Appmanifests provide relative install path
    #! May prove useful elsewhere
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
        # print(self.data)
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
        self.libraries = self.retrieve_libraries(self.drives)
        self.unlinked_manifests = self.load_manifests(self.libraries)

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
        libraries = []
        common_paths = [
        '/Program Files (x86)/Steam/steamapps',
        '/Program Files/Steam/steamapps',
        '/SteamLibrary/steamapps',
        '/Games/Steam/steamapps',
        ]
        for drive in drives:
            for common_path in common_paths:
                if os.path.exists(os.path.join(drive, common_path)):
                    libraries.append(os.path.join(drive, common_path)) 
        print(f"Found {len(libraries)} Steam libraries!")
        return libraries

    def retrieve_libraries(self, drives, update=True):
        if update:
            return self.find_libraries(drives)
        elif os.path.exists(self.LIBRARY_PATH_FILE):
            with open(self.LIBRARY_PATH_FILE, 'r') as f:
                return yaml.safe_load(f)
        else:
            return self.find_libraries(drives)
    @staticmethod
    def get_game_dir(manifest_path):
        common_dir = os.path.join(os.path.dirname(manifest_path), 'common')
        with open(manifest_path, 'r') as f:
            lines = f.readlines()
        for line in lines:
            line = line.lstrip()
            if line.startswith("\"installdir\""):
                line = line.removeprefix("\"installdir\"")
                game_dir = line.lstrip().lstrip('\"').rstrip().rstrip('\"')
                break
        return game_dir
    @staticmethod
    def is_unlinked(manifest_path):
        common_dir = os.path.join(os.path.dirname(manifest_path), 'common')
        with open(manifest_path, 'r') as f:
            lines = f.readlines()
        for line in lines:
            line = line.lstrip()
            if line.startswith("\"installdir\""):
                line = line.removeprefix("\"installdir\"")
                game_dir = line.lstrip().lstrip('\"').rstrip().rstrip('\"')
                break
        game_dir = os.path.join(common_dir,game_dir)
        # print(game_dir, not os.path.exists(game_dir))
        return not os.path.exists(game_dir)
    
    def load_manifests(self, libraries):
        manifest_paths = []
        unlinked_manifest_paths = []
        for library in libraries:
            library_manifest_paths = [os.path.join(library, appman) for appman in os.listdir(library) if appman.startswith('appmanifest_') and appman.endswith(".acf")]
            manifest_paths.extend(library_manifest_paths)
        print(f"Found {len(manifest_paths)} app manifests!")
        for manifest_path in manifest_paths:
            if Muncher.is_unlinked(manifest_path):
                unlinked_manifest_paths.append(manifest_path)
        return unlinked_manifest_paths
    
    def remove_manifest_list(self, unlinked_manifests):
        print(f"{len(unlinked_manifests)} unlinked manifest files were found. \n Would you like to review them?")
        choice = input("(Y/n)")
        if choice.lower() in "yes":
            for manifest in unlinked_manifests:
                print(f"{manifest} : ({Muncher.get_game_dir(manifest)})")
        elif choice.lower == "":
            for manifest in unlinked_manifests:
                print(f"{manifest} : ({Muncher.get_game_dir(manifest)})")            
        else:
            print("No.")
            
        print(f"Delete {len(unlinked_manifests)} unlinked manifests?")
        choice = input("(y/N)")
        if choice.lower() in "yes":
            for manifest in unlinked_manifests:
                if os.path.isfile(manifest):
                    os.remove(manifest)
        else:
            print("No changes were made.")

            
    
if __name__ == "__main__":
    muncher = Muncher()
    muncher.remove_manifest_list(muncher.unlinked_manifests)

    # steam_app_id_manager = SteamAppIDManager()


import hashlib
import json
import os
import re
import subprocess
import requests
from datetime import datetime
import yaml
import sys
import ctypes

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
        self.scrap_files = []
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
        print(f"\033[92;1mFound\033[0m \033[1m{len(libraries)}\033[0m \033[92;1mSteam libraries!\033[0m")
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
    def is_ghost_directory(directory):
        '''Bool if directory is < 2KB -> True'''
        #!Some older games may store saves in installation directory.
        #!Threshold is arbitrary, but unlikely to delete these saves at 2KB
        size = 0
        positive_thres = 2 #kb
        if len(os.listdir(directory)) == 0:
            return True
        for dirpath, dirnames, filenames in os.walk(directory):
            for f in filenames:
                if size > positive_thres:
                    return False #early return
                fp = os.path.join(dirpath, f)
                # skip if it is symbolic link
                if not os.path.islink(fp):
                    size += os.path.getsize(fp)/1024
        return size < positive_thres  # bool size is less than 2KB

    @staticmethod
    def get_game_dir(manifest_path):
        '''manifest path -> installation directory'''
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
    
    
    def is_unlinked(self, manifest_path):
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
        if os.path.exists(game_dir):
            if Muncher.is_ghost_directory(game_dir):
                self.scrap_files.extend([game_dir, manifest_path])
        return not os.path.exists(game_dir)
    
    def load_manifests(self, libraries):
        manifest_paths = []
        unlinked_manifest_paths = []
        for library in libraries:
            library_manifest_paths = [os.path.join(library, appman) for appman in os.listdir(library) if appman.startswith('appmanifest_') and appman.endswith(".acf")]
            manifest_paths.extend(library_manifest_paths)
        print(f"\033[92;1mFound\033[0m \033[1m{len(manifest_paths)}\033[0m \033[92;1m app manifests!\033[0m")
        for manifest_path in manifest_paths:
            if self.is_unlinked(manifest_path):
                unlinked_manifest_paths.append(manifest_path)
        return unlinked_manifest_paths
    
    def remove_manifest_list(self, unlinked_manifests):
        if len(unlinked_manifests) > 0:
            print(f"\033[91m{len(unlinked_manifests)} unlinked manifest files were found. Would you like to review them?\033[0m")
            choice = input("\033[1m(Y/n)\033[0m").strip().lower()
            if choice.startswith('y') or choice == "":  
                for manifest in unlinked_manifests:
                    print(f"{manifest} : ({Muncher.get_game_dir(manifest)})")        
            else:
                print("No.")       
            print(f"\033[91mDelete {len(unlinked_manifests)} unlinked manifests?\033[0m")
            choice = input("\033[1m(N/y)\033[0m").strip().lower()
            if choice.startswith('y'):  
                for manifest in unlinked_manifests:
                    if os.path.isfile(manifest):
                        os.remove(manifest)
            else:  
                print("No changes were made.")
        
        elif len(self.scrap_files) > 0:
            print(f"\033[91mSome scraps appear to be remaining from partial uninstallations. View these? (Y/n) Affected files: {len(self.scrap_files)}\033[0m")
            choice = input("\033[1m(Y/n)\033[0m").strip().lower()
            if choice.startswith('y') or choice == "":  
                for idx in range(0, len(self.scrap_files), 2):
                    if idx + 1 < len(self.scrap_files):
                        manifest = os.path.basename(self.scrap_files[idx+1])
                        manifest.strip().removeprefix("appmanifest_").removesuffix(".acf")
                        print(self.scrap_files[idx], '→', manifest)
                    else:
                        print(self.scrap_files[idx]) #scrap files should be in pairs, but print everything to be safe
            choice = input("\033[91mRemove these entries?\033[0m \033[1m(N/y)\033[0m").strip().lower()
            if choice.startswith('y'):  
                count = len(self.scrap_files)
                for scrap_path in self.scrap_files:
                    if os.path.exists(scrap_path):
                        try:
                            os.popen(f'del /F /Q "{scrap_path}"')
                        except Exception as e:
                            print("An error occurred:", str(e))
                print(f"\033[91mRemoved {count} scraps!\033[0m")
            else:  
                print("\033[91mNo changes were made.\033[0m")
        else:
            print("\033[92;1mAll Steam Libraries appear clean!\033[0m")
def enable_ansi_colors():
    if sys.platform.startswith('win'):
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if not is_admin():
        if sys.platform.startswith('win'):
            try:
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
                sys.exit(0)
            except Exception as e:
                print("Failed to elevate process:", e)
                sys.exit(1)
        else:
            print("Elevation is only supported on Windows.")
    else:
        print("Already running as admin.")
            
    
if __name__ == "__main__":
    run_as_admin()
    enable_ansi_colors()
    muncher = Muncher()
    muncher.remove_manifest_list(muncher.unlinked_manifests)
    input()

    # steam_app_id_manager = SteamAppIDManager()


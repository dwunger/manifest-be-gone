import os
import subprocess
import re





class manifest(self, id, name, ):


class Muncher(self):
    def __init__(self, manifests, drives):
        self.manifests = load_manifests(drives)
        self.drives = get_disks()
    def get_disks(): 
        '''['C:\\', 'D:\\']'''
        stdout_raw = subprocess.check_output(['fsutil', 'fsinfo', 'drives'])
        std_utf8 = stdout_raw.decode('utf-8')
        system_drives = [item.strip() for item in system_drives.split() if re.match(r'[A-Za-z]{1}:\\', item) is not None]
        choice = input(f"Select a drive:\n{[f'{idx - 1}: {drive}' for idx, drive in enumerate(system_drives)]}\nDefault: All mounted drives (Enter)\n")
        if choice == '':
            return system_drives
        else:
            if choice.isdigit():
                return system_drives[choice]
    
    def load_manifests(self.drives):
        pass
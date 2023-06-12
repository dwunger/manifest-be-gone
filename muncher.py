import os
import subprocess
import re
out = subprocess.check_output(['fsutil', 'fsinfo', 'drives'])
out = out.decode('utf-8')
out = [item.strip() for item in out.split() if re.match(r'[A-Za-z]{1}:\\', item) is not None]
print(out)





# class manifest(self, id, name, ):


# class Muncher(self):
#     def __init__(self, manifests, drives)
#         self.manifests = load_manifests(drives)
#     def load_manifests(drives)
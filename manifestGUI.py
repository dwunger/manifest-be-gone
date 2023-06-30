import os, re, subprocess, requests, yaml, sys, ctypes
from PyQt5.QtWidgets import QApplication, QMainWindow, QListWidget, QPushButton, QComboBox, QVBoxLayout, QWidget, QMessageBox
from PyQt5.QtCore import Qt
from datetime import datetime

class Muncher:
    LIBRARY_PATH_FILE = "steam_libs.yaml"
    def __init__(self):
        self.scrap_files = []
        self.drives = self.get_disks()
        self.libraries = self.retrieve_libraries(self.drives)
        self.unlinked_manifests = self.load_manifests(self.libraries)
        
    def get_disks(self): 
        stdout_raw = subprocess.check_output(['fsutil', 'fsinfo', 'drives'])
        std_utf8 = stdout_raw.decode('utf-8')
        system_drives = [item.strip() for item in std_utf8.split() if re.match(r'[A-Za-z]{1}:\\', item) is not None]
        return system_drives

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
        removed_manifests = []
        removed_scraps = []
        
        if len(unlinked_manifests) > 0:
            for manifest in unlinked_manifests:
                if os.path.isfile(manifest):
                    os.remove(manifest)
                    removed_manifests.append(manifest)
        return removed_manifests, removed_scraps
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
            
from PyQt5.QtWidgets import QApplication, QMainWindow, QListWidget, QPushButton, QComboBox, QVBoxLayout, QWidget, QMessageBox, QLabel
from PyQt5.QtCore import Qt

class SteamMuncherGUI(QMainWindow):
    def __init__(self, muncher):
        super().__init__()
        self.muncher = muncher
        self.initUI()

    def initUI(self):
        self.setGeometry(200, 200, 600, 400)
        self.setWindowTitle('Steam Muncher')

        main_widget = QWidget(self)
        self.setCentralWidget(main_widget)

        layout = QVBoxLayout()

        self.disk_select_combo = QComboBox(self)
        self.disk_select_combo.addItem("All")
        self.disk_select_combo.addItems(self.muncher.drives)
        self.disk_select_combo.currentTextChanged.connect(self.update_manifest_list)

        self.manifest_list_label = QLabel("Unlinked Manifests", self)  # New label to describe the widget

        self.manifest_list_widget = QListWidget(self)
        self.update_manifest_list()

        self.remove_button = QPushButton('Remove', self)
        self.remove_button.clicked.connect(self.remove_selected_manifests)

        self.remove_all_button = QPushButton('Remove All', self)  # New button to remove all
        self.remove_all_button.clicked.connect(self.remove_all_manifests)

        layout.addWidget(self.disk_select_combo)
        layout.addWidget(self.manifest_list_label)  # Adding label to layout
        layout.addWidget(self.manifest_list_widget)
        layout.addWidget(self.remove_button)
        layout.addWidget(self.remove_all_button)  # Adding button to layout

        main_widget.setLayout(layout)

    def update_manifest_list(self):
        self.manifest_list_widget.clear()
        disk = self.disk_select_combo.currentText()
        if disk == "All":
            self.manifest_list_widget.addItems(self.muncher.unlinked_manifests)
        else:
            self.manifest_list_widget.addItems([manifest for manifest in self.muncher.unlinked_manifests if manifest.startswith(disk)])

    def remove_selected_manifests(self):
        selected_manifests = [item.text() for item in self.manifest_list_widget.selectedItems()]
        if selected_manifests:
            confirmation_box = QMessageBox.question(self, 'Confirmation',
                                                    'Are you sure you want to delete the selected manifests?',
                                                    QMessageBox.Yes | QMessageBox.No)
            if confirmation_box == QMessageBox.Yes:
                removed_manifests, _ = self.muncher.remove_manifest_list(selected_manifests)
                for manifest in removed_manifests:
                    item = self.manifest_list_widget.findItems(manifest, Qt.MatchExactly)
                    if item:
                        self.manifest_list_widget.takeItem(self.manifest_list_widget.row(item[0]))

    def remove_all_manifests(self):  # New function to remove all manifests
        all_manifests = [self.manifest_list_widget.item(i).text() for i in range(self.manifest_list_widget.count())]
        if all_manifests:
            confirmation_box = QMessageBox.question(self, 'Confirmation',
                                                    'Are you sure you want to delete all manifests?',
                                                    QMessageBox.Yes | QMessageBox.No)
            if confirmation_box == QMessageBox.Yes:
                removed_manifests, _ = self.muncher.remove_manifest_list(all_manifests)
                for manifest in removed_manifests:
                    item = self.manifest_list_widget.findItems(manifest, Qt.MatchExactly)
                    if item:
                        self.manifest_list_widget.takeItem(self.manifest_list_widget.row(item[0]))

def main():
    # run_as_admin()
    # enable_ansi_colors()
    muncher = Muncher()
    
    app = QApplication(sys.argv)
    gui = SteamMuncherGUI(muncher)
    gui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()


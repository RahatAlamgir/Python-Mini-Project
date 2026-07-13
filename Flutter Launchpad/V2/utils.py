import os
import stat
import subprocess
import getpass

CONFIG_FILE = "config.json"

def onerror(func, path, exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        try:
            subprocess.run(["attrib", "-R", "-H", "-S", path], capture_output=True, shell=True)
            func(path)
        except Exception:
            pass

def get_git_username():
    try:
        result = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, shell=True)
        username = result.stdout.strip()
        if not username:
            result_email = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True, shell=True)
            email = result_email.stdout.strip()
            if email and "@" in email:
                return email.split("@")[0]
        return username if username else getpass.getuser()
    except Exception:
        try:
            return getpass.getuser()
        except Exception:
            return "PC User"
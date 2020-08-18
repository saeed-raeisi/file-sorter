import platform


os_linux="linux"
os_windows="windows"



# ------------------------------------------------ detect operator system
def os_recognizer():
    os_name = platform.system()
    address = ""
    if os_name == "Linux":
        return os_linux
    elif os_name == "Windows":
        return os_windows


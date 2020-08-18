import os, fnmatch, sys
from pathlib import Path
import time, threading
import pyautogui, shutil


# find root dir
def set_root(list):
    for item in list:
        if (item != "timeshit" and item != "lost+found"):
            find = item
    return find


# sort by last char
def last_1chars(x):
    return (x[-1:])


# get file
def get_file(path):
    for files in os.listdir(path):
        if os.path.isfile(os.path.join(path, files)):
            print(files)


# find file name
def find_name(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                # result.append(os.path.join(root, name))
                result.append(name)
    return result


# find files
def find(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root, name))
                # result.append(name)
    return result


# get file size
def get_file_size_in_bytes(file_path):
    size = os.path.getsize(file_path)
    return size


# create directory
def create_dir(path, list_format):
    paths = []
    for item in list_format:
        paths.append(item[1:])
    for item in paths:
        try:
            temp = path + "/" + item
            # print(temp)
            if not os.path.exists(temp):
                # os.mkdir(temp,mode=0o777, dir_fd=None)
                oldmask = os.umask(000)
                os.makedirs(temp, 0o777)
                os.umask(oldmask)
        except OSError as error:
            print(error)
    for item1 in paths:
        temp = "*.%s" % item1
        list_file = find(temp, path)
        list_file_name = find_name(temp, path)
        i2 = 0
        # print(list_file)
        for item2 in list_file:
            oldmask = os.umask(000)
            try:
                source = item2
                destination = path + "/" + item1
                new_path = shutil.move(source, destination)
            except OSError as error:
                for i in list_file:
                    time.sleep(0.01)
                    print('\r %s' % error, end="", flush=True)
                temp = destination + "/" + list_file_name[i2]
                # print(temp)
                os.replace(source, temp)
                i2 += 1
            os.umask(oldmask)


# get file suffix
def get_suffix(path):
    result = []
    for item in path:
        result.append(Path(item).suffix)
    return result


# get file suffixes
def get_suffixes(path):
    result = []
    for item in path:
        result.append(Path(item).suffixes)
    return result


# sort size

# sort format

# sort name

# create test file
def test_file(path):
    for i in range(1, 6):
        oldmask = os.umask(000)
        file = open(path + "/file%d.txt" % i, "w")
        file.write("Your text goes here%d" % i)
        file.close()

        file = open(path + "/code%d.py" % i, "w")
        file.write("Your text goes here%d" % i)
        file.close()

        file = open(path + "/code%d.jl" % i, "w")
        file.write("Your text goes here%d" % i)
        file.close()

        file = open(path + "/code%d.cpp" % i, "w")
        file.write("Your text goes here%d" % i)
        file.close()

        os.umask(oldmask)


# menu
def menu(a):
    switcher = {
        0: {
            # pyautogui.hotkey('ctrl', 'l'),
            print("hi"),
            # Sleep(2),
            print("hi"),
            # sleep(2),
            print("hi"),
        },
        1: {
            # clear = lambda: os.system('clear') , # on Linux System
            # clear(),
        },
        2: "two",
    }
    return switcher.get(a, "nothing")


####################################################### welcome
try:
    file_list = os.listdir("/home")
    root = set_root(file_list)
    dir_path = "/home/" + root + "/test_sort"
    if not os.path.exists(dir_path):
        # os.mkdir(temp,mode=0o777, dir_fd=None)
        oldmask = os.umask(000)
        os.makedirs(dir_path, 0o777)
        os.umask(oldmask)
    file_list = os.listdir("/home/" + root + "/test_sort")
    sorted(file_list, key=last_1chars)

    # print(file_list)
    # print(root)
    # print(sorted(file_list, key = last_1chars))

    dir_path = "/home/" + root + "/test_sort"
    test_file(dir_path)
    list_file = find("*.*", "/home/" + root + "/test_sort")
    list_format = get_suffix(list_file)
    final_new_menu = list(set(list_format))
    #  or  mylist = list(dict.fromkeys(mylist))
    print(final_new_menu)
    create_dir(dir_path, final_new_menu)
    for i1 in final_new_menu:
        for i in range(101):
            time.sleep(0.01)
            print('\rcomplete--- [%d%%] %s' % (i, i1), end="", flush=True)
    print()
    # for item in find("*.*", "/home/"+root+"/test_sort"):
    #     print(item)
    # for item in get_suffix(find("*.*", "/home/"+root+"/test_sort")):
    #     print(item)
except:
    print(":(")
######################################################### Goodbye
# main
if __name__ == "__main__":
    print("--------Hello, we are here to help you sort your files----------")
    print()
    print("......-1) sort by size ")
    print("......-2) sort by format ")
    print("......-3) sort by name ")
    print()
    # while True:
    # x=input("Choose an operation: ")
    # menu(int(x))

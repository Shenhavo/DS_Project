# Autonomous Drones Laboratory - TAU
# by Dan Blanaru & Shenhav Ovadia

from py_files import global_consts
from py_files import csv_mngr
import os

def main():
    try:
        csv = csv_mngr.CsvMngr(global_consts.CONFIG_FILE_PATH)

        print("Hola Mundo")
    except Exception as e:
        print(e)


    # dir_path = os.path.dirname(os.path.realpath(__file__))
    # print(dir_path)
    print("Hola Mundo")


if __name__ == "__main__":
    main()

# import numpy

MAIN_WIFI_M2M_BUFFER_SIZE = 1460

# creates array 0,1,2,...256, 0,1,2...256 with 1460 elements

def main():
    str = '={'
    for index in range(1460):
        str = str + hex(index % 256) + ', '
    str = str[0:-2]
    str = str + '};'
    print(str)
if __name__ == "__main__":
    main()
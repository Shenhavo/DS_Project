
import socket, time
import numpy as n
from datetime import datetime


MAIN_WIFI_M2M_BUFFER_SIZE   =   1024
NEW_FRAME_DATA_SIZE_B       =   1017
MID_FRAME_DATA_SIZE_B       =   1023
HOST = '192.168.1.1'  # Standard loopback interface address (localhost)
PORT = 6666  # Port to listen on (non-privileged ports are > 1023)
NEW_FRAME_SOF               =	33 # '!'
MID_FRAME_SOF	            =   65 # 'A'
IMU_SOF			            =   105# 'i'
GLOBAL_VERBOSITY            =   0


def main():
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    prnt(("date and time ="+ dt_string),0)

    pm  = PacketMngr(HOST, PORT)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        pm.add_socket(s)
        pm.socket.connect((pm.host, pm.port))

        print("Are you ready to start? y/n\r\n")
        user_intput = input()

        if( user_intput == 'y'):
            s.sendall(b'Start\r\n')

            while True:

                incoming_data = s.recv(MAIN_WIFI_M2M_BUFFER_SIZE)#pm.rx_bytes_to_read)
                print(incoming_data)
                if pm.mode == 0: # case idle state
                    if incoming_data[0] == NEW_FRAME_SOF:

                        pm.frame_size   =   TwoBytesToUint16(incoming_data, 1)

                        if pm.frame_size > NEW_FRAME_DATA_SIZE_B:
                            pm.sys_tick = FourBytesToUint32(incoming_data, 3)
                            pm.mode = 1
                            pm.rx_buff = incoming_data[7:]
                            pm.print_buff_len()
                            pm.frame_size = pm.frame_size - NEW_FRAME_DATA_SIZE_B
                            if pm.frame_size >= MID_FRAME_DATA_SIZE_B:
                                pm.rx_bytes_to_read = MID_FRAME_DATA_SIZE_B
                            else:
                                pm.rx_bytes_to_read = pm.frame_size
                            pm.expected_num_of_packets = 1 + n.ceil((pm.frame_size)/MID_FRAME_DATA_SIZE_B)
                            pm.frame_ctr = pm.frame_ctr + 1
                            prnt("Img " + str(pm.frame_ctr) + "/" + str(pm.expected_num_of_packets),0)

                        else:
                            ErrorHandler("an image less than 1kB size has arrived")
                    elif incoming_data[0] == MID_FRAME_SOF:
                        prnt(incoming_data, 0)
                        ErrorHandler("mid frame received first!")
                    elif incoming_data[0] == IMU_SOF:
                        pm.mode = 2
                        prnt("TO BE CONTINUED", 0)
                else:
                    if pm.mode == 1: # case image mode
                        tmp = incoming_data[1:]
                        pm.rx_buff = pm.rx_buff + tmp
                        pm.print_buff_len()
                        pm.frame_ctr = pm.frame_ctr + 1
                        prnt("Img " + str(pm.frame_ctr) + "/" + str(pm.expected_num_of_packets), 0)

                        if pm.frame_size > MID_FRAME_DATA_SIZE_B: # means that there will be an additional packet
                            pm.frame_size = pm.frame_size - MID_FRAME_DATA_SIZE_B
                            if pm.frame_size >= MID_FRAME_DATA_SIZE_B:
                                pm.rx_bytes_to_read = MID_FRAME_DATA_SIZE_B
                            else:
                                pm.rx_bytes_to_read = pm.frame_size
                        else: # means this is the last packet
                            prnt("image size =", 0)
                            pm.print_buff_len()
                            prnt(("systick = " + str(pm.sys_tick)),0)
                            pm.ptr_jpeg = open("outputs\output_file"+str(pm.sys_tick)+now.strftime("_%M_%S_%f")+".jpeg", 'w+b')
                            pm.ptr_jpeg.write(pm.rx_buff)
                            pm.ptr_jpeg.close()
                            # ===== cleaning:  ======
                            pm.clear_frame_properties()
                            pm.rx_bytes_to_read = MAIN_WIFI_M2M_BUFFER_SIZE # TODO: IMPORTANT TO CHANGE WHEN IMU IS IMPLEMENTED
                    elif pm.mode == 2: # case IMU mode
                        prnt("TO BE CONTINUED", 0)

        else:
            prnt("bye bye..\r\n")
            input()
            exit(1)

def TwoBytesToUint16 (a_byte_arr, a_shift = 0):
    return int(a_byte_arr[a_shift+0]) + int(a_byte_arr[a_shift+1])*256

def FourBytesToUint32 (a_byte_arr, a_shift):
    return int(a_byte_arr[a_shift+0]) + int(a_byte_arr[a_shift+1])*256 + int(a_byte_arr[a_shift+2])*65536 + int(a_byte_arr[a_shift+3])*16777216

def ErrorHandler(a_string = ""):
    print("Fatal Error:")
    print(a_string)
    y = input()
    exit(1)

def WarningHandler(a_string = ""):
    print("Warning:")
    print(a_string)

def prnt(a_string ="", a_verbosity = 10000):
    if(a_verbosity >= GLOBAL_VERBOSITY):
        print(a_string)

class PacketMngr:
    'Common base class for all employees'
    counter = 0

    def __init__(self, a_host, a_port):
        self.host   = a_host
        self.port   = a_port
        self.socket = None
        self.rx_buff = None
        self.rx_bytes_to_read   =   MAIN_WIFI_M2M_BUFFER_SIZE # might be problematic if there will be am image less than 1kB size
        self.packet_ctr =   0
        self.sys_tick   =   0
        self.frame_size =   0
        self.frame_ctr  =   0
        self.expected_num_of_packets = 0
        self.ptr_jpeg   = None
        self.mode       =   0 # 0 = off, 1 = Image, 2 = IMU
    def add_socket(self, a_socket):
        self.socket =   a_socket

    def save_jpeg(self):
        print("saved")

    def clear_frame_properties(self):
        self.packet_ctr =   0
        self.sys_tick   =   0
        self.frame_size =   0
        self.frame_ctr  =   0
        self.expected_num_of_packets = 0
        self.ptr_jpeg   = None
        self.mode       =   0 # 0 = off, 1 = Image, 2 = IMU

    def print_buff_len(self):
        print("bytes to read: " + str(self.rx_bytes_to_read))
        try:
            print("buff len: " + str(len(self.rx_buff)))
        except:
            print("buff len: 0")

if __name__ == "__main__":
    main()



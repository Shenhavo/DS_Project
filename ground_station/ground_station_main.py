
import socket
from datetime import datetime
import os
import subprocess
import time
import numpy as np
import cv2
import threading
import matplotlib.pyplot as plt

GLOBAL_VERBOSITY            =   0

MAIN_WIFI_M2M_BUFFER_SIZE   =   1024
FRAME_DATA_SIZE_B           =   1017
FRAME_HEADER_WO_SOF_SIZE_B  =   6
FRAME_HEADER_SIZE_B         =   7
IMU_PACkET_SIZE_B           =   125
SOF_SIZE_B                  =   1
IMU_PACKET_SIZE_WO_HEADER   =   IMU_PACkET_SIZE_B - SOF_SIZE_B

HOST = '192.168.1.1'  # Standard loopback interface address (localhost)
PORT = 6666  # Port to listen on (non-privileged ports are > 1023)
FRAME_SOF                   =	33 # '!'
IMU_SOF			            =   105# 'i'

IMU_SYSTICK_SHIFT_MSEC      =   50
IMU_CALLS_PER_PACKET        =   10
IMU_SOF_SIZE_B              =   1
SYSTICK_SIZE_B              =   4
IMU_DATA_SHIFT_SIZE_B       =   SYSTICK_SIZE_B
IMU_PARAMETER_SIZE_B        =   2
IMU_PARAMETERS_PER_CALL     =   6
IMU_CALL_SIZE_B             =   IMU_PARAMETER_SIZE_B*IMU_PARAMETERS_PER_CALL
GYRO_X_SHIFT                =   0
GYRO_Y_SHIFT                =   2
GYRO_Z_SHIFT                =   4
ACC_X_SHIFT                 =   6
ACC_Y_SHIFT                 =   8
ACC_Z_SHIFT                 =   10

IMG_H                       = 240
IMG_W                       = 320
IMG_H_CROP                  = 16

TARGET_START_SEND_CMD       = b'Start\r\n'

SSID = 'WINC1500_AP'

ERR_IMG_PATH = r"err.jpg"


def main():
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    prnt(("date and time = " + dt_string), 0)
    # define the name of the directory to be created
    path = r"outputs\\" + now.strftime("%d%m%Y-%H%M%S")

    try:
        os.mkdir(path)
    except OSError:
        print ("directory creation %s failed" % path)
    else:
        print ("created  directory %s " % path)

    # this section is tested with WIN10
    try:
        cmd = "netsh wlan connect name={0} ssid={0}".format(SSID)
        k = subprocess.run(cmd, capture_output=True, text=True).stdout
        # print("connection succeed: " + k)
        time.sleep(2)
        cmd = "netsh wlan show interfaces"
        k = subprocess.run(cmd, capture_output=True, text=True).stdout
        connection_result = k.find(SSID)
        if connection_result > 0:
            print("connected")
        else:
            print("NOT connected")
    except:
        print("could not connect AP: " + k)

    pm = PacketMngr(HOST, PORT)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        pm.add_socket(s)
        pm.socket.connect((pm.host, pm.port))

        # print("Are you ready to start? y/n\r\n")
        # user_intput = input()
        #
        # if( user_intput == 'y'):
        s.sendall(TARGET_START_SEND_CMD)

        display_img_thread = threading.Thread(target=pm.display_img)
        display_img_thread.setDaemon(True)
        display_img_thread.start()

        # display_imu_thread = threading.Thread(target=pm.display_imu)
        # display_imu_thread.setDaemon(True)
        # display_imu_thread.start()

        acc_x_values = []
        acc_y_values = []
        acc_z_values = []
        #
        # imu_plt = plt.plot(0, acc_x_values)
        # plt.show()

        while True:
            incoming_data = s.recv(SOF_SIZE_B)
            print("SOF="+str(incoming_data))
            if incoming_data[0] == FRAME_SOF:
                incoming_data = s.recv(FRAME_HEADER_WO_SOF_SIZE_B)
                incoming_sys_tick = FourBytesToUint32(incoming_data, 0)
                print("tick=" + str(incoming_sys_tick))
                if pm.frame_sys_tick == 0 or pm.frame_sys_tick == incoming_sys_tick:
                    pm.frame_sys_tick = incoming_sys_tick
                else:
                    print("invalid systick arrived")# TODO: see if it handles missing property
                    pm.clear_frame_properties()
                    continue
                pm.frame_size = TwoBytesToUint16(incoming_data, 4)
                if pm.frame_size > FRAME_DATA_SIZE_B:  # means that there will be an additional packet
                    if pm.frame_rx_buff == bytes(0):
                        pm.frame_rx_buff = s.recv(FRAME_DATA_SIZE_B)
                    else:
                        pm.frame_rx_buff = pm.frame_rx_buff + s.recv(FRAME_DATA_SIZE_B)

                else: # means this is the last packet
                    try:
                        pm.frame_rx_buff = pm.frame_rx_buff + s.recv(pm.frame_size)# - FRAME_HEADER_SIZE_B)
                    except:
                        expected_frame_size = pm.frame_size - FRAME_HEADER_SIZE_B
                        print("bad recv size: %d" % expected_frame_size)
                    else:
                        print("frame recv size: %d" % len(pm.frame_rx_buff))
                        pm.save_jpeg(path)
                        delta_tick = pm.frame_sys_tick - pm.last_valid_frame_sys_tick
                        print("sys_tick diff = %d [msec]" % delta_tick)
                        pm.last_valid_frame_sys_tick = pm.frame_sys_tick
                    # ===== cleaning:  ======
                    pm.clear_frame_properties()

            elif incoming_data[0] == IMU_SOF:
                pm.imu_rx_buff = s.recv(IMU_PACKET_SIZE_WO_HEADER)
                pm.imu_sys_tick = FourBytesToUint32(pm.imu_rx_buff, 0) - IMU_SYSTICK_SHIFT_MSEC
                print("X" + str(pm.imu_sys_tick))
                pm.process_imu_data(pm.imu_rx_buff)
                pm.print_imu_data()
                # acc_x_values.append(pm.acc_x)
                # acc_y_values.append(pm.acc_y)
                # acc_z_values.append(pm.acc_z)

                pm.clear_imu_properties()
            else:
                prnt("ERR SOF", 1)

        else:
            prnt("bye bye..\r\n")
            input()
            exit(1)

def TwoBytesToUint16 (a_byte_arr, a_shift = 0):
    return int.from_bytes( a_byte_arr[a_shift:a_shift+2],byteorder='little',signed=False)


def FourBytesToUint32 (a_byte_arr, a_shift):
    return int.from_bytes( a_byte_arr[a_shift:a_shift+4],byteorder='little',signed=False)

def TwoBytesToInt16 (a_byte_arr, a_shift = 0):
    return int.from_bytes( a_byte_arr[a_shift:a_shift+2],byteorder='little',signed=True)

def FourBytesToInt32 (a_byte_arr, a_shift):
    return int.from_bytes( a_byte_arr[a_shift:a_shift+4],byteorder='little',signed=True)

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

    def __init__(self, a_host, a_port):
        self.host   = a_host
        self.port   = a_port
        self.socket = None
        self.rx_bytes_to_read = 1
        self.frame_rx_buff = bytes()
        self.frame_sys_tick = 0
        self.last_valid_frame_sys_tick = 0
        self.frame_size =   0
        self.ptr_jpeg   = None
        self.last_saved_img_path = ''
        self.last_saved_cropped_img_path = ''

        self.imu_rx_buff = bytes()
        self.imu_sys_tick = 0

        self.new_img_rec = False
        self.new_imu_rec = False

        self.gyro_x = 0
        self.gyro_y = 0
        self.gyro_z = 0
        self.acc_x = 0
        self.acc_y = 0
        self.acc_z = 0

    def add_socket(self, a_socket):
        self.socket =   a_socket

    def save_jpeg(self, save_path):
        # prnt("image size =", 0)
        # self.print_buff_len()
        # prnt(("img systick = " + str(self.frame_sys_tick)), 0)
        curr_saved_file_name = save_path + "\\" + str(self.frame_sys_tick)

        self.last_saved_img_path = curr_saved_file_name + ".jpeg"
        self.ptr_jpeg = open(self.last_saved_img_path, "wb")
        self.ptr_jpeg.write(self.frame_rx_buff)
        self.ptr_jpeg.close()
        self.crop_img(self.last_saved_img_path)
        self.new_img_rec = True

    def display_img(self):
        img_plt = None
        while True:
            if self.new_img_rec:
                self.new_img_rec = False
                print("displaying new img")
                try:
                    img = plt.imread(self.last_saved_cropped_img_path)
                    if img_plt is None:
                        img_plt = plt.imshow(img)
                    else:
                        img_plt.set_data(img)
                    plt.pause(.001)  # needs to be less then 1/15fps
                    plt.draw()
                except:
                    img = plt.imread(ERR_IMG_PATH)
                    if img_plt is None:
                        img_plt = plt.imshow(img)
                    else:
                        img_plt.set_data(img)
                    plt.pause(.001)  # needs to be less then 1/15fps
                    plt.draw()
                    print("img show err")

    # def display_imu(self):
    #     imu_plt = None
    #     while True:
    #         if self.new_imu_rec:
    #             self.new_imu_rec = False
    #             print("displaying new imu")
    #             try:
    #                 if imu_plt is None:
    #                     imu_plt = plt.plot(0, 0)
    #                 else:
    #                     imu_plt.set_data(np.linspace(0, len(self.acc_x)), self.acc_x)
    #                 plt.pause(.067) # ~15fps
    #                 plt.draw()
    #             except:
    #                 print("imu show err")

    def crop_img(self, img_path):
        try:
            img = cv2.imread(img_path)
            cropped_img = img[IMG_H_CROP:IMG_H, 0:IMG_W]
            self.last_saved_cropped_img_path = self.last_saved_img_path.replace('.jpeg', '_c.jpeg')
            # self.last_saved_img_path = cropped_img_file_name
            cropped_img = cv2.flip(cropped_img, 1)
            cropped_img = cv2.rotate(cropped_img, cv2.ROTATE_180)
            cv2.imwrite(self.last_saved_cropped_img_path, cropped_img)
        except:
            print("crop img err")


    def clear_frame_properties(self):
        self.packet_ctr =   0
        self.frame_sys_tick   =   0
        self.frame_size =   0
        self.frame_ctr  =   0
        self.expected_num_of_packets = 0
        self.ptr_jpeg   = None
        self.mode       =   0 # 0 = off, 1 = Image, 2 = IMU
        self.frame_rx_buff = bytes(0)

    def clear_imu_properties(self):
        self.imu_rx_buff = bytes(0)
        self.imu_sys_tick = 0

    def print_buff_len(self):
        try:
            print("buff len: " + str(len(self.frame_rx_buff)))
        except:
            print("buff len: 0")

    def process_imu_data(self, a_byte_arr):
        self.new_imu_rec = True

        for imu_call_idx in range(IMU_CALLS_PER_PACKET):
            self.gyro_x = TwoBytesToInt16(a_byte_arr,IMU_DATA_SHIFT_SIZE_B + imu_call_idx*IMU_CALL_SIZE_B + GYRO_X_SHIFT) / 131.0
            self.gyro_y = TwoBytesToInt16(a_byte_arr,IMU_DATA_SHIFT_SIZE_B + imu_call_idx * IMU_CALL_SIZE_B + GYRO_Y_SHIFT) / 131.0
            self.gyro_z = TwoBytesToInt16(a_byte_arr,IMU_DATA_SHIFT_SIZE_B + imu_call_idx * IMU_CALL_SIZE_B + GYRO_Z_SHIFT) / 131.0
            self.acc_x = TwoBytesToInt16(a_byte_arr,IMU_DATA_SHIFT_SIZE_B + imu_call_idx * IMU_CALL_SIZE_B + ACC_X_SHIFT) / 16384.0
            self.acc_y = TwoBytesToInt16(a_byte_arr,IMU_DATA_SHIFT_SIZE_B + imu_call_idx * IMU_CALL_SIZE_B + ACC_Y_SHIFT) / 16384.0
            self.acc_z = TwoBytesToInt16(a_byte_arr,IMU_DATA_SHIFT_SIZE_B + imu_call_idx * IMU_CALL_SIZE_B + ACC_Z_SHIFT) / 16384.0

    def print_imu_data(self):
        prnt(("Gyro X = " + str(self.gyro_x)), 0)
        prnt(("Gyro Y = " + str(self.gyro_y)), 0)
        prnt(("Gyro Z = " + str(self.gyro_z)), 0)
        prnt(("Acc X = " + str(self.acc_x)), 0)
        prnt(("Acc Y = " + str(self.acc_y)), 0)
        prnt(("Acc Z = " + str(self.acc_z)), 0)


if __name__ == "__main__":
    main()



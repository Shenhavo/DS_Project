
import socket
from datetime import datetime
import os
import subprocess
import time
from PIL import Image
import cv2
import pickle

GLOBAL_VERBOSITY            =   5

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

SSID = 'WINC1500_AP'

def main():
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    prnt(("date and time =" + dt_string), 0)
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
        #
        # print("Are you ready to start? y/n\r\n")
        # user_intput = input()
        #
        # if( user_intput == 'y'):
        s.sendall(b'Start\r\n')

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
                        # pm.crop_cheat(pm.last_saved_img_path)
                        delta_tick = pm.frame_sys_tick - pm.last_valid_frame_sys_tick
                        print("sys_tick diff = %d [msec]" % delta_tick)
                        pm.last_valid_frame_sys_tick = pm.frame_sys_tick
                    # ===== cleaning:  ======
                    pm.clear_frame_properties()

            # elif incoming_data[0] == IMU_SOF:
            #     pm.imu_rx_buff = s.recv(IMU_PACKET_SIZE_WO_HEADER)
            #     pm.imu_sys_tick = FourBytesToUint32(pm.imu_rx_buff, 0) - IMU_SYSTICK_SHIFT_MSEC
            #     print( "X" +str(pm.imu_sys_tick))
            #     # pm.print_IMU_data(pm.imu_rx_buff)
            #     # pm.clear_imu_properties()
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

        self.imu_rx_buff = bytes()
        self.imu_sys_tick = 0

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

        #TODO: remove
        # self.last_saved_img_path = save_path + "\\" + str(self.frame_sys_tick) + ".bmp"
        # self.ptr_jpeg = open(self.last_saved_img_path, 'w+b')
        # self.ptr_jpeg.write(self.frame_rx_buff)
        # self.ptr_jpeg.close()
        # f_bin_out_path = curr_saved_file_name + ".bin"
        # f_bin_out = open(f_bin_out_path, "wb")
        # f_bin_out.write(self.frame_rx_buff)
        # f_bin_out.close()

        self.crop_img(self.last_saved_img_path)

        # fix_jpeg_save_path = save_path + "\\" + str(self.frame_sys_tick) + "fix.jpeg"
        # img = cv2.imread(self.last_saved_img_path)
        # cv2.imshow('image', img)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        # crop_img = img[16:288, 0:240]
        # cv2.imshow("cropped" + img_path, crop_img)
        # cv2.imwrite(fix_jpeg_save_path, img)
#        Image.open(self.last_saved_img_path).save("sample1.bmp")

    # TOOD: remove
    def crop_img(self, img_path):
        try:
            img = cv2.imread(img_path)
            cropped_img = img[16:240, 0:320]
            # cv2.imshow("cropped" + img_path, crop_img)
            cropped_img_file_name = self.last_saved_img_path.replace('.jpeg', '_c.jpeg')

            cv2.imwrite(cropped_img_file_name, cropped_img)
            # cv2.waitKey(0)
        except:
            None


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

    def print_IMU_data(self,a_byte_arr):
        # prnt(("imu systick = " + str(self.imu_sys_tick)), 0)
        for imu_call_idx in range(IMU_CALLS_PER_PACKET):
            prnt(("Gyro X = " + str(TwoBytesToInt16(a_byte_arr,IMU_DATA_SHIFT_SIZE_B + imu_call_idx*IMU_CALL_SIZE_B + GYRO_X_SHIFT)/131.0 )), 0)
            prnt(("Gyro Y = " + str(TwoBytesToInt16(a_byte_arr,IMU_DATA_SHIFT_SIZE_B + imu_call_idx * IMU_CALL_SIZE_B + GYRO_Y_SHIFT)/131.0 )),
                 0)
            prnt(("Gyro Z = " + str(TwoBytesToInt16(a_byte_arr,IMU_DATA_SHIFT_SIZE_B + imu_call_idx * IMU_CALL_SIZE_B + GYRO_Z_SHIFT)/131.0 )),
                 0)
            prnt(("Acc X = " + str(TwoBytesToInt16(a_byte_arr,IMU_DATA_SHIFT_SIZE_B + imu_call_idx * IMU_CALL_SIZE_B + ACC_X_SHIFT)/16384.0 )),
                 0)
            prnt(("Acc Y = " + str(TwoBytesToInt16(a_byte_arr,IMU_DATA_SHIFT_SIZE_B + imu_call_idx * IMU_CALL_SIZE_B + ACC_Y_SHIFT)/16384.0  )),
                 0)
            prnt(("Acc Z = " + str(TwoBytesToInt16(a_byte_arr,IMU_DATA_SHIFT_SIZE_B + imu_call_idx * IMU_CALL_SIZE_B + ACC_Z_SHIFT)/16384.0  )),
                 0)




if __name__ == "__main__":
    main()



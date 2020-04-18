
import socket, time
from datetime import datetime


MAIN_WIFI_M2M_BUFFER_SIZE = 1024
def main():
    HOST = '192.168.1.1' # Standard loopback interface address (localhost)
    PORT = 6666  # Port to listen on (non-privileged ports are > 1023)

    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    print("date and time =", dt_string)

    ptr = open("output_file.txt", 'w')
    ptr.write("hola mundo\t"+ dt_string + "\r\n")


    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))

        print("Are you ready to start? y/n\r\n")
        user_intput = input()

        if( user_intput == 'y'):
            s.sendall(b'Start\r\n')
            string_input = b""
            loop_counter = 0
            frame_ctr = 0

            while True:

                tmp = s.recv(MAIN_WIFI_M2M_BUFFER_SIZE) # blocking mode, therefore size wont be a problem

                if ( loop_counter == 0 ):
                    size = FourBytesToUint32(tmp)
                    print("size = " + str(size))
                    tmp = b""
                loop_counter = loop_counter + 1

                string_input = string_input + tmp

                if (len(string_input) >= size ):
                    frame_ctr = frame_ctr + 1
                    print("frame counter = " + str(frame_ctr))
                    string_input = string_input[0:size]
                    print("len=" + str(len(string_input)))
                    now = datetime.now()
                    ptr_jpeg = open("outputs\output_file"+now.strftime("%M_%S_%f")+".jpeg", 'w+b')
                    ptr_jpeg.write(string_input)
                    ptr_jpeg.close()
                    ptr_jpeg = None
                    tmp = b""
                    string_input = b""

        else:
            print("bye bye..\r\n")
            input()
            exit(1)

def FourBytesToUint32 (a_byte_arr):
    return int(a_byte_arr[0]) + int(a_byte_arr[1])*256 + int(a_byte_arr[2])*65536 + int(a_byte_arr[3])*16777216

if __name__ == "__main__":
    main()



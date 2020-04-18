
import socket, time
from datetime import datetime
MAIN_WIFI_M2M_BUFFER_SIZE = 1024

# This code communicates with payload and prints time-stamps that aew are added to the first 4 bytes of the packets

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
            data =[]
            tick = 0
            while True:

                tmp = s.recv(MAIN_WIFI_M2M_BUFFER_SIZE)

                new_tick = FourBytesToUint32(tmp)

                if new_tick != tick:
                    now = datetime.now()
                    dt_string = now.strftime("%H:%M:%S.%f")
                    print(dt_string + '\t' + str(tick))
                tick = new_tick

        else:
            print("bye bye..\r\n")
            input()
            exit(1)


def FourBytesToUint32 (a_byte_arr):
    return int(a_byte_arr[0]) + int(a_byte_arr[1])*256 + int(a_byte_arr[2])*65536 + int(a_byte_arr[3])*16777216


if __name__ == "__main__":
    main()




INPUT_FILE = "so_jpeg.jpg"
OUTPUT_FILE = "hex_arr.txt"
def main():
    input_file = open(INPUT_FILE, "rb")

    input_file_content = input_file.read()
    a = input_file_content[0]
    output = ", ".join(hex(c) for c in input_file_content)

    outputFile = open(OUTPUT_FILE, "w")
    outputFile.write(output)
    outputFile.close()


if __name__ == "__main__":
    main()
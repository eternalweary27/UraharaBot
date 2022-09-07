import os
import random
path = "./test/test.txt"
with open(path, mode = "r") as read_file:
    lines = read_file.readlines()
    read_file.close()
print(lines)

filenames = os.listdir("./")
print(filenames)

random_filename = "./test/" + random.choice(os.listdir("./test"))
os.remove(random_filename)
print("File removed: " + random_filename)
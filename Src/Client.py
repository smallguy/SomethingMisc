import socket

sk = socket.socket()
sk.connect(('127.0.0.1', 1559))
data = sk.recv(1024)
print(data)
while True:
    i = input("> ")
    sk.sendall(str(i))
    msg = sk.recv(1024)
    print(str(msg))

sk.close()
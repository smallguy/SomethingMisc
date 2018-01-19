

import socket
import select

sk = socket.socket()
sk.bind(('127.0.0.1', 1559))
sk.listen(5)

inputs = [sk]
outputs = []
messages = {}

"""
messages = {
    socket_obj1: [msg]
    socket_obj2: [msg]
}
"""

while True:
    rList, wList, e = select.select(inputs, outputs, [], 1)
    print("---" * 20)
    print("select inputs num>", len(inputs), " | socket num>", len(rList))
    print("select outputs num>", len(outputs), " | reply num>", len(wList))
    for s in rList:
        if s == sk:
            conn, address = s.accept()
            inputs.append(conn)
            messages[conn] = []
            conn.sendall('hello')
        else:
            try:
                msg = s.recv(1024)
                if not msg:
                    raise Exception('client break')
                else:
                    outputs.append(s)
                    messages[s].append(msg)
            except Exception as ex:
                inputs.remove(s)
                del messages[s]

    for s in wList:
        msg = messages[s].pop()
        s.sendall(msg)
        outputs.remove(s)

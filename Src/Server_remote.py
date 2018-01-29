import socket
import selectors
import errno
import re

def accept(sock, mask):
    conn, addr = sock.accept()  # Should be ready
    print('accepted', conn, 'from', addr)
    sel.register(conn, selectors.EVENT_READ, firstread)
    conn.setblocking(False)

def firstread(sock, mask):
    datas = b''
    while True:
        try:
            data = sock.recv(1024)
            if not data and not datas:
                sel.unregister(sock)
                sock.close()
                break
            else:
                datas += data
        except socket.error as msg:
            if msg.errno == errno.WSAEWOULDBLOCK:
                print(datas)
                host = ('127.0.0.1', 1560)
                gethostfromdata(datas,host)
                datalist[sock] = datas
                connecttonextpoint(sock, host)
                break
            else:
                sel.unregister(sock)
                sock.close()
                break

def gethostfromdata(datas,host):
    regex_start_m = re.compile("Host:.+", re.M)
    strHost = regex_start_m.findall(datas.decode())[0][6:-1]
    index = strHost.find(':')
    if(index == -1):
        host = (socket.gethostbyname(strHost),80)
    else:
        host = (socket.gethostbyname(strHost[0:index]),int(strHost[index+1:]))
    print(repr(host))

def connecttonextpoint(sock,host):
    sk = socket.socket()
    sk.connect(host)
    print('connect from',sk)
    sk.setblocking(False)
    sockmap[sock] = sk
    sockmap[sk] = sock
    sel.register(sk, selectors.EVENT_WRITE, writer)


def read(sock, mask):
    datas =b''
    while True:
        try:
            data = sock.recv(1024)
            if not data and not datas:
                sel.unregister(sock)
                sel.unregister(sockmap[sock])
                sockmap.pop(sockmap[sock])
                sockmap[sock].close()
                sockmap.pop(sock)
                sock.close()
                break
            else:
                datas += data
        except socket.error as msg:
            if msg.errno == errno.WSAEWOULDBLOCK:
                print ('read:',datas)
                datalist[sock] = datas
                sel.unregister(sockmap[sock])
                sel.register(sockmap[sock],selectors.EVENT_WRITE, writer)
                break
            else:
                sel.unregister(sockmap[sock])
                sel.unregister(sock)
                sockmap.pop(sockmap[sock])
                sockmap[sock].close()
                sockmap.pop(sock)
                sock.close()
                break

def writer(sock, mask):
   sendLen = 0
   while True:
       try:
            sendLen += sock.send(datalist[sockmap[sock]][sendLen:])
            if sendLen == len(datalist[sockmap[sock]]):
                sel.unregister(sock)
                sel.register(sock, selectors.EVENT_READ, read)
                datalist.pop(sockmap[sock])
                break
       except socket.error as msg:
           sel.unregister(sockmap[sock])
           sel.unregister(sock)
           sockmap.pop(sockmap[sock])
           sockmap[sock].close()
           sockmap.pop(sock)
           sock.close()
           break

sk = socket.socket()
sk.bind(('127.0.0.1', 1561))
sk.listen(100)
sk.setblocking(False)
sel = selectors.DefaultSelector()
sel.register(sk, selectors.EVENT_READ, accept)
datalist = {} #store msg
sockmap = {} # store connection map
#加一个是否处理加密问题的set
print("start")
while True:
    print("listening")
    events = sel.select()
    for key, mask in events:
        callback = key.data
        callback(key.fileobj, mask)

#coding:utf-8
test test
import socket
import selectors
import errno
import queue

def accept(sock, mask):
    conn, addr = sock.accept()  # Should be ready
    print('accept', conn, 'from', addr)
    conn.setblocking(False)
    isclientsocket[conn] = True
    sel.register(conn, selectors.EVENT_READ, read)

def read(sock, mask):
    datas =b''
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                if datas:
                    print('read:\r\n', datas)
                    ondatacome(sock,datas)
                    break
                onclose(sock)
                break
            else:
                datas += data
        except socket.error as msg:
            if msg.errno == errno.WSAEWOULDBLOCK:
                print ('read:\r\n',datas)
                ondatacome(sock,datas)
                break
            else:
                onclose(sock)
                break

def writer(sock, mask):
    try:
        if sock in msgtosock.keys():
            q = msgtosock[sock]
            while q.empty() != True:
                msg = q.get()
                sock.sendall(msg)
                print('writer:\r\n', msg)
        sel.unregister(sock)
        sel.register(sock, selectors.EVENT_READ, read)
        msgtosock.pop(sock)
    except:
        onclose(sock)

def ondatacome(sock,data):
    if ((sock in isclientsocket.keys()) and (isclientsocket[sock] == True)):
        if((sock not in channel.keys()) or (channel[sock].fileno() == -1)):# to establish channel
            host = ("127.0.0.1",1561)
            try:
                sk = socket.socket()
                isclientsocket[sk] = False
                sk.settimeout(1)
                sk.connect(host)
                sk.setblocking(False)
                print('connect next', sk)
                if ((sock in channel.keys()) and (channel[sock].fileno() == -1)):
                    channel.pop(channel[sock])
                channel[sock] = sk
                channel[sk] = sock
                sel.register(sk, selectors.EVENT_READ, read)
            except:
               onclose(sock)
               return

        if sock in channel.keys():
            print('client->server:', data)
            if (channel[sock]) not in msgtosock:
                q = queue.Queue(100)
                q.put_nowait(data)
                msgtosock[channel[sock]] = q
            else:
                q = msgtosock.pop(channel[sock])
                q.put_nowait(data)
                msgtosock[channel[sock]] = q
            try:
                sel.unregister(channel[sock])
            except:
                pass
            sel.register(channel[sock], selectors.EVENT_WRITE, writer)
            return
    else:
        if sock in channel.keys():
             print('server->client:', data)
             if (channel[sock]) not in msgtosock:
                 q = queue.Queue(100)
                 q.put_nowait(data)
                 msgtosock[channel[sock]] = q
             else:
                 q = msgtosock.pop(channel[sock])
                 q.put_nowait(data)
                 msgtosock[channel[sock]] = q
             try:
                sel.unregister(channel[sock])
             except:
                 pass
             sel.register(channel[sock], selectors.EVENT_WRITE, writer)

def onclose(sock):
    if ((sock in isclientsocket.keys()) and isclientsocket[sock] == True):
        if sock in msgtosock.keys():
            msgtosock.pop(sock)
        if((sock in channel.keys()) and (channel[sock] in msgtosock.keys())):
            msgtosock.pop(channel[sock])
        if ((sock in channel.keys()) and (channel[sock] in isclientsocket.keys())):
            isclientsocket.pop(channel[sock])
        if (sock in isclientsocket.keys()):
            isclientsocket.pop(sock)
        if((sock in channel.keys()) and (channel[sock].fileno() != -1)):
           try:
             sel.unregister(channel[sock])
           except:
               pass
        elif sock in channel.keys():
            channel[sock].close()
        if(sock.fileno() != -1):
            try:
                sel.unregister(sock)
            except:
                pass
        else:
            sock.close()
        if (sock in channel.keys()) and (channel[sock] in channel.keys()):
            channel.pop(channel[sock])
        elif sock in channel.keys():
            channel.pop(sock)
    else:
        if sock in msgtosock.keys():
            msgtosock.pop(sock)
        if(sock.fileno() != -1):
            try:
                sel.unregister(sock)
            except:
                pass
        else:
            sock.close()

if __name__ == '__main__':
    sk = socket.socket()
    sk.bind(('127.0.0.1', 1560))
    sk.listen(1000)
    sk.setblocking(False)
    sel = selectors.DefaultSelector()
    sel.register(sk, selectors.EVENT_READ, accept)
    msgtosock = {} #store msg
    channel = {} # store connection map
    isclientsocket = {}
    print("start")
    while True:
        print("listening")
        events = sel.select()
        for key, mask in events:
            callback = key.data
            callback(key.fileobj, mask)

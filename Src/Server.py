#coding:utf-8
import socket
import selectors
import errno
import re
import queue

def accept(sock, mask):
    conn, addr = sock.accept()  # Should be ready
    print('accept', conn, 'from', addr)
    conn.setblocking(False)
    isclientsocket[conn] = True
    sel.register(conn, selectors.EVENT_READ, read)

def adjustRequestHeader(datas):
    method = getmethodfromdata(datas)
    uri = bytes(method[1]).decode()
    data = bytes(datas).decode()
    request_header = data.split('\r\n\r\n')[0] + '\r\n\r\n'
    header_length = len(request_header)
    request_header = re.sub('Proxy-Connection: .+\r\n', '', request_header)
    request_header = re.sub('Connection: .+', '', request_header)
    request_header = re.sub('\r\n\r\n', '\r\nConnection: close\r\n\r\n', request_header)
    idx = uri.index('/', 8)
    request_header = re.sub(uri, uri[idx:], request_header)
    data = request_header + data[header_length:]
    return data.encode()

def gethostfromdata(datas):
    regex_start_m = re.compile("Host:.+", re.M)
    strHost = regex_start_m.findall(bytes(datas).decode())[0][6:-1]
    index = strHost.find(':')
    if(index == -1):
        host = (socket.gethostbyname(strHost),80)
    else:
        host = (socket.gethostbyname(strHost[0:index]),int(strHost[index+1:]))
    print(repr(host))
    return host

def getmethodfromdata(datas):
    index = datas.find(b'\r')
    strFirstLine = datas[0:index]
    method = strFirstLine.split(b' ')
    print("getmethodfromdata",method,datas)
    return method

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
            host = gethostfromdata(data)
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
        if (sock not in isconnectmethod.keys()) or (isconnectmethod[sock] == False):
             method = getmethodfromdata(data)
             if (method[0] == b"CONNECT"):
                isconnectmethod[sock] = True
                if sock in channel.keys():
                    isconnectmethod[channel[sock]] = True
                toclientmsg = method[2] + b' HTTP/1.1 200 Connection Established\r\nConnection: Close\r\n\r\n'
                if sock not in msgtosock.keys():
                    q = queue.Queue(20)
                    q.put_nowait(toclientmsg)
                    msgtosock[sock] = q
                else:
                    q = msgtosock.pop(sock)
                    q.put_nowait(toclientmsg)
                    msgtosock[sock] = q
                print('server->client:',toclientmsg)
                try:
                    sel.unregister(sock)
                except:
                    pass
                sel.register(sock, selectors.EVENT_WRITE, writer)
             else:
                isconnectmethod[sock] = False
                if sock in channel.keys():
                    isconnectmethod[channel[sock]] = False
                adjustdata = adjustRequestHeader(data)
                if sock in channel.keys():
                    print('client->server:', adjustdata)
                    if (channel[sock]) not in msgtosock:
                        q = queue.Queue(20)
                        q.put_nowait(adjustdata)
                        msgtosock[channel[sock]] = q
                    else:
                        q = msgtosock.pop(channel[sock])
                        q.put_nowait(adjustdata)
                        msgtosock[channel[sock]] = q
                    try:
                        sel.unregister(channel[sock])
                    except:
                        pass
                    sel.register(channel[sock], selectors.EVENT_WRITE, writer)
             return
        elif isconnectmethod[sock] == True:
             if sock in channel.keys():
                print('connect client->server:', data)
                if (channel[sock]) not in msgtosock:
                    q = queue.Queue(20)
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
    elif sock in isconnectmethod.keys() and isconnectmethod[sock] == True:
        if sock in channel.keys():
             print('connect server->client:', data)
             if (channel[sock]) not in msgtosock:
                 q = queue.Queue(20)
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
    else:
        if sock in channel.keys():
             print('server->client:', data)
             if (channel[sock]) not in msgtosock:
                 q = queue.Queue(20)
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
    if ((sock in isclientsocket.keys()) and isclientsocket[sock] == True) or ((sock in isconnectmethod.keys()) and (isconnectmethod[sock] == True)):
        if sock in msgtosock.keys():
            msgtosock.pop(sock)
        if((sock in channel.keys()) and (channel[sock] in msgtosock.keys())):
            msgtosock.pop(channel[sock])
        if sock in isconnectmethod.keys():
            isconnectmethod.pop(sock)
        if((sock in channel.keys()) and (channel[sock] in isconnectmethod.keys())):
            isconnectmethod.pop(channel[sock])
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

sk = socket.socket()
sk.bind(('127.0.0.1', 1561))
sk.listen(1000)
sk.setblocking(False)
sel = selectors.DefaultSelector()
sel.register(sk, selectors.EVENT_READ, accept)
msgtosock = {} #store msg
channel = {} # store connection map
isclientsocket = {}
isconnectmethod = {} #is CONNECT method
print("start")
while True:
    print("listening")
    events = sel.select()
    for key, mask in events:
        callback = key.data
        callback(key.fileobj, mask)

#!/usr/bin/env python3
"""
Hybrid P2P audio client using sounddevice (PortAudio).

• Registers with signaling server over TCP.
• Exchanges call setup messages.
• Streams microphone → UDP → peer.
• Plays received UDP audio via sounddevice.
"""
import socket, threading, json, argparse, sys, time
import sounddevice as sd, numpy as np

RATE=44100; CHUNK=1024; CHANNELS=1; DTYPE=np.int16

# ----------- audio loops -----------
def udp_audio_send(udp, peer, stop):
    """Capture mic and send over UDP."""
    def cb(indata, frames, time_info, status):
        if not stop.is_set():
            udp.sendto(indata.tobytes(), peer)
    print(f"[audio→] to {peer}")
    with sd.InputStream(samplerate=RATE, channels=CHANNELS, dtype=DTYPE,
                        callback=cb, blocksize=CHUNK):
        while not stop.is_set(): time.sleep(0.05)
    print("[audio→] stopped")

def udp_audio_recv(udp, stop):
    """Receive UDP and play through speakers."""
    def cb(outdata, frames, time_info, status):
        try:
            data,_=udp.recvfrom(CHUNK*4)
            out=np.frombuffer(data,dtype=DTYPE)
            outdata[:len(out)] = out.reshape(-1,1)
        except socket.timeout:
            outdata.fill(0)
    print("[audio←] listening")
    with sd.OutputStream(samplerate=RATE, channels=CHANNELS, dtype=DTYPE,
                         callback=cb, blocksize=CHUNK):
        while not stop.is_set(): time.sleep(0.05)
    print("[audio←] stopped")

# ----------- tcp listener -----------
def tcp_listener(sock, handlers):
    f=sock.makefile("rb")
    for line in f:
        try: msg=json.loads(line.decode())
        except: continue
        typ=msg.get("type")
        if typ in handlers: handlers[typ](msg)
        else: print("[srv]",msg)
    print("[control] disconnected"); sys.exit(0)

# ----------- interactive client -----------
def cli(tcp, udp, name):
    stop=threading.Event(); threads=[]
    last_incoming=None; peer=None

    def established(m):
        nonlocal peer, threads
        peer=(m["peer_ip"],int(m["peer_udp_port"]))
        print(f"[call] established with {m['peer']} @ {peer}")
        stop.clear()
        t1=threading.Thread(target=udp_audio_send,args=(udp,peer,stop),daemon=True)
        t2=threading.Thread(target=udp_audio_recv,args=(udp,stop),daemon=True)
        threads=[t1,t2]; [t.start() for t in threads]

    handlers={
        "incoming_call":lambda m: handle_incoming(m),
        "call_resp":lambda m: print("[status]",m),
        "call_established":established,
        "call_rejected":lambda m: print(f"[rejected] {m['from']}"),
        "busy": lambda m: print(f"[busy] {m['user']} is currently in another call."),
        "hangup":lambda m:(print(f"[hangup] {m['from']}"), stop.set()),
        "user_free": lambda m: print(f"[notify] {m['user']} is now free to receive calls."),
        "who_resp":lambda m: print(json.dumps(m["users"],indent=2))
    }

    def handle_incoming(m):
        nonlocal last_incoming
        last_incoming=m["from"]
        print(f"\n[incoming] call from {last_incoming} → accept/reject?")

    threading.Thread(target=tcp_listener,args=(tcp,handlers),daemon=True).start()

    while True:
        try: cmd=input("cmd> ").strip().split()
        except (EOFError,KeyboardInterrupt): cmd=["quit"]
        if not cmd: continue
        c=cmd[0]
        if c=="call" and len(cmd)>1:
            tcp.sendall((json.dumps({"action":"call","to":cmd[1]})+"\n").encode())
        elif c=="accept" and last_incoming:
            tcp.sendall((json.dumps({"action":"call_response","from":last_incoming,"accept":True})+"\n").encode()); last_incoming=None
        elif c=="reject" and last_incoming:
            tcp.sendall((json.dumps({"action":"call_response","from":last_incoming,"accept":False})+"\n").encode()); last_incoming=None
        elif c=="hangup":
            stop.set(); tcp.sendall((json.dumps({"action":"hangup"})+"\n").encode())
        elif c=="who":
            tcp.sendall((json.dumps({"action":"who"})+"\n").encode())
        elif c=="quit":
            stop.set(); tcp.sendall((json.dumps({"action":"unregister"})+"\n").encode()); tcp.close(); break
        else:
            print("commands: call <user>, accept, reject, hangup, who, quit")

# ----------- entry point -----------
def main(host,port,user,udp_port):
    udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    udp.bind(("0.0.0.0",udp_port)); udp.settimeout(0.5)
    tcp=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    tcp.connect((host,port))
    tcp.sendall((json.dumps({"action":"register","username":user,"udp_port":udp_port})+"\n").encode())
    resp=json.loads(tcp.makefile("r").readline())
    if resp.get("status")!="ok": print("register failed:",resp); return
    print(f"[registered] {user}@{host}:{port} udp:{udp_port}")
    cli(tcp,udp,user)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--server-host",default="127.0.0.1")
    ap.add_argument("--server-port",type=int,default=5000)
    ap.add_argument("--username",required=True)
    ap.add_argument("--udp-port",type=int,default=20000)
    a=ap.parse_args()
    main(a.server_host,a.server_port,a.username,a.udp_port)

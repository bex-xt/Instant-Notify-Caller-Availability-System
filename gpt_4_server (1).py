#!/usr/bin/env python3
"""
Hybrid signaling server for 1-to-1 P2P audio chat.

Enhancement:
------------
If a user (e.g. Bob) is busy and another user (e.g. Charlie) tries to call them,
Charlie is told "bob is busy". Then, when Bob becomes free again,
the server automatically sends Charlie a message:
{"type": "user_free", "user": "bob"}.
"""
import socket, threading, json, time, argparse

LOCK = threading.Lock()
users = {}      # username → {"tcp":sock, "addr":(ip,port), "udp":int, "peer":username|None, "seen":timestamp}
waiters = {}    # target_username → [caller1, caller2, ...]

def now(): return int(time.time())

def send_json(sock, obj):
    try:
        sock.sendall((json.dumps(obj)+"\n").encode())
    except:
        pass

def handle_client(conn, addr):
    user = None
    f = conn.makefile("rb")
    try:
        while True:
            line = f.readline()
            if not line:
                break
            try:
                msg = json.loads(line.decode())
            except:
                continue
            act = msg.get("action")

            # --- registration ---
            if act == "register":
                name, udp = msg.get("username"), int(msg.get("udp_port", 0))
                with LOCK:
                    if name in users:
                        send_json(conn, {"type":"register_resp","status":"error","reason":"taken"})
                        continue
                    users[name] = {"tcp":conn,"addr":addr,"udp":udp,"peer":None,"seen":now()}
                user = name
                send_json(conn, {"type":"register_resp","status":"ok"})
                print(f"[+] {name}@{addr[0]}:{udp}")

            elif act == "unregister":
                break

            # --- call initiation ---
            elif act == "call":
                caller = user
                target = msg.get("to")
                if not caller or not target:
                    continue
                with LOCK:
                    if target not in users:
                        send_json(conn, {"type":"call_resp","status":"error","reason":"not_found"})
                        continue
                    # If either is busy
                    if users[caller]["peer"] or users[target]["peer"]:
                        send_json(conn, {"type":"busy","user":target})
                        if users[target]["peer"]:
                            waiters.setdefault(target, []).append(caller)
                            print(f"[busy] {target} busy; {caller} added to wait list.")
                        continue

                    # Otherwise, forward call
                    send_json(conn, {"type":"call_resp","status":"ringing"})
                    send_json(users[target]["tcp"], {"type":"incoming_call","from":caller})
                    print(f"[call] {caller}→{target}")

            # --- response to incoming call ---
            elif act == "call_response":
                caller, accept = msg.get("from"), bool(msg.get("accept"))
                if not user or not caller:
                    continue
                with LOCK:
                    if caller not in users:
                        continue
                    c, r = users[caller], users[user]
                    if accept:
                        c["peer"] = user
                        r["peer"] = caller
                        send_json(c["tcp"], {"type":"call_established","peer":user,
                                             "peer_ip":r["addr"][0],"peer_udp_port":r["udp"]})
                        send_json(r["tcp"], {"type":"call_established","peer":caller,
                                             "peer_ip":c["addr"][0],"peer_udp_port":c["udp"]})
                        print(f"[established] {caller}↔{user}")
                    else:
                        send_json(c["tcp"], {"type":"call_rejected","from":user})
                        print(f"[rejected] {user}→{caller}")

            # --- hangup ---
            elif act == "hangup":
                with LOCK:
                    if user and user in users and users[user]["peer"]:
                        peer = users[user]["peer"]
                        if peer in users:
                            send_json(users[peer]["tcp"], {"type":"hangup","from":user})
                            users[peer]["peer"] = None
                        users[user]["peer"] = None
                        send_json(conn, {"type":"hangup_resp","status":"ok"})
                        print(f"[hangup] {user} with {peer}\n")
                        # notify
                        if user in waiters:
                            for w in waiters.pop(user):
                                if w in users:
                                    send_json(users[w]["tcp"], {"type":"user_free","user":user})
                                    print(f"[notify] told {w} that {user} is now free")

            # --- who list ---
            elif act == "who":
                with LOCK:
                    lst = {u: {"udp":v["udp"], "peer":v["peer"]} for u,v in users.items()}
                send_json(conn, {"type":"who_resp","users":lst})

    finally:
        conn.close()
        with LOCK:
            if user and user in users:
                peer = users[user]["peer"]
                if peer and peer in users:
                    send_json(users[peer]["tcp"], {"type":"hangup","from":user})
                    users[peer]["peer"] = None
                users.pop(user, None)
                # If user disconnects while busy, also notify waiters
                if user in waiters:
                    for w in waiters.pop(user):
                        if w in users:
                            send_json(users[w]["tcp"], {"type":"user_free","user":user})
                            print(f"[notify] told {w} that {user} is now free (disconnected)")
        print(f"[-] {user or addr} disconnected")

def main(host, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen()
    print(f"[server] listening on {host}:{port}")
    try:
        while True:
            c, a = s.accept()
            threading.Thread(target=handle_client, args=(c, a), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[server] bye")
    finally:
        s.close()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=5000)
    a = ap.parse_args()
    main(a.host, a.port)

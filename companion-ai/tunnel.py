"""
SSH 本地端口转发守护进程
将本地 15000 端口转发到远程服务器的 127.0.0.1:8000
用法：python tunnel.py   （在 companion-ai 环境中运行，保持终端开着）
"""
import socket
import threading
import logging
import sys
import paramiko

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

SSH_HOST = "10.184.17.35"
SSH_PORT = 10222
SSH_USER = "jyyin"
SSH_PASS = "jyyin@123"

LOCAL_PORT = 15000
REMOTE_HOST = "127.0.0.1"
REMOTE_PORT = 8000


def _forward(local_sock: socket.socket, ssh_transport: paramiko.Transport):
    try:
        channel = ssh_transport.open_channel(
            "direct-tcpip", (REMOTE_HOST, REMOTE_PORT), local_sock.getpeername()
        )
    except Exception as e:
        logger.error(f"Channel open failed: {e}")
        local_sock.close()
        return

    def pipe(src, dst):
        try:
            while True:
                data = src.recv(4096)
                if not data:
                    break
                dst.sendall(data)
        except Exception:
            pass
        finally:
            try:
                src.close()
            except Exception:
                pass
            try:
                dst.close()
            except Exception:
                pass

    t1 = threading.Thread(target=pipe, args=(local_sock, channel), daemon=True)
    t2 = threading.Thread(target=pipe, args=(channel, local_sock), daemon=True)
    t1.start()
    t2.start()


def main():
    logger.info(f"Connecting SSH to {SSH_HOST}:{SSH_PORT} ...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, password=SSH_PASS, timeout=15)
    transport = client.get_transport()
    transport.set_keepalive(30)
    logger.info("SSH connected.")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", LOCAL_PORT))
    server.listen(20)
    logger.info(f"Tunnel listening on localhost:{LOCAL_PORT} -> {REMOTE_HOST}:{REMOTE_PORT}")

    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(target=_forward, args=(conn, transport), daemon=True).start()
    except KeyboardInterrupt:
        logger.info("Tunnel stopped.")
    finally:
        server.close()
        client.close()


if __name__ == "__main__":
    main()

"""测试 SSH 隧道 + LLM /health 接口"""
import paramiko
import http.client
import json

HOST = "10.184.17.35"
PORT = 10222
USER = "jyyin"
PASS = "jyyin@123"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print(f"Connecting to {HOST}:{PORT} ...")
client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=10)
print("SSH connected OK")

transport = client.get_transport()
channel = transport.open_channel("direct-tcpip", ("127.0.0.1", 8000), ("127.0.0.1", 0))

conn = http.client.HTTPConnection("127.0.0.1", 8000)
conn.sock = channel
conn.request("GET", "/health", headers={"Connection": "close"})
r = conn.getresponse()
body = r.read().decode()
print(f"Health status: {r.status}")
print(f"Body: {body}")
client.close()

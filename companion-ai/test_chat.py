"""测试 /chat 接口"""
import paramiko
import http.client
import json

HOST = "10.184.17.35"
PORT = 10222
USER = "jyyin"
PASS = "jyyin@123"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(HOST, port=PORT, username=USER, password=PASS, timeout=10)
print("SSH connected")

transport = client.get_transport()
channel = transport.open_channel("direct-tcpip", ("127.0.0.1", 8000), ("127.0.0.1", 0))

payload = json.dumps({
    "messages": [
        {"role": "system", "content": "你是惠惠，26岁，温柔知性的姐姐。回复简短自然。"},
        {"role": "user", "content": "今天好累啊"}
    ],
    "max_new_tokens": 100,
    "temperature": 0.85,
    "top_p": 0.9,
    "repetition_penalty": 1.1
}).encode("utf-8")

conn = http.client.HTTPConnection("127.0.0.1", 8000)
conn.sock = channel
conn.request("POST", "/chat", body=payload, headers={
    "Content-Type": "application/json",
    "Content-Length": str(len(payload)),
    "Connection": "close"
})
r = conn.getresponse()
body = r.read().decode("utf-8")
import sys
sys.stdout.reconfigure(encoding="utf-8")
print(f"Status: {r.status}")
data = json.loads(body)
print(f"Reply: {data['reply']}")
client.close()

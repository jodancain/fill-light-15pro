"""在仓库根目录运行；--require-tcp 要求真实 TCP + curl 完成，否则返回非零。"""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from http.client import HTTPResponse
from functools import partial
from io import BytesIO
from threading import Thread
import argparse, subprocess

ROOT=Path(__file__).resolve().parents[1]; WEB=ROOT/'web'
ASSETS=['index.html','app.js','models/filllight.glb','models/parts.json','models/comparison.png','models/power-route.svg']

class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass

def memory_request(name):
    class Capture(Handler):
        def setup(self):
            self.rfile=BytesIO(f'GET /{name} HTTP/1.0\r\nHost: localhost\r\n\r\n'.encode())
            self.wfile=BytesIO()
        def finish(self): self.response=self.wfile.getvalue()
    response=Capture(None,('127.0.0.1',0),None,directory=WEB).response
    class Adapter:
        def makefile(self,*args): return BytesIO(response)
    r=HTTPResponse(Adapter()); r.begin()
    assert r.status==200 and r.read()==(WEB/name).read_bytes()
    print(f'离线处理器（非套接字） {r.status} {name}')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-tcp',action='store_true'); opts=parser.parse_args()
    for f in [WEB/'app.js',*sorted((WEB/'vendor').glob('*.js'))]:
        subprocess.run(['node','--input-type=module','--check'],input=f.read_bytes(),check=True)
    print('app.js 及全部本地依赖语法通过',flush=True)
    subprocess.run(['node','--disable-warning=MODULE_TYPELESS_PACKAGE_JSON',ROOT/'mech/check_glb.mjs'],check=True)
    try: server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=WEB))
    except PermissionError as exc:
        print(f'TCP 未验收：无法监听回环地址（{exc}）。改核标准库请求处理与响应体。')
        for name in ASSETS: memory_request(name)
        return 2 if opts.require_tcp else 0
    try:
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        for name in ASSETS:
            result=subprocess.run(['curl','--noproxy','*','--max-time','5','-fsS','-w','%{http_code}',
                f'http://127.0.0.1:{server.server_port}/{name}'],capture_output=True,check=True)
            assert result.stdout[-3:]==b'200' and result.stdout[:-3]==(WEB/name).read_bytes()
            print('TCP + curl 200',name)
    finally:
        server.shutdown(); server.server_close();thread.join()
    return 0
if __name__=='__main__': raise SystemExit(main())

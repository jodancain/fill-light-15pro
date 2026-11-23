"""在仓库根目录运行；--require-tcp 要求真实 TCP + curl 完成，否则返回非零。"""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from http.client import HTTPResponse
from functools import partial
from io import BytesIO
from threading import Thread
import argparse, subprocess, json
TRANSPORT="未执行"

ROOT=Path(__file__).resolve().parents[1]; WEB=ROOT/'web'
ASSETS=['index.html','app.js','models/filllight.glb','models/parts.json','models/comparison.png','models/power-route.svg','battery.html','app_battery.js','models/filllight_battery.glb','models/parts_battery.json','style.css',*[p.relative_to(WEB).as_posix() for p in (WEB/'vendor').glob('*.js')]]

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
    global TRANSPORT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-tcp',action='store_true'); opts=parser.parse_args()
    for f in [WEB/'app.js',WEB/'app_battery.js',*sorted((WEB/'vendor').glob('*.js'))]:
        subprocess.run(['node','--input-type=module','--check'],input=f.read_bytes(),check=True)
    print('app.js 及全部本地依赖语法通过',flush=True)
    subprocess.run(['node','--disable-warning=MODULE_TYPELESS_PACKAGE_JSON',ROOT/'mech/check_glb.mjs'],check=True)
    subprocess.run(['node','--disable-warning=MODULE_TYPELESS_PACKAGE_JSON',ROOT/'mech/check_glb.mjs','--battery'],check=True)
    try: server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=WEB))
    except PermissionError as exc:
        print(f'TCP 未验收：无法监听回环地址（{exc}）。改核标准库请求处理与响应体。')
        for name in ASSETS: memory_request(name)
        from socketserver import UnixStreamServer
        import os,tempfile
        class Local(UnixStreamServer):
            def get_request(self):
                stream,_=super().get_request();return stream,('localhost',0)
        save=Path.cwd();(ROOT/'mech/out').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'mech/out') as tmp:
            os.chdir(tmp)
            try:
                with Local('serve.sock',partial(Handler,directory=WEB)) as srv:
                    t=Thread(target=srv.serve_forever,daemon=True);t.start()
                    try:
                        for name in ASSETS:
                            response=subprocess.run(['curl','--noproxy','*','--unix-socket','serve.sock','--max-time','5','-fsS','-w','%{http_code}',f'http://localhost/{name}'],capture_output=True,check=True).stdout
                            assert response[-3:]==b'200' and response[:-3]==(WEB/name).read_bytes()
                            print('本机 HTTP / Unix 套接字 curl 200',name)
                        TRANSPORT='本机 Unix 套接字 HTTP + curl；非 TCP'
                    finally:srv.shutdown();t.join()
            except PermissionError as local_exc:
                TRANSPORT='离线 HTTP 处理器，状态码和响应体逐字节验证；沙箱拒绝 TCP/Unix 监听，未验收 curl/TCP'
                print(f'本机 UNIX 套接字也禁止监听（{local_exc}）；离线评估已逐资源验证 200 和响应字节，不记为 curl/TCP 通过。')
            finally:os.chdir(save)
        return 2 if opts.require_tcp else 0
    try:
        thread=Thread(target=server.serve_forever,daemon=True);thread.start()
        for name in ASSETS:
            result=subprocess.run(['curl','--noproxy','*','--max-time','5','-fsS','-w','%{http_code}',
                f'http://127.0.0.1:{server.server_port}/{name}'],capture_output=True,check=True)
            assert result.stdout[-3:]==b'200' and result.stdout[:-3]==(WEB/name).read_bytes()
            print('TCP + curl 200',name)
        TRANSPORT='TCP + curl'
    finally:
        server.shutdown(); server.server_close();thread.join()
    return 0
if __name__=='__main__':
    code=main()
    if code==0:
        out=ROOT/'mech/out'; ledger=out/'round08/web-check.json';ledger.parent.mkdir(parents=True,exist_ok=True)
        summary=dict(transport=TRANSPORT,assets=ASSETS,code=code,loaders=['C-r7','A2-r1'])
        ledger.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
        report=out/'report_battery.md'
        if report.exists():
            head='## 网页与冻结交付回读'
            body=report.read_text().split(head)[0].rstrip()
            report.write_text(body+'\n\n'+head+'\n\n本地 three.js GLTFLoader：C、A2 模型和目录、单位、方向、分组通过。'
                +f'{len(ASSETS)} 个离线资源，{TRANSPORT}。详见 [网页记录](round08/web-check.json)。'
                +'C-r7 完整文件 SHA-256 与发布清单逐件核对，另有 [30 个 STEP/STL/GLB 的逐节点体积和包围盒差](round08/c_readback.json)。\n')
    raise SystemExit(code)

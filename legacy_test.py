"""Run as root on an authorized Linux Docker test host. Requires the pinned image already present."""
import base64, hashlib, io, json, os, secrets, shutil, socket, subprocess as sp, sys, tarfile, tempfile, time
from pathlib import Path

def check(x,s):
    if not x: raise RuntimeError(s)
    print("PASS",s,flush=True)

def cmd(*a,ok=True):
    r=sp.run(a,stdout=sp.PIPE,stderr=sp.PIPE,text=True)
    if ok and r.returncode: raise RuntimeError(r.stderr[:1200])
    return r.stdout.strip()

class Client:
    def __init__(self,p):
        self.s=socket.create_connection(('127.0.0.1',14222),2)
        self.f=self.s.makefile('rb'); assert self.f.readline().startswith(b'INFO ')
        self.send('CONNECT '+json.dumps(dict(verbose=False,pedantic=False,user='client',**{'pass':p}))+'\r\nPING\r\n')
        self.ok=self.f.readline().strip()==b'PONG'
    def send(self,t): self.s.sendall(t.encode())
    def msg(self):
        line=self.f.readline().split()
        assert line and line[0]==b'MSG',line
        n=int(line[-1]); data=self.f.read(n); assert self.f.read(2)==b'\r\n'
        return line,data
    def req(self,subj,body):
        self.send('SUB _INBOX.test 9\r\nUNSUB 9 1\r\nPUB '+subj+' _INBOX.test '+str(len(body))+'\r\n'+body+'\r\n')
        result=json.loads(self.msg()[1]);assert 'error' not in result,result;return result
    def close(self): self.f.close();self.s.close()

def main(pkg):
    check(os.geteuid()==0,'isolated test authorized; running Linux host harness')
    check(not cmd('docker','ps','-aq','--filter','name=^/nats$'),'no existing nats container')
    project='tm3'+secrets.token_hex(4); root=Path(tempfile.mkdtemp(prefix=project+'-'))
    prev=Path.cwd(); os.chdir(root); started=False
    compose=lambda *args: cmd('docker','compose','-p',project,*args)
    def ready(p):
        for _ in range(40):
            try:
                c=Client(p)
                if c.ok:return c
                c.close()
            except (OSError,AssertionError):pass
            time.sleep(.25)
        raise RuntimeError('startup: '+compose('logs','--tail','10')[:1200])
    try:
        with tarfile.open(fileobj=io.BytesIO(pkg)) as t:
            raw=t.extractfile('docker-compose.yml').read()
        Path('docker-compose.yml').write_bytes(raw)
        print('PACKAGE SHA256',hashlib.sha256(pkg).hexdigest(),flush=True)
        Path('data').mkdir();os.chown('data',1000,1000)
        for payload in ['', 'NATS_CLIENT_SECRET=\n']:
            Path('.env').write_text(payload)
            fail=sp.run(['docker','compose','-p',project,'config','-q'],capture_output=True)
            check(fail.returncode!=0 and b'NATS_CLIENT_SECRET' in fail.stderr,'missing or empty secret rejected')
        pw=secrets.token_hex(24);f=Path('.env');f.write_text('NATS_CLIENT_SECRET='+pw+'\n');f.chmod(0o600)
        cfg=json.loads(compose('config','--format','json')); expected=cfg['services']['nats']['image']
        check(cmd('docker','image','inspect','-f','{{.Os}}/{{.Architecture}}',expected)=='linux/amd64','pinned linux/amd64 image available')
        started=True
        compose('up','-d','--pull','never');c=ready(pw);wrong=Client('wrong');check(not wrong.ok,'incorrect credentials refused');wrong.close()
        z=json.loads(cmd('docker','inspect','nats'))[0];h=z['HostConfig']
        check(z['Config']['Image']==expected and z['Config']['User']=='1000:1000' and h['ReadonlyRootfs'] and 'ALL' in h['CapDrop'] and any('no-new-privileges' in x for x in h['SecurityOpt']),'running digest reference, UID and hardening')
        check(h['PortBindings']=={'4222/tcp':[{'HostIp':'127.0.0.1','HostPort':'14222'}]},'only host loopback client port published')
        q=ready(pw); q.send('SUB pilot.jobs workers 1\r\nPING\r\n');check(q.f.readline()==b'PONG\r\n','queue group registered')
        c.send('SUB _INBOX.r 1\r\nPUB pilot.jobs _INBOX.r 3\r\njob\r\n');hdr,body=q.msg();assert body==b'job' and hdr[3]==b'_INBOX.r'
        q.send('PUB _INBOX.r 4\r\ndone\r\n');check(c.msg()[1]==b'done','queue worker replies to synthetic request');q.close()
        result=c.req('$JS.API.STREAM.CREATE.PILOT',json.dumps(dict(name='PILOT',subjects=['pilot.events'],storage='file',num_replicas=1)))
        assert result['config']['storage']=='file'
        check(c.req('pilot.events','synthetic')['seq']==1,'JetStream acknowledged stored message');c.close()
        compose('down');compose('up','-d','--pull','never');c=ready(pw)
        msg=c.req('$JS.API.STREAM.MSG.GET.PILOT','{"seq":1}')['message'];check(base64.b64decode(msg['data'])==b'synthetic','same payload after container recreation');c.close()
    finally:
        try:
            if started:compose('down','--volumes')
        finally:
            os.chdir(prev);shutil.rmtree(root)
        check(not cmd('docker','ps','-aq','--filter','label=com.docker.compose.project='+project) and not cmd('docker','network','ls','-q','--filter','label=com.docker.compose.project='+project) and not root.exists(),'own resources and credentials cleaned')
if __name__=='__main__':main(Path(sys.argv[1]).read_bytes())

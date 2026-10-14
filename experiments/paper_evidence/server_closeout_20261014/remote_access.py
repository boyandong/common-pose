"""Bounded clone transport. Authentication enters stdin and is never persisted."""
import hashlib
import getpass
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'runtime_transport'))
sys.stdout.reconfigure(encoding='utf-8')
import paramiko

HOST='connect.westd.seetacloud.com';PORT=29596
pinfile=HERE/'HOST_IDENTITY.json'
expected=json.loads(pinfile.read_text())['host_key_sha256'] if pinfile.exists() else None


class PinPolicy(paramiko.MissingHostKeyPolicy):
    def missing_host_key(self,client,hostname,key):
        digest=hashlib.sha256(key.asbytes()).hexdigest()
        if expected and digest!=expected:raise RuntimeError('Host identity changed')
        if not expected:pinfile.write_text(json.dumps({'host':HOST,'port':PORT,'host_key_sha256':digest,'trust':'first observation on user-authorized clone'},indent=2)+'\n')


print('AWAITING_AUTH_ON_STDIN',flush=True)
secret=getpass.getpass('Server authentication: ')
client=paramiko.SSHClient();client.set_missing_host_key_policy(PinPolicy())
client.connect(HOST,port=PORT,username='root',password=secret,allow_agent=False,look_for_keys=False,timeout=20,auth_timeout=20,banner_timeout=20)
del secret
sftp=client.open_sftp();print('AUTHENTICATED_CLONE_READY',flush=True)
try:
    for line in sys.stdin:
        request=json.loads(line)
        if request['action']=='close':print('CLOSED',flush=True);break
        if request['action']=='exec':
            _,out,err=client.exec_command(request['command'],timeout=request.get('timeout',55))
            result={'exit_code':out.channel.recv_exit_status(),'stdout':out.read().decode('utf-8','replace'),'stderr':err.read().decode('utf-8','replace')}
            if request.get('save'):Path(request['save']).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(result,ensure_ascii=False),flush=True)
        elif request['action']=='put':
            sftp.put(request['local'],request['remote']);print(json.dumps({'status':'UPLOADED','remote':request['remote']}),flush=True)
        elif request['action']=='get':
            p=Path(request['local']);p.parent.mkdir(parents=True,exist_ok=True);sftp.get(request['remote'],str(p))
            print(json.dumps({'status':'DOWNLOADED','local':str(p),'bytes':p.stat().st_size}),flush=True)
        else:raise ValueError('Unknown action')
finally:
    sftp.close();client.close()

import os, json, hashlib, urllib.request, time

TOKEN  = 'nfp_mfk8bRwxEcaE5zxJkeHPu1dcDisCVdvYa3bf'
FOLDER = '/tmp/proposal-demo-v5/'
SITE_NAME = 'd1-proposal-v5'

def api(path, method='GET', data=None, content_type='application/json'):
    req = urllib.request.Request(
        f'https://api.netlify.com/api/v1{path}', data=data,
        headers={'Content-Type': content_type, 'Authorization': f'Bearer {TOKEN}'},
        method=method)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

html_path = os.path.join(FOLDER, 'index.html')
with open(html_path, 'rb') as f:
    html_content = f.read()
sha1 = hashlib.sha1(html_content).hexdigest()
print(f'HTML: {len(html_content)//1024} KB')

try:
    site = api('/sites', method='POST', data=json.dumps({'name': SITE_NAME}).encode())
except:
    SITE_NAME = f'{SITE_NAME}-{int(time.time())}'
    site = api('/sites', method='POST', data=json.dumps({'name': SITE_NAME}).encode())

site_id = site['id']
deploy = api(f'/sites/{site_id}/deploys', method='POST',
    data=json.dumps({'files': {'/index.html': sha1}, 'async': False}).encode())
deploy_id = deploy['id']
api(f'/deploys/{deploy_id}/files/index.html', method='PUT',
    data=html_content, content_type='text/html; charset=utf-8')

for _ in range(10):
    d = api(f'/deploys/{deploy_id}')
    if d.get('state') == 'ready': break
    time.sleep(2)

print(f'Live: https://{SITE_NAME}.netlify.app')

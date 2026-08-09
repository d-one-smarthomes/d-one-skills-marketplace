#!/usr/bin/env python3
"""
Publish the proposal option photos to the live image host.

WHAT THIS IS FOR
    The proposal cards hot-link their photos from a hosted image site
    (config/image_host.json > base_url). To CHANGE a photo you never edit the
    skill: you replace the file in the Google Drive source folder, then run this
    script once to push the folder up to the host. Every proposal — new and
    already-sent — then shows the new photo.

WHERE TO CHANGE THE PHOTOS
    config/image_host.json > "source_folder", laid out as:
        <Category>/<System>/<Tier>/<one image file>
    e.g. .../Proposal skill images/Security/CCTV/Entry/whatever.jpg
    Exactly ONE image per Tier folder. Any format (jpg/png/webp/jpeg) and any
    filename — this script normalises each to <system-slug>/<tier>.jpg on the host.

RUN IT (on a machine that can see the Drive folder AND reach Netlify — i.e. the Mac):
    python3 scripts/publish_images.py
    python3 scripts/publish_images.py --dry-run      # build the tree, don't deploy

Requires config/netlify.json (token) and config/image_host.json (base_url, source_folder, slug_map).
macOS 'sips' is used to convert to JPG; falls back to Pillow if available.
"""
import os, sys, json, io, zipfile, subprocess, tempfile, urllib.request, urllib.error, time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
HOST_CFG = os.path.join(SKILL_DIR, 'config', 'image_host.json')
NETLIFY_CFG = os.path.join(SKILL_DIR, 'config', 'netlify.json')
TIERS = ['Entry', 'Mid', 'Premium']
EXTS = ('.jpg', '.jpeg', '.png', '.webp')
API = 'https://api.netlify.com/api/v1'


def load(p):
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_one_image(folder):
    if not os.path.isdir(folder):
        return None
    files = [f for f in sorted(os.listdir(folder))
             if not f.startswith('.') and f.lower().endswith(EXTS)]
    return os.path.join(folder, files[0]) if files else None


def to_jpg(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    # macOS sips first
    try:
        r = subprocess.run(['sips', '-s', 'format', 'jpeg', src, '--out', dst],
                           capture_output=True)
        if r.returncode == 0 and os.path.exists(dst):
            return True
    except FileNotFoundError:
        pass
    # Pillow fallback
    try:
        from PIL import Image
        im = Image.open(src).convert('RGB')
        im.save(dst, 'JPEG', quality=90)
        return True
    except Exception as e:
        print(f"  ! convert failed for {src}: {e}")
        return False


def build_tree(cfg, out_dir):
    src_root = cfg['source_folder']
    slug_map = cfg['slug_map']
    made, missing = [], []
    for slug, rel in slug_map.items():
        for tier in TIERS:
            folder = os.path.join(src_root, rel, tier)
            src = find_one_image(folder)
            if not src:
                missing.append(f"{slug}/{tier}")
                continue
            dst = os.path.join(out_dir, slug, f"{tier.lower()}.jpg")
            if to_jpg(src, dst):
                made.append(f"{slug}/{tier.lower()}.jpg  <= {os.path.basename(src)}")
    return made, missing


def netlify_req(path, token, method='GET', data=None, ctype='application/json'):
    hdr = {'Authorization': 'Bearer ' + token}
    body = None
    if data is not None:
        if ctype == 'application/json':
            body = json.dumps(data).encode(); hdr['Content-Type'] = 'application/json'
        else:
            body = data; hdr['Content-Type'] = ctype
    req = urllib.request.Request(API + path, data=body, headers=hdr, method=method)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def deploy(out_dir, token, site_name):
    sites = netlify_req('/sites?per_page=100', token)
    site = next((s for s in sites if s.get('name') == site_name), None)
    if not site:
        site = netlify_req('/sites', token, 'POST', {'name': site_name})
        print('created site', site_name)
    sid = site['id']
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(out_dir):
            for fn in files:
                fp = os.path.join(root, fn)
                z.write(fp, os.path.relpath(fp, out_dir))
    netlify_req(f'/sites/{sid}/deploys', token, 'POST', buf.getvalue(), 'application/zip')
    time.sleep(4)
    info = netlify_req(f'/sites/{sid}', token)
    return info.get('ssl_url') or info.get('url')


def main():
    dry = '--dry-run' in sys.argv
    cfg = load(HOST_CFG)
    base = (cfg.get('base_url') or '').rstrip('/')
    site_name = base.split('//')[-1].split('.')[0] if base else 'd-one-proposal-images'
    out_dir = tempfile.mkdtemp(prefix='proposal-images-')
    made, missing = build_tree(cfg, out_dir)
    for m in made:
        print('ok ', m)
    for m in missing:
        print('MISSING', m)
    print(f"\n{len(made)} images staged in {out_dir}")
    if dry:
        print("--dry-run: not deploying"); return
    token = load(NETLIFY_CFG)['token']
    url = deploy(out_dir, token, site_name)
    print("\nLIVE:", url)
    print("Sample:", f"{url}/cctv/entry.jpg")


if __name__ == '__main__':
    main()

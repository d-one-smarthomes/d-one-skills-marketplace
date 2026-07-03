#!/usr/bin/env python3
"""
Deploy a proposal folder to Netlify and return the live URL.

Usage:
    python deploy.py <proposal_folder> [--site-name <name>]

The proposal_folder should contain:
    index.html

Returns JSON with url and site_id on success.
"""

import sys
import os
import json
import zipfile
import tempfile
import urllib.request
import urllib.error
import argparse
import re
import time

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'netlify.json')


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def zip_folder(folder_path):
    tmp = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
    with zipfile.ZipFile(tmp.name, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zf.write(file_path, arcname)
    return tmp.name


def sanitise_name(name):
    """Convert a client/project name into a valid Netlify site slug."""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug[:40]


def netlify_request(path, method='GET', data=None, content_type='application/json', token=None):
    url = f'https://api.netlify.com/api/v1{path}'
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            'Content-Type': content_type,
            'Authorization': f'Bearer {token}',
        },
        method=method
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def deploy(folder_path, site_name=None):
    config = load_config()
    token = config['token']
    prefix = config.get('site_name_prefix', 'd1')

    slug = f"{prefix}-{sanitise_name(site_name)}" if site_name else f"{prefix}-{int(time.time())}"

    zip_path = zip_folder(folder_path)

    try:
        # Step 1: Create a named site
        site_body = json.dumps({"name": slug}).encode()
        site = netlify_request('/sites', method='POST', data=site_body, token=token)
        site_id = site['id']

        # Step 2: Deploy the zip to that site
        with open(zip_path, 'rb') as f:
            zip_data = f.read()

        deploy_result = netlify_request(
            f'/sites/{site_id}/deploys',
            method='POST',
            data=zip_data,
            content_type='application/zip',
            token=token
        )

        # Wait briefly for deploy to propagate
        time.sleep(2)

        # Step 3: Get the site's canonical URL
        site_info = netlify_request(f'/sites/{site_id}', token=token)
        site_url = site_info.get('ssl_url') or site_info.get('url')

        print(json.dumps({
            'success': True,
            'url': site_url,
            'site_id': site_id,
            'slug': slug,
        }))
        return site_url

    except urllib.error.HTTPError as e:
        body = e.read().decode()
        # If slug is taken, append timestamp and retry once
        if e.code == 422 and 'taken' in body.lower():
            slug = f"{slug}-{int(time.time())}"
            site_body = json.dumps({"name": slug}).encode()
            site = netlify_request('/sites', method='POST', data=site_body, token=token)
            site_id = site['id']
            with open(zip_path, 'rb') as f:
                zip_data = f.read()
            netlify_request(f'/sites/{site_id}/deploys', method='POST', data=zip_data,
                           content_type='application/zip', token=token)
            time.sleep(2)
            site_info = netlify_request(f'/sites/{site_id}', token=token)
            site_url = site_info.get('ssl_url') or site_info.get('url')
            print(json.dumps({'success': True, 'url': site_url, 'site_id': site_id, 'slug': slug}))
            return site_url
        print(json.dumps({'success': False, 'error': f"HTTP {e.code}: {body}"}), file=sys.stderr)
        sys.exit(1)
    finally:
        os.unlink(zip_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', help='Path to the proposal folder to deploy')
    parser.add_argument('--site-name', help='Client or project name for the URL slug')
    args = parser.parse_args()

    deploy(args.folder, args.site_name)

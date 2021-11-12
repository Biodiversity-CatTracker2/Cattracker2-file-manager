import os
import warnings
from datetime import datetime
from pathlib import Path

import requests
from dateparser import parse
from dotenv import load_dotenv
from yourls import YOURLSClient, exceptions

warnings.filterwarnings('ignore')


def check_token_expiry():
    if not Path('.timestamp').exists():
        with open('.timestamp', 'w') as f:
            f.write(str(datetime.now()))
    with open('.timestamp', 'r+') as f:
        diff = datetime.now() - parse(f.read())
        if diff.total_seconds() >= 3600:
            f.seek(0)
            f.write(str(datetime.now()))
            f.truncate()
            return diff.total_seconds(), True
        else:
            return diff.total_seconds(), False


def return_tokens():
    time_diff, expired = check_token_expiry()
    if not expired:
        return os.environ['UPLOAD_TOKEN'], os.environ['WEBLINK_TOKEN']
    data = {
        'username': os.environ['FILERUN_USERNAME'],
        'password': os.environ['FILERUN_PASSWORD'],
        'client_id': os.environ['FILERUN_CLIENT_ID'],
        'client_secret': os.environ['FILERUN_CLIENT_SECRET'],
        'redirect_uri': 'http://localhost',
        'grant_type': 'password'
    }
    tokens = []
    for scope in ['upload', 'weblink']:
        data.update({'scope': scope})
        response = requests.post('https://cattracker.app/files/oauth2/token/',
                                 data=data)
        tokens.append(response.json()['access_token'])
    with open('.env', 'r+') as f:
        lines = f.readlines()
        lines[-2] = f'UPLOAD_TOKEN={tokens[0]}' + '\n'
        lines[-1] = f'WEBLINK_TOKEN={tokens[1]}' + '\n'
        f.seek(0)
        f.writelines(lines)
    return tokens


def upload(file, upload_token):
    file_name = Path(file).name
    os.popen(
        f"curl -sX PUT --header 'Authorization: Bearer {upload_token}' -T '{file}' 'https://cattracker.app/files/api.php/files/upload/?path=/ROOT/HOME/{file_name}'"
    ).read()


def get_download_link(file, weblink_token):
    file_name = Path(file).name
    url = 'https://cattracker.app/files/api.php/files/weblink'
    payload = {'Authorization': f'Bearer {weblink_token}'}
    data = {'path': f'/ROOT/HOME/{file_name}'}
    res = requests.post(url, headers=payload, data=data)
    res_json = res.json()
    link = res_json['data']['url'] + '&fmode=download'
    return link


def shorten_url(long_url, signature):
    yourls = YOURLSClient('https://cattracker.app/u/yourls-api.php',
                          signature=signature)
    short_link = yourls.shorten(long_url)
    return short_link


def main(file):
    upload_token, weblink_token = return_tokens()
    signature = os.environ['YOURLS_SIGNATURE']
    upload(file, upload_token)
    long_url = get_download_link(file, weblink_token)
    try:
        short_url = shorten_url(long_url, signature)
    except exceptions.YOURLSURLExistsError as e:
        return e
    assert short_url.url == long_url
    return short_url.shorturl


if __name__ == '__main__':
    file = '.placeholder'
    load_dotenv()
    url = main(file)
    print(url)

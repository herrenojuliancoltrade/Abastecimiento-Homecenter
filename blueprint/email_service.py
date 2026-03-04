import json
import os
import base64
from email.mime.text import MIMEText
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode


def send_email(to_email, subject, body):
    provider = os.getenv('MAIL_PROVIDER', 'gmail_api').strip().lower()
    if provider != 'gmail_api':
        raise RuntimeError('MAIL_PROVIDER debe ser gmail_api.')
    _send_with_gmail_api(to_email, subject, body)


def _send_with_gmail_api(to_email, subject, body):
    client_id = os.getenv('GMAIL_CLIENT_ID', '').strip()
    client_secret = os.getenv('GMAIL_CLIENT_SECRET', '').strip()
    refresh_token = os.getenv('GMAIL_REFRESH_TOKEN', '').strip()
    from_email = os.getenv('GMAIL_FROM', '').strip()

    if not client_id or not client_secret or not refresh_token or not from_email:
        raise RuntimeError(
            'Configura GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN y GMAIL_FROM.'
        )

    access_token = _gmail_access_token(client_id, client_secret, refresh_token)

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['To'] = to_email
    msg['From'] = from_email
    msg['Subject'] = subject
    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')

    payload = {'raw': raw_message}
    req = urlrequest.Request(
        'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'herramienta-hc/1.0'
        },
        method='POST'
    )
    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            if resp.status >= 300:
                raise RuntimeError(f'Gmail API respondio estado {resp.status}')
    except HTTPError as e:
        detail = e.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'Error Gmail API HTTP {e.code}: {detail}') from e
    except URLError as e:
        raise RuntimeError(f'No se pudo conectar a Gmail API: {e}') from e


def _gmail_access_token(client_id, client_secret, refresh_token):
    token_url = 'https://oauth2.googleapis.com/token'
    data = urlencode({
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token'
    }).encode('utf-8')
    req = urlrequest.Request(
        token_url,
        data=data,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'herramienta-hc/1.0'
        },
        method='POST'
    )
    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode('utf-8', errors='replace'))
            token = (payload or {}).get('access_token')
            if not token:
                raise RuntimeError(f'No se recibio access_token de Google: {payload}')
            return token
    except HTTPError as e:
        detail = e.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'Error token Google HTTP {e.code}: {detail}') from e
    except URLError as e:
        raise RuntimeError(f'No se pudo conectar al token endpoint de Google: {e}') from e

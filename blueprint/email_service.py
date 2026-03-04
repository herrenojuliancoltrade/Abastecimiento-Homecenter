import json
import os
import smtplib
from email.mime.text import MIMEText
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError


def send_email(to_email, subject, body):
    provider = os.getenv('MAIL_PROVIDER', 'auto').strip().lower()
    if provider == 'auto':
        provider = 'resend' if _is_render_environment() else 'smtp'

    if provider == 'resend':
        _send_with_resend(to_email, subject, body)
        return
    _send_with_smtp(to_email, subject, body)


def _is_render_environment():
    # Render expone estas variables en runtime.
    return any(
        os.getenv(var, '').strip()
        for var in ('RENDER', 'RENDER_SERVICE_ID', 'RENDER_EXTERNAL_HOSTNAME')
    )


def _send_with_smtp(to_email, subject, body):
    smtp_host = os.getenv('SMTP_HOST', '').strip()
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER', '').strip()
    smtp_password = os.getenv('SMTP_PASS', '').strip()
    from_email = os.getenv('SMTP_FROM', smtp_user).strip()
    use_tls = os.getenv('SMTP_USE_TLS', 'true').strip().lower() in ('1', 'true', 'yes', 'y')
    use_ssl = os.getenv('SMTP_USE_SSL', 'false').strip().lower() in ('1', 'true', 'yes', 'y')

    if not smtp_host or not smtp_user or not smtp_password or not from_email:
        raise RuntimeError('Configura SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS y SMTP_FROM.')

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    if use_ssl or smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, [to_email], msg.as_string())
        return

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        server.ehlo()
        if use_tls:
            server.starttls()
            server.ehlo()
        server.login(smtp_user, smtp_password)
        server.sendmail(from_email, [to_email], msg.as_string())


def _send_with_resend(to_email, subject, body):
    api_key = os.getenv('RESEND_API_KEY', '').strip()
    from_email = os.getenv('RESEND_FROM', os.getenv('MAIL_FROM', os.getenv('SMTP_FROM', ''))).strip()
    if not api_key or not from_email:
        raise RuntimeError('Configura RESEND_API_KEY y RESEND_FROM (o MAIL_FROM) para usar Resend.')

    payload = {
        'from': from_email,
        'to': [to_email],
        'subject': subject,
        'text': body
    }

    req = urlrequest.Request(
        'https://api.resend.com/emails',
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        },
        method='POST'
    )
    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            if resp.status >= 300:
                raise RuntimeError(f'Resend respondio estado {resp.status}')
    except HTTPError as e:
        detail = e.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'Error Resend HTTP {e.code}: {detail}') from e
    except URLError as e:
        raise RuntimeError(f'No se pudo conectar a Resend: {e}') from e

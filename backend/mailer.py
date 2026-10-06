"""
Email notifications for completed analysis jobs.

SMTP settings are read from environment variables (set in docker-compose.yml):

    SMTP_HOST          SMTP server hostname. If empty, notifications are disabled.
    SMTP_PORT          Port (default: 587).
    SMTP_SECURITY      "starttls" (default), "ssl" (implicit TLS, usually port 465)
                       or "none" (plain, only for trusted internal relays).
    SMTP_USER          Login user (optional; no login if empty).
    SMTP_PASSWORD      Login password (optional).
    SMTP_FROM          Sender address, e.g. "COCOMAPS-MD <no-reply@example.org>".
                       Defaults to SMTP_USER.
    SMTP_TIMEOUT       Socket timeout in seconds (default: 20).
    COCOMAPS_PUBLIC_URL  Public base URL of the web app, including the path prefix,
                       e.g. https://example.org/BioTools/COCOMAPS-MD
                       Used to build the link to the results. Required: the
                       backend cannot reliably know its public address behind
                       nginx / an institutional proxy.

Sending is strictly best-effort: a mail failure never affects the job status.
"""
import logging
import os
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from urllib.parse import quote

logger = logging.getLogger(__name__)

DEFAULT_SMTP_PORT = 587
DEFAULT_SMTP_TIMEOUT = 20

# Deliberately simple: one address, no whitespace/control chars, one "@".
_EMAIL_RE = re.compile(r'^[^@\s<>,;"\']+@[^@\s<>,;"\']+\.[^@\s<>,;"\']+$')
MAX_EMAIL_LENGTH = 254


def is_valid_email(address):
    """Return True if `address` looks like a single, safe email address."""
    if not isinstance(address, str):
        return False
    address = address.strip()
    if not address or len(address) > MAX_EMAIL_LENGTH:
        return False
    return bool(_EMAIL_RE.match(address))


def _env(name, default=''):
    return (os.environ.get(name) or default).strip()


def get_smtp_config():
    """Read SMTP settings from the environment on every call (easy to test)."""
    try:
        port = int(_env('SMTP_PORT', str(DEFAULT_SMTP_PORT)))
    except ValueError:
        port = DEFAULT_SMTP_PORT
    try:
        timeout = float(_env('SMTP_TIMEOUT', str(DEFAULT_SMTP_TIMEOUT)))
    except ValueError:
        timeout = DEFAULT_SMTP_TIMEOUT

    security = _env('SMTP_SECURITY', 'starttls').lower()
    if security not in {'starttls', 'ssl', 'none'}:
        logger.warning("Unknown SMTP_SECURITY=%r, falling back to 'starttls'", security)
        security = 'starttls'

    user = _env('SMTP_USER')
    return {
        'host': _env('SMTP_HOST'),
        'port': port,
        'security': security,
        'user': user,
        'password': os.environ.get('SMTP_PASSWORD', ''),
        'sender': _env('SMTP_FROM') or user,
        'timeout': timeout,
        'public_url': _env('COCOMAPS_PUBLIC_URL').rstrip('/'),
    }


def is_configured(config=None):
    """True when notifications can actually be sent."""
    config = config or get_smtp_config()
    return bool(config['host'] and config['sender'] and config['public_url'])


def build_analysis_url(analysis_job_id, config=None):
    """Public link to the results page (Vue router: /analysis/<jobId>)."""
    config = config or get_smtp_config()
    return f"{config['public_url']}/analysis/{quote(str(analysis_job_id), safe='')}"


def _build_message(config, to_address, job_name, analysis_job_id, expires_at=None):
    url = build_analysis_url(analysis_job_id, config)
    # Strip control characters from user-controlled text used in the subject.
    safe_name = re.sub(r'[\r\n\t]+', ' ', job_name or '').strip() or analysis_job_id

    lines = [
        'Hello,',
        '',
        f'your COCOMAPS-MD analysis "{safe_name}" is complete.',
        '',
        f'Job ID: {analysis_job_id}',
        f'Results: {url}',
        '',
    ]
    if expires_at:
        lines.append(f'The results will be available until {expires_at}.')
        lines.append('')
    lines += [
        'Anyone with this link can view the results, so share it with care.',
        '',
        'You are receiving this message because this address was entered in the '
        'Advanced Settings of a COCOMAPS-MD job. If this was not you, you can '
        'ignore this email.',
    ]

    msg = EmailMessage()
    msg['Subject'] = f'COCOMAPS-MD: your results are ready ({safe_name})'
    msg['From'] = config['sender']
    msg['To'] = formataddr(parseaddr(to_address))
    msg.set_content('\n'.join(lines))
    return msg


def _send(config, msg):
    context = ssl.create_default_context()
    if config['security'] == 'ssl':
        server = smtplib.SMTP_SSL(
            config['host'], config['port'], timeout=config['timeout'], context=context
        )
    else:
        server = smtplib.SMTP(config['host'], config['port'], timeout=config['timeout'])
    with server:
        if config['security'] == 'starttls':
            server.starttls(context=context)
        if config['user']:
            server.login(config['user'], config['password'])
        server.send_message(msg)


def send_job_completed_email(to_address, job_name, analysis_job_id, expires_at=None):
    """
    Send the "results are ready" email.

    Returns True if the message was handed to the SMTP server, False otherwise
    (disabled, invalid recipient, or SMTP error). Never raises.
    """
    config = get_smtp_config()

    if not to_address:
        return False
    if not analysis_job_id:
        logger.warning("Email not sent: job has no public analysis job ID")
        return False
    if not is_configured(config):
        logger.info(
            "Email notifications disabled (set SMTP_HOST, SMTP_FROM/SMTP_USER and "
            "COCOMAPS_PUBLIC_URL to enable them)"
        )
        return False
    if not is_valid_email(to_address):
        logger.warning("Email not sent: invalid recipient address")
        return False

    try:
        msg = _build_message(config, to_address.strip(), job_name, analysis_job_id, expires_at)
        _send(config, msg)
    except Exception as exc:  # smtplib.SMTPException, OSError, ssl.SSLError, ...
        logger.error("Could not send completion email for job %s: %s", analysis_job_id, exc)
        return False

    logger.info("Completion email sent for job %s", analysis_job_id)
    return True

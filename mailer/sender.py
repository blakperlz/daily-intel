"""
Email sender — Gmail SMTP with HTML + plain text fallback.
Scale-up path: set EMAIL_PROVIDER=resend in .env to switch to Resend.com.
"""
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, Any, List

from jinja2 import Environment, FileSystemLoader

from utils.config_loader import get_config, get_secret

TEMPLATE_DIR = Path(__file__).parent / "templates"


def render_digest(digest: Dict[str, Any], digest_type: str, item_count: int) -> tuple[str, str]:
    """Render HTML and plain text versions of the digest."""
    now = datetime.now()

    if digest_type == "weekly":
        title = f"Weekly Intelligence Summary — {now.strftime('%B %d, %Y')}"
    elif now.hour < 12:
        title = f"Morning Intelligence Brief — {now.strftime('%A, %B %d')}"
    else:
        title = f"Evening Intelligence Recap — {now.strftime('%A, %B %d')}"

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("digest.html")

    html = template.render(
        title=title,
        date_str=now.strftime("%A, %B %d, %Y"),
        time_str=now.strftime("%I:%M %p"),
        digest=digest,
        item_count=item_count,
    )

    # Simple plain text fallback
    plain = _build_plain_text(title, digest)

    return html, plain, title


def _build_plain_text(title: str, digest: Dict[str, Any]) -> str:
    subject = digest.get("subject_line") or title
    lines = [
        subject,
        "=" * len(subject),
        "",
        "EXECUTIVE BRIEF",
        "-" * 30,
        digest.get("executive_brief", ""),
        "",
    ]

    for section in digest.get("sections", []):
        lines += [section.get("title", "").upper(), "-" * 30]
        if section.get("summary"):
            lines += [section["summary"], ""]
        for article in section.get("articles", []):
            lines.append(f"  ▸ {article.get('headline', '')}")
            if article.get("snippet"):
                lines.append(f"    {article['snippet']}")
            if article.get("source_url"):
                lines.append(f"    {article['source_url']}")
            lines.append("")

    if digest.get("next_week_watchlist"):
        lines += ["NEXT WEEK WATCHLIST", "-" * 30]
        for item in digest["next_week_watchlist"]:
            if isinstance(item, dict):
                lines.append(f"  • {item.get('item', '')}")
                if item.get("why"):
                    lines.append(f"    {item['why']}")
            else:
                lines.append(f"  • {item}")
        lines.append("")

    if digest.get("confidence_note"):
        lines += ["NOTE", "-" * 30, digest["confidence_note"], ""]

    lines += [
        "---",
        "daily-intel | github.com/blakperlz/daily-intel",
        "For informational purposes only. Not financial or legal advice.",
    ]

    return "\n".join(lines)


def send_digest(digest: Dict[str, Any], digest_type: str, item_count: int) -> bool:
    """Render and send the digest to all configured recipients."""
    cfg = get_config()
    recipients = cfg["digest"]["recipients"]
    gmail_user = get_secret("GMAIL_USER")
    gmail_pass = get_secret("GMAIL_APP_PASSWORD")

    if not gmail_user or not gmail_pass:
        raise ValueError("GMAIL_USER and GMAIL_APP_PASSWORD must be set in .env")

    html, plain, title = render_digest(digest, digest_type, item_count)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = digest.get("subject_line") or title
    msg["From"] = f"daily-intel <{gmail_user}>"
    msg["To"] = ", ".join(recipients)

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, recipients, msg.as_string())

    print(f"[email] Sent '{title}' to {len(recipients)} recipient(s)")
    return True

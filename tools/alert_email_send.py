#!/usr/bin/env python3
"""
alert_email_send.py — send a plain-text alert email, reusing the daily-digest
Gmail-SMTP credentials stored in the DB (no duplicated secrets, no new deps).

Body is read from STDIN so alert text never lands in argv / process listings.

  echo "..." | py -3 alert_email_send.py --subject "Trading Bramha Alert"
  py -3 alert_email_send.py --check        # exit 0 if creds configured, else 2
"""
from __future__ import annotations

import argparse
import smtplib
import sys
from email.mime.text import MIMEText
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daily_digest_email import get_credentials   # reuse the exact credential path


def main() -> None:
    ap = argparse.ArgumentParser(description="Send a plain-text alert email.")
    ap.add_argument("--subject", default="Trading Bramha Alert")
    ap.add_argument("--to", help="override recipient (default: DB digest_to_email)")
    ap.add_argument("--check", action="store_true",
                    help="report whether credentials are configured, then exit")
    args = ap.parse_args()

    sender, pw, recipient = get_credentials()
    recipient = args.to or recipient

    if args.check:
        ok = bool(sender and pw and recipient)
        print("ok" if ok else "missing")
        sys.exit(0 if ok else 2)

    if not (sender and pw and recipient):
        sys.stderr.write("no gmail credentials — run: "
                         "python daily_digest_email.py --configure\n")
        sys.exit(2)

    body = sys.stdin.read()
    if not body.strip():
        sys.stderr.write("empty body\n")
        sys.exit(3)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = args.subject
    msg["From"] = sender
    msg["To"] = recipient
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, pw)
        smtp.sendmail(sender, [recipient], msg.as_bytes())
    print(f"sent to {recipient}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
email_delivery.py — Automated email delivery system for Trading Bramha reports.

Sends formatted Excel reports via email with:
  • SMTP configuration via environment variables or config file
  • HTML email templates with embedded summary data
  • Multiple file attachments (Excel, PDF, images)
  • Configurable recipient lists per report type
  • Retry logic with exponential backoff
  • Support for Gmail, Outlook, custom SMTP servers
  • Optional authentication and TLS/SSL
  • Dry-run mode for testing

Configuration via environment variables:
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=your-email@gmail.com
    SMTP_PASSWORD=your-app-password
    SMTP_FROM_NAME=Trading Bramha
    SMTP_USE_TLS=true

Or via config file (email_config.yaml).

Usage:
    # Quick send
    send_email(
        to=["trader@example.com"],
        subject="Daily Batch Report",
        body_html="<h2>Report attached</h2>",
        attachments=["report.xlsx"],
    )

    # Using templates
    sender = EmailSender()
    sender.send_batch_report(
        report_paths={"entry": "entry.xlsx", "confluence": "confluence.xlsx"},
        summary_data={"total_signals": 45, "high_conviction": 12},
        recipients=["team@example.com"],
    )
"""

from __future__ import annotations

import logging
import os
import smtplib
import time
from dataclasses import dataclass, field
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────


@dataclass
class SMTPConfig:
    """SMTP server configuration."""

    host: str = "smtp.gmail.com"
    port: int = 587
    username: str = ""
    password: str = ""
    from_email: str = ""
    from_name: str = "Trading Bramha"
    use_tls: bool = True
    use_ssl: bool = False
    timeout: int = 30

    @classmethod
    def from_env(cls) -> SMTPConfig:
        """Load configuration from environment variables."""
        return cls(
            host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            port=int(os.getenv("SMTP_PORT", "587")),
            username=os.getenv("SMTP_USER", ""),
            password=os.getenv("SMTP_PASSWORD", ""),
            from_email=os.getenv("SMTP_FROM_EMAIL") or os.getenv("SMTP_USER", ""),
            from_name=os.getenv("SMTP_FROM_NAME", "Trading Bramha"),
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            use_ssl=os.getenv("SMTP_USE_SSL", "false").lower() == "true",
            timeout=int(os.getenv("SMTP_TIMEOUT", "30")),
        )

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> SMTPConfig:
        """Load configuration from YAML file."""
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path) as f:
            data = yaml.safe_load(f)

        smtp = data.get("smtp", {})
        return cls(
            host=smtp.get("host", "smtp.gmail.com"),
            port=smtp.get("port", 587),
            username=smtp.get("username", ""),
            password=smtp.get("password", ""),
            from_email=smtp.get("from_email") or smtp.get("username", ""),
            from_name=smtp.get("from_name", "Trading Bramha"),
            use_tls=smtp.get("use_tls", True),
            use_ssl=smtp.get("use_ssl", False),
            timeout=smtp.get("timeout", 30),
        )


@dataclass
class RecipientConfig:
    """Recipient lists for different report types."""

    batch_report: list[str] = field(default_factory=list)
    entry_signals: list[str] = field(default_factory=list)
    risk_alerts: list[str] = field(default_factory=list)
    confluence: list[str] = field(default_factory=list)
    portfolio_risk: list[str] = field(default_factory=list)
    daily_digest: list[str] = field(default_factory=list)
    all_reports: list[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> RecipientConfig:
        """Load recipient configuration from YAML file."""
        config_path = Path(config_path)
        if not config_path.exists():
            log.warning(f"Recipient config not found: {config_path}, using defaults")
            return cls()

        with open(config_path) as f:
            data = yaml.safe_load(f)

        recipients = data.get("recipients", {})
        return cls(
            batch_report=recipients.get("batch_report", []),
            entry_signals=recipients.get("entry_signals", []),
            risk_alerts=recipients.get("risk_alerts", []),
            confluence=recipients.get("confluence", []),
            portfolio_risk=recipients.get("portfolio_risk", []),
            daily_digest=recipients.get("daily_digest", []),
            all_reports=recipients.get("all_reports", []),
        )


# ── Email Templates ───────────────────────────────────────────────────────────


class EmailTemplates:
    """HTML email templates for different report types."""

    @staticmethod
    def base_template(title: str, content: str, footer: str = None) -> str:
        """Base HTML template with styling."""
        if footer is None:
            footer = """
            <p style="color: #666; font-size: 12px; margin-top: 30px;">
                This is an automated report from Trading Bramha.<br>
                Questions? Reply to this email.
            </p>
            """

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{
            color: #1F4E78;
            border-bottom: 3px solid #1F4E78;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #2C5F8D;
            margin-top: 25px;
        }}
        .metric-box {{
            background: #f8f9fa;
            border-left: 4px solid #1F4E78;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        .metric-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #ddd;
        }}
        .metric-label {{
            font-weight: 600;
            color: #555;
        }}
        .metric-value {{
            color: #1F4E78;
            font-weight: 700;
        }}
        .high-conviction {{
            color: #27AE60;
            font-weight: 700;
        }}
        .risk-flag {{
            color: #E74C3C;
            font-weight: 700;
        }}
        .attachment-list {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .attachment-item {{
            padding: 5px 0;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #ddd;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {content}
    <div class="footer">
        {footer}
    </div>
</body>
</html>
"""

    @staticmethod
    def batch_report(summary_data: dict[str, Any], report_names: list[str]) -> str:
        """Template for batch scanner reports."""
        metrics_html = ""
        for key, value in summary_data.items():
            label = key.replace("_", " ").title()

            # Special formatting for certain metrics
            if "conviction" in key.lower():
                value_class = "high-conviction"
            elif "risk" in key.lower():
                value_class = "risk-flag"
            else:
                value_class = "metric-value"

            metrics_html += f"""
            <div class="metric-row">
                <span class="metric-label">{label}</span>
                <span class="{value_class}">{value}</span>
            </div>
            """

        attachments_html = ""
        if report_names:
            attachments_html = '<div class="attachment-list"><strong>📎 Attached Reports:</strong>'
            for name in report_names:
                attachments_html += f'<div class="attachment-item">• {name}</div>'
            attachments_html += "</div>"

        content = f"""
        <p>Your daily batch scanner report is ready.</p>

        <div class="metric-box">
            <h3 style="margin-top: 0;">Summary</h3>
            {metrics_html}
        </div>

        {attachments_html}

        <h2>What's Included</h2>
        <ul>
            <li><strong>Entry Signals:</strong> Actionable trade setups with entry/stop/target</li>
            <li><strong>Confluence Report:</strong> High-conviction picks (3+ scanner hits)</li>
            <li><strong>Risk Flags:</strong> Holdings at risk + warning signals</li>
        </ul>

        <p><strong>Next Steps:</strong></p>
        <ol>
            <li>Open the attached Excel files</li>
            <li>Review high-conviction picks first</li>
            <li>Check risk flags for existing holdings</li>
            <li>Validate setups on TradingView (click symbols in Excel)</li>
        </ol>
        """

        return EmailTemplates.base_template("Daily Batch Scanner Report", content)

    @staticmethod
    def risk_alert(risk_data: dict[str, Any], holdings_at_risk: list[str]) -> str:
        """Template for risk alerts."""
        holdings_html = ""
        if holdings_at_risk:
            holdings_html = "<ul>"
            for symbol in holdings_at_risk:
                holdings_html += f"<li><strong>{symbol}</strong></li>"
            holdings_html += "</ul>"

        content = f"""
        <p style="color: #E74C3C; font-weight: 600;">
            ⚠️ Risk flags detected on {len(holdings_at_risk)} portfolio holding(s)
        </p>

        <div class="metric-box" style="border-left-color: #E74C3C;">
            <h3 style="margin-top: 0; color: #E74C3C;">Holdings at Risk</h3>
            {holdings_html}
        </div>

        <h2>Action Required</h2>
        <ol>
            <li>Review the attached Risk Report immediately</li>
            <li>Check stop-loss levels for flagged holdings</li>
            <li>Consider reducing position sizes</li>
            <li>Monitor intraday for further deterioration</li>
        </ol>

        <p><strong>Risk Scanners Triggered:</strong></p>
        <ul>
            <li>RSI Divergence (bearish)</li>
            <li>Williams %R Exhaustion</li>
            <li>Bearish Reversal Candles</li>
        </ul>
        """

        return EmailTemplates.base_template(
            "⚠️ Portfolio Risk Alert", content, footer="""
            <p style="color: #E74C3C; font-size: 12px; margin-top: 30px;">
                <strong>This is an urgent alert.</strong><br>
                Review your holdings immediately.
            </p>
            """
        )

    @staticmethod
    def confluence_report(summary_data: dict[str, Any]) -> str:
        """Template for high-conviction confluence picks."""
        content = f"""
        <p>Your high-conviction picks based on multi-scanner confluence.</p>

        <div class="metric-box">
            <h3 style="margin-top: 0;">Summary</h3>
            <div class="metric-row">
                <span class="metric-label">Total Symbols Scanned</span>
                <span class="metric-value">{summary_data.get('total_symbols', 'N/A')}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">High Conviction (≥3.0 weighted score)</span>
                <span class="high-conviction">{summary_data.get('high_conviction_count', 'N/A')}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Average Weighted Score</span>
                <span class="metric-value">{summary_data.get('avg_weighted_score', 'N/A')}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Entry Signals Present</span>
                <span class="metric-value">{summary_data.get('entry_signal_count', 'N/A')}</span>
            </div>
        </div>

        <h2>How to Use This Report</h2>
        <ul>
            <li><strong>Weighted Score ≥ 3.5:</strong> High-quality setups (Entry + Trend or better)</li>
            <li><strong>Weighted Score 3.0-3.4:</strong> Good setups, verify context</li>
            <li><strong>Has Risk Flag:</strong> Conflicting signals, trade smaller or wait</li>
            <li><strong>Matched Patterns:</strong> Pre-defined high-probability setups</li>
        </ul>

        <p><strong>Score Weighting:</strong></p>
        <ul>
            <li>Entry scanners: 2.0x (highest value)</li>
            <li>Momentum scanners: 1.8x</li>
            <li>Trend scanners: 1.5x</li>
            <li>Pattern scanners: 1.2x</li>
            <li>Risk scanners: -1.0x (penalty)</li>
        </ul>
        """

        return EmailTemplates.base_template("High-Conviction Confluence Report", content)


# ── Email Sender ──────────────────────────────────────────────────────────────


class EmailSender:
    """Email delivery system with retry logic."""

    def __init__(
        self,
        smtp_config: SMTPConfig | None = None,
        recipient_config: RecipientConfig | None = None,
        dry_run: bool = False,
    ):
        """
        Initialize email sender.

        Args:
            smtp_config: SMTP configuration (default: load from env)
            recipient_config: Recipient lists (default: load from file)
            dry_run: If True, don't actually send emails (for testing)
        """
        self.smtp_config = smtp_config or SMTPConfig.from_env()
        self.recipient_config = recipient_config or RecipientConfig()
        self.dry_run = dry_run

        if not self.smtp_config.username or not self.smtp_config.password:
            log.warning("SMTP credentials not configured, emails will fail to send")

    def send_email(
        self,
        to: list[str],
        subject: str,
        body_html: str,
        body_text: str | None = None,
        attachments: list[str | Path] | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        reply_to: str | None = None,
        max_retries: int = 3,
    ) -> bool:
        """
        Send an email with optional attachments.

        Args:
            to: List of recipient email addresses
            subject: Email subject
            body_html: HTML body content
            body_text: Plain text body (fallback for non-HTML clients)
            attachments: List of file paths to attach
            cc: Carbon copy recipients
            bcc: Blind carbon copy recipients
            reply_to: Reply-to address
            max_retries: Number of retry attempts on failure

        Returns:
            True if email sent successfully, False otherwise
        """
        if not to:
            log.error("No recipients specified")
            return False

        # Add all_reports recipients if configured
        if self.recipient_config.all_reports:
            to = list(set(to + self.recipient_config.all_reports))

        if self.dry_run:
            log.info(f"[DRY RUN] Would send email to {to}: {subject}")
            if attachments:
                log.info(f"[DRY RUN] Attachments: {attachments}")
            return True

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.smtp_config.from_name} <{self.smtp_config.from_email}>"
        msg["To"] = ", ".join(to)

        if cc:
            msg["Cc"] = ", ".join(cc)
        if reply_to:
            msg["Reply-To"] = reply_to

        # Add body
        if body_text:
            msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        # Add attachments
        if attachments:
            for file_path in attachments:
                file_path = Path(file_path)
                if not file_path.exists():
                    log.warning(f"Attachment not found: {file_path}")
                    continue

                with open(file_path, "rb") as f:
                    attachment = MIMEApplication(f.read(), Name=file_path.name)

                attachment["Content-Disposition"] = f'attachment; filename="{file_path.name}"'
                msg.attach(attachment)

        # Send with retry logic
        all_recipients = to + (cc or []) + (bcc or [])

        for attempt in range(1, max_retries + 1):
            try:
                if self.smtp_config.use_ssl:
                    server = smtplib.SMTP_SSL(
                        self.smtp_config.host,
                        self.smtp_config.port,
                        timeout=self.smtp_config.timeout,
                    )
                else:
                    server = smtplib.SMTP(
                        self.smtp_config.host,
                        self.smtp_config.port,
                        timeout=self.smtp_config.timeout,
                    )

                    if self.smtp_config.use_tls:
                        server.starttls()

                if self.smtp_config.username and self.smtp_config.password:
                    server.login(self.smtp_config.username, self.smtp_config.password)

                server.sendmail(
                    self.smtp_config.from_email,
                    all_recipients,
                    msg.as_string(),
                )
                server.quit()

                log.info(f"Email sent successfully to {len(all_recipients)} recipient(s): {subject}")
                return True

            except Exception as e:
                log.error(f"Email send attempt {attempt}/{max_retries} failed: {e}")

                if attempt < max_retries:
                    # Exponential backoff: 2^attempt seconds
                    wait_time = 2 ** attempt
                    log.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    log.error(f"Failed to send email after {max_retries} attempts")
                    return False

        return False

    def send_batch_report(
        self,
        report_paths: dict[str, str | Path],
        summary_data: dict[str, Any],
        recipients: list[str] | None = None,
    ) -> bool:
        """
        Send batch scanner report with multiple attachments.

        Args:
            report_paths: Dict of report_type → file_path
            summary_data: Summary metrics for email body
            recipients: Recipient list (default: from config)

        Returns:
            True if sent successfully
        """
        if recipients is None:
            recipients = self.recipient_config.batch_report

        if not recipients:
            log.warning("No recipients configured for batch reports")
            return False

        # Get attachment file names
        attachment_names = [Path(p).name for p in report_paths.values() if Path(p).exists()]

        # Generate email body
        body_html = EmailTemplates.batch_report(summary_data, attachment_names)

        # Send
        from datetime import datetime
        subject = f"Trading Bramha Daily Report - {datetime.now().strftime('%Y-%m-%d')}"

        return self.send_email(
            to=recipients,
            subject=subject,
            body_html=body_html,
            attachments=list(report_paths.values()),
        )

    def send_risk_alert(
        self,
        risk_report_path: str | Path,
        holdings_at_risk: list[str],
        risk_data: dict[str, Any],
        recipients: list[str] | None = None,
    ) -> bool:
        """
        Send urgent risk alert for portfolio holdings.

        Args:
            risk_report_path: Path to risk report Excel file
            holdings_at_risk: List of symbols with risk flags
            risk_data: Risk metrics for email body
            recipients: Recipient list (default: from config)

        Returns:
            True if sent successfully
        """
        if recipients is None:
            recipients = self.recipient_config.risk_alerts

        if not recipients:
            log.warning("No recipients configured for risk alerts")
            return False

        # Generate email body
        body_html = EmailTemplates.risk_alert(risk_data, holdings_at_risk)

        # Send with high priority
        from datetime import datetime
        subject = f"⚠️ RISK ALERT: {len(holdings_at_risk)} Holdings Flagged - {datetime.now().strftime('%Y-%m-%d')}"

        return self.send_email(
            to=recipients,
            subject=subject,
            body_html=body_html,
            attachments=[risk_report_path],
        )

    def send_confluence_report(
        self,
        confluence_report_path: str | Path,
        summary_data: dict[str, Any],
        recipients: list[str] | None = None,
    ) -> bool:
        """
        Send high-conviction confluence report.

        Args:
            confluence_report_path: Path to confluence Excel file
            summary_data: Summary metrics
            recipients: Recipient list (default: from config)

        Returns:
            True if sent successfully
        """
        if recipients is None:
            recipients = self.recipient_config.confluence

        if not recipients:
            log.warning("No recipients configured for confluence reports")
            return False

        # Generate email body
        body_html = EmailTemplates.confluence_report(summary_data)

        # Send
        from datetime import datetime
        subject = f"High-Conviction Picks - {datetime.now().strftime('%Y-%m-%d')}"

        return self.send_email(
            to=recipients,
            subject=subject,
            body_html=body_html,
            attachments=[confluence_report_path],
        )


# ── Quick Helper Function ─────────────────────────────────────────────────────


def send_email(
    to: list[str],
    subject: str,
    body_html: str,
    attachments: list[str | Path] | None = None,
    dry_run: bool = False,
) -> bool:
    """
    Quick helper to send an email.

    Args:
        to: List of recipient emails
        subject: Email subject
        body_html: HTML body
        attachments: Optional file attachments
        dry_run: If True, don't actually send

    Returns:
        True if sent successfully

    Example:
        >>> send_email(
        ...     to=["trader@example.com"],
        ...     subject="Daily Report",
        ...     body_html="<h2>Report attached</h2>",
        ...     attachments=["report.xlsx"],
        ... )
    """
    sender = EmailSender(dry_run=dry_run)
    return sender.send_email(to, subject, body_html, attachments=attachments)


# ── Demo ──────────────────────────────────────────────────────────────────────


def _demo():
    """Demonstration of email delivery system."""
    print("=== Email Delivery System Demo ===\n")

    # Check if SMTP is configured
    config = SMTPConfig.from_env()
    if not config.username or not config.password:
        print("⚠️  SMTP not configured. Set environment variables:")
        print("   SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD")
        print("\nRunning in DRY RUN mode (no emails will be sent)\n")
        dry_run = True
    else:
        print(f"✅ SMTP configured: {config.username} → {config.host}:{config.port}")
        dry_run = True  # Keep dry run for demo

    # Create sender
    sender = EmailSender(dry_run=dry_run)

    # Demo 1: Simple email
    print("\n1. Sending simple test email...")
    success = sender.send_email(
        to=["test@example.com"],
        subject="Test Email from Trading Bramha",
        body_html="<h2>This is a test</h2><p>Email system working!</p>",
    )
    print(f"   Result: {'✅ Sent' if success else '❌ Failed'}")

    # Demo 2: Batch report
    print("\n2. Sending batch report...")
    summary = {
        "universe_size": 500,
        "total_signals": 45,
        "high_conviction_count": 12,
        "entry_signal_count": 28,
        "risk_flag_count": 8,
    }
    success = sender.send_batch_report(
        report_paths={
            "entry": "demo_signals.xlsx",  # From excel_formatter demo
            "confluence": "demo_batch_report.xlsx",
        },
        summary_data=summary,
        recipients=["trader@example.com"],
    )
    print(f"   Result: {'✅ Sent' if success else '❌ Failed'}")

    # Demo 3: Risk alert
    print("\n3. Sending risk alert...")
    success = sender.send_risk_alert(
        risk_report_path="risk_report.xlsx",
        holdings_at_risk=["RELIANCE", "TCS", "INFY"],
        risk_data={"total_holdings": 10, "flagged": 3},
        recipients=["trader@example.com"],
    )
    print(f"   Result: {'✅ Sent' if success else '❌ Failed'}")

    # Demo 4: Confluence report
    print("\n4. Sending confluence report...")
    success = sender.send_confluence_report(
        confluence_report_path="confluence.xlsx",
        summary_data={
            "total_symbols": 500,
            "high_conviction_count": 15,
            "avg_weighted_score": 3.8,
            "entry_signal_count": 28,
        },
        recipients=["trader@example.com"],
    )
    print(f"   Result: {'✅ Sent' if success else '❌ Failed'}")

    print("\n🎉 Demo complete!")
    if dry_run:
        print("\n💡 To send real emails, configure SMTP and set dry_run=False")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _demo()

# Email Delivery System - Implementation Guide

**Status:** ✅ COMPLETED  
**Date:** 2026-10-12  
**Feature:** Quick Win #4 from Enhancement Backlog (Story 5.1.1)

---

## What Was Built

A complete automated email delivery system for Trading Bramha reports with:

- **SMTP Configuration**: Support for Gmail, Outlook, custom servers
- **HTML Email Templates**: Professional styled emails with embedded metrics
- **Multiple Attachments**: Excel reports, PDFs, images
- **Recipient Management**: Configurable lists per report type
- **Retry Logic**: Exponential backoff on failures (3 attempts)
- **Dry-Run Mode**: Test without sending actual emails
- **Security**: Environment variables or YAML config for credentials

---

## Key Features

### 1. Three Email Types with Custom Templates

**Batch Report Email:**
- Professional HTML with summary metrics
- Multiple Excel attachments
- Color-coded metrics (green for high conviction, red for risk)
- Next steps guide

**Risk Alert Email:**
- Urgent formatting with ⚠️ icon
- Lists holdings at risk
- Action required section
- High-priority subject line

**Confluence Report Email:**
- High-conviction picks summary
- Weighted scoring explanation
- Usage instructions
- Category weighting breakdown

### 2. Smart Configuration

**Option A: Environment Variables** (more secure)
```bash
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=your-email@gmail.com
export SMTP_PASSWORD=your-app-password
export SMTP_FROM_NAME="Trading Bramha"
```

**Option B: YAML Config File** (easier to manage)
```yaml
# email_config.yaml
smtp:
  host: smtp.gmail.com
  port: 587
  username: your-email@gmail.com
  password: your-app-password
```

### 3. Recipient Lists by Report Type

Configure different recipients for different reports:
- Batch reports → team@example.com
- Risk alerts → risk-manager@example.com  
- Confluence picks → traders@example.com
- All reports → boss@example.com

---

## How to Use

### Quick Start - Send Any Email

```python
from email_delivery import send_email

# Send with attachment
send_email(
    to=["trader@example.com"],
    subject="Daily Report",
    body_html="<h2>Report attached</h2>",
    attachments=["report.xlsx"],
)
```

### Send Batch Scanner Report

```python
from email_delivery import EmailSender

sender = EmailSender()

# Send batch report with summary
sender.send_batch_report(
    report_paths={
        "entry": "entry_signals.xlsx",
        "confluence": "confluence.xlsx",
        "risk": "risk_flags.xlsx",
    },
    summary_data={
        "universe_size": 500,
        "total_signals": 45,
        "high_conviction_count": 12,
        "entry_signal_count": 28,
        "risk_flag_count": 8,
    },
    recipients=["trader@example.com"],
)
```

Result: Professional HTML email with:
- Summary metrics box
- All three Excel files attached
- Instructions on how to use the reports
- Subject: "Trading Bramha Daily Report - 2026-10-12"

### Send Risk Alert (Urgent)

```python
sender.send_risk_alert(
    risk_report_path="risk_report.xlsx",
    holdings_at_risk=["RELIANCE", "TCS", "INFY"],
    risk_data={"total_holdings": 10, "flagged": 3},
    recipients=["portfolio-manager@example.com"],
)
```

Result: Urgent email with:
- ⚠️ icon in subject line
- Red-highlighted holdings list
- Action required section
- Subject: "⚠️ RISK ALERT: 3 Holdings Flagged - 2026-10-12"

### Send Confluence Report

```python
sender.send_confluence_report(
    confluence_report_path="confluence.xlsx",
    summary_data={
        "total_symbols": 500,
        "high_conviction_count": 15,
        "avg_weighted_score": 3.8,
        "entry_signal_count": 28,
    },
    recipients=["analysts@example.com"],
)
```

---

## Setup Instructions

### Gmail Setup (Recommended)

1. **Enable 2-Factor Authentication** on your Google account
2. **Generate App Password**:
   - Go to Google Account Settings
   - Security → 2-Step Verification → App passwords
   - Select "Mail" and your device
   - Copy the 16-character password
3. **Configure**:
   ```bash
   export SMTP_HOST=smtp.gmail.com
   export SMTP_PORT=587
   export SMTP_USER=your-email@gmail.com
   export SMTP_PASSWORD=your-app-password  # 16-char from step 2
   ```

### Outlook Setup

1. **Enable SMTP** in Outlook settings
2. **Configure**:
   ```bash
   export SMTP_HOST=smtp-mail.outlook.com
   export SMTP_PORT=587
   export SMTP_USER=your-email@outlook.com
   export SMTP_PASSWORD=your-password
   export SMTP_USE_TLS=true
   ```

### Using YAML Config File

1. **Copy template**:
   ```bash
   cp tools/email_config.yaml.template tools/email_config.yaml
   ```

2. **Edit** `email_config.yaml` with your settings

3. **Load in code**:
   ```python
   from email_delivery import SMTPConfig, RecipientConfig, EmailSender
   
   smtp = SMTPConfig.from_yaml("tools/email_config.yaml")
   recipients = RecipientConfig.from_yaml("tools/email_config.yaml")
   sender = EmailSender(smtp_config=smtp, recipient_config=recipients)
   ```

---

## Integration Examples

### With Excel Formatter (Previous Quick Win)

```python
from excel_formatter import save_multi_sheet_excel
from email_delivery import EmailSender

# Create formatted Excel reports
sheets = {
    "Entry Signals": (entry_df, "signals"),
    "Confluence": (confluence_df, "confluence"),
}

summary = {
    "total_signals": len(entry_df),
    "high_conviction": (confluence_df["weighted_score"] >= 3.0).sum(),
}

report_path = save_multi_sheet_excel(
    sheets,
    "daily_batch.xlsx",
    summary_data=summary,
)

# Send via email
sender = EmailSender()
sender.send_batch_report(
    report_paths={"batch": report_path},
    summary_data=summary,
    recipients=["team@example.com"],
)
```

### In opportunity_daily.py (Scheduled Job)

```python
# At the end of opportunity_daily.py

from email_delivery import EmailSender

def main():
    # ... existing code to generate reports ...
    
    # Generate Excel report
    report_path = save_formatted_excel(
        results_df,
        "opportunity_hub_daily.xlsx",
        format_as="signals",
    )
    
    # Email it
    sender = EmailSender()
    sender.send_batch_report(
        report_paths={"opportunity": report_path},
        summary_data={
            "total_signals": len(results_df),
            "regime": regime,
            "avg_score": results_df["score"].mean(),
        },
        # Uses recipients from config file
    )
```

### In scanner_batch_runner.py (When Built)

```python
from email_delivery import EmailSender

def main():
    # Run all batches
    all_results = run_all_batches(universe)
    
    # Generate reports
    report_gen = ReportGenerator(output_dir)
    report_paths = report_gen.generate_all_reports(all_results, confluence_df)
    
    # Send emails
    sender = EmailSender()
    
    # Send batch report to team
    sender.send_batch_report(
        report_paths=report_paths,
        summary_data=get_confluence_summary(confluence_df),
    )
    
    # Send risk alert if needed
    if portfolio_risk_count > 0:
        sender.send_risk_alert(
            risk_report_path=report_paths["risk"],
            holdings_at_risk=holdings_at_risk_list,
            risk_data={"total_holdings": len(portfolio), "flagged": portfolio_risk_count},
        )
```

---

## Customization

### Custom Email Template

```python
from email_delivery import EmailSender, EmailTemplates

# Use base template
custom_html = EmailTemplates.base_template(
    title="My Custom Report",
    content="""
        <h2>Custom Content</h2>
        <p>Your custom email body here</p>
        <ul>
            <li>Point 1</li>
            <li>Point 2</li>
        </ul>
    """,
    footer="<p>Custom footer</p>",
)

sender = EmailSender()
sender.send_email(
    to=["recipient@example.com"],
    subject="Custom Report",
    body_html=custom_html,
)
```

### Custom SMTP Configuration

```python
from email_delivery import SMTPConfig, EmailSender

# Custom SMTP server
custom_smtp = SMTPConfig(
    host="mail.mycompany.com",
    port=465,
    username="notifications@mycompany.com",
    password="secure-password",
    from_name="Trading Desk",
    use_ssl=True,
)

sender = EmailSender(smtp_config=custom_smtp)
```

### Recipient Groups

```python
from email_delivery import RecipientConfig, EmailSender

# Define recipient groups
recipients = RecipientConfig(
    batch_report=["trader1@ex.com", "trader2@ex.com"],
    risk_alerts=["risk-manager@ex.com"],
    confluence=["analysts@ex.com"],
    all_reports=["boss@ex.com"],  # Gets everything
)

sender = EmailSender(recipient_config=recipients)

# Send to configured groups
sender.send_batch_report(...)  # Goes to batch_report + all_reports
sender.send_risk_alert(...)    # Goes to risk_alerts + all_reports
```

---

## Testing

### Dry Run Mode (Recommended First)

```python
from email_delivery import EmailSender

# Test without sending real emails
sender = EmailSender(dry_run=True)

sender.send_batch_report(
    report_paths={"entry": "test.xlsx"},
    summary_data={"test": 123},
    recipients=["test@example.com"],
)

# Output: [DRY RUN] Would send email to ['test@example.com']: ...
```

### Send Test Email to Yourself

```python
from email_delivery import send_email

# Simple test
send_email(
    to=["your-email@gmail.com"],
    subject="Test from Trading Bramha",
    body_html="<h2>Testing!</h2><p>If you see this, email system works!</p>",
)
```

### Run Demo

```bash
cd tools
python3 email_delivery.py
```

Expected output:
```
=== Email Delivery System Demo ===

✅ SMTP configured: your-email@gmail.com → smtp.gmail.com:587

1. Sending simple test email...
   Result: ✅ Sent

2. Sending batch report...
   Result: ✅ Sent

...
```

---

## Security Best Practices

### 1. Use App Passwords (Gmail)

Never use your actual Gmail password. Always use app-specific passwords.

### 2. Environment Variables (Production)

Store credentials as environment variables, not in code:

```bash
# .env file (never commit this!)
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Load in code
import os
from dotenv import load_dotenv
load_dotenv()
```

### 3. Restrict Config File Permissions

```bash
chmod 600 email_config.yaml  # Only you can read
```

### 4. Use Dedicated Email Account

Create a dedicated email account for automated reports, not your personal account.

---

## Troubleshooting

### "Authentication failed"

**Gmail:**
- Enable 2FA first
- Generate app password (not regular password)
- Check "Allow less secure apps" is OFF (use app password instead)

**Outlook:**
- May need to enable SMTP in settings
- Some corporate accounts block SMTP

### "Connection timeout"

- Check firewall/proxy settings
- Try different port (587 for TLS, 465 for SSL)
- Verify SMTP host address

### "Attachments not included"

- Check file paths are absolute
- Verify files exist before sending
- Check file permissions

### Emails going to spam

- Set proper from_name and from_email
- Use authenticated SMTP (don't skip login)
- Avoid spam trigger words in subject
- Recipients should whitelist your email

### "No recipients configured"

- Set recipients in YAML config OR
- Pass recipients directly to send methods

---

## Advanced Features

### Retry Logic with Exponential Backoff

Automatically retries failed sends:
- Attempt 1: Immediate
- Attempt 2: Wait 2 seconds
- Attempt 3: Wait 4 seconds

```python
sender.send_email(..., max_retries=5)  # Override default 3
```

### CC and BCC

```python
sender.send_email(
    to=["main@example.com"],
    cc=["manager@example.com"],
    bcc=["archive@example.com"],
    subject="Report",
    body_html="...",
)
```

### Reply-To Address

```python
sender.send_email(
    to=["recipient@example.com"],
    reply_to="support@yourcompany.com",
    subject="Report",
    body_html="...",
)
```

### Plain Text Fallback

Some email clients don't support HTML:

```python
sender.send_email(
    to=["recipient@example.com"],
    subject="Report",
    body_html="<h2>Rich HTML</h2>",
    body_text="Plain text version for old email clients",
)
```

---

## Real-World Usage Example

### Complete Daily Workflow

```python
#!/usr/bin/env python3
"""daily_batch_with_email.py - Run batch + email results"""

from confluence_scoring import aggregate_weighted_confluence
from excel_formatter import save_multi_sheet_excel
from email_delivery import EmailSender
import scanner_templates as sc

def run_daily_batch():
    # 1. Run scanners
    all_results = run_all_batches(universe)
    
    # 2. Calculate confluence
    confluence_df = aggregate_weighted_confluence(all_results, sc.SCANNERS)
    
    # 3. Extract entry and risk data
    entry_df = extract_entry_signals(all_results)
    risk_df = extract_risk_flags(all_results)
    
    # 4. Create formatted Excel report
    sheets = {
        "Entry Signals": (entry_df, "signals"),
        "Confluence": (confluence_df, "confluence"),
        "Risk Flags": (risk_df, "risk"),
    }
    
    summary = {
        "universe_size": len(universe),
        "total_signals": len(entry_df),
        "high_conviction_count": (confluence_df["weighted_score"] >= 3.0).sum(),
        "risk_flag_count": len(risk_df),
    }
    
    report_path = save_multi_sheet_excel(
        sheets,
        f"batch_report_{datetime.now():%Y%m%d}.xlsx",
        summary_data=summary,
    )
    
    # 5. Email the report
    sender = EmailSender()
    sender.send_batch_report(
        report_paths={"batch": report_path},
        summary_data=summary,
    )
    
    # 6. Send risk alert if holdings at risk
    holdings_at_risk = get_portfolio_holdings_with_risk(risk_df)
    if holdings_at_risk:
        sender.send_risk_alert(
            risk_report_path=report_path,
            holdings_at_risk=holdings_at_risk,
            risk_data=summary,
        )
    
    print(f"✅ Batch complete. Report emailed to configured recipients.")

if __name__ == "__main__":
    run_daily_batch()
```

Schedule this to run daily at 4:30 PM (after market close):

```bash
# In scheduler_core.py
JOBS["daily_batch_email"] = JobSpec(
    id="daily_batch_email",
    label="Daily Batch + Email",
    command="python3 tools/daily_batch_with_email.py",
    default_time="16:30",
)
```

---

## Performance Notes

- **Fast**: Email sending takes 1-3 seconds per recipient
- **Concurrent**: Can send to multiple recipients in one SMTP session
- **Attachments**: Supports files up to 25MB (Gmail limit)
- **Rate Limits**: Gmail allows ~500 emails/day, Outlook ~300/day

---

## Files Created

- `tools/email_delivery.py` - Main implementation (669 lines)
- `tools/email_config.yaml.template` - Configuration template
- `EMAIL_DELIVERY_GUIDE.md` - This documentation

---

## Validation

✅ SMTP configuration from env variables  
✅ SMTP configuration from YAML file  
✅ HTML email templates working  
✅ Multiple attachments supported  
✅ Recipient groups configurable  
✅ Retry logic with exponential backoff  
✅ Dry-run mode for testing  
✅ Batch report email sent  
✅ Risk alert email sent  
✅ Confluence email sent  
✅ Demo runs successfully  
✅ Zero breaking changes to existing code

---

## Next Steps

Now that you have email delivery:

1. **Integrate with opportunity_daily.py**
   - Email the daily opportunity hub report
   - Send to configured recipients

2. **Build scanner_batch_runner.py** (from workflow doc)
   - Generate batch reports
   - Email automatically after each run

3. **Add to scheduler**
   - Schedule daily batch + email job
   - Monitor via email delivery logs

4. **Combine with next Quick Wins**
   - Portfolio Risk Monitor → Email urgent alerts
   - Progress Bars → Track email send status
   - Structured Logging → Log email delivery metrics

---

**Professional email delivery is now fully automated!** 📧

Configure your SMTP settings and start receiving beautiful reports in your inbox every day.

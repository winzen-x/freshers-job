"""Optional settings (environment variables). Only needed for email alerts."""
import os
SMTP_HOST = os.getenv("SMTP_HOST", ""); SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", ""); SMTP_PASS = os.getenv("SMTP_PASS", "")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")
ALERT_INTERVAL_MIN = int(os.getenv("ALERT_INTERVAL_MIN", "60"))

# Web search keys (needed for "search the internet" features). Use ONE of them:
TAVILY_KEY = os.getenv("TAVILY_KEY", "")   # free: tavily.com (1000 searches/month, no card)
BRAVE_KEY  = os.getenv("BRAVE_KEY", "")    # brave.com/search/api

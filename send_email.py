import argparse
import os
import sys

from lib.emailer import send_email


def load_env(path):
    env = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def main():
    parser = argparse.ArgumentParser(description="Send an email report via Gmail SMTP (manual/local testing helper).")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body-file", required=True, help="Path to a UTF-8 text/markdown file containing the email body.")
    parser.add_argument("--to", default=None, help="Recipient address. Defaults to GMAIL_ADDRESS from .env.")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))
    env = load_env(os.path.join(base_dir, ".env"))

    sender = env.get("GMAIL_ADDRESS")
    password = env.get("GMAIL_APP_PASSWORD")
    if not sender or not password:
        print("Missing GMAIL_ADDRESS or GMAIL_APP_PASSWORD in .env", file=sys.stderr)
        sys.exit(1)

    with open(args.body_file, "r", encoding="utf-8") as f:
        body = f.read()

    send_email(args.subject, body, sender, password, to=args.to)
    print(f"Email sent to {args.to or sender}: {args.subject}")


if __name__ == "__main__":
    main()

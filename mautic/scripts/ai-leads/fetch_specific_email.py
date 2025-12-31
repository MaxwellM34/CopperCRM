#!/usr/bin/env python3

import sys
import logging
from logging.handlers import RotatingFileHandler
from email_tool import main  

# -----------------------------
# Logging Setup
# -----------------------------
logHandler = RotatingFileHandler(
    "emailFetcher.log",
    maxBytes=1_000_000,   # 1 MB per log file
    backupCount=5,        # keep 5 backups
    encoding="utf-8"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logHandler, logging.StreamHandler()] 
    # StreamHandler prints to terminal also
)

logger = logging.getLogger(__name__)

# -----------------------------
# Helpers
# -----------------------------
def askInt(prompt, default=None):
    """Safely ask for an integer from terminal."""
    while True:
        text = input(prompt).strip()
        if text == "" and default is not None:
            return default
        try:
            return int(text)
        except ValueError:
            print("Please enter a valid number.")

# -----------------------------
# Main External Logic
# -----------------------------
def mainExternal():
    logger.info("------ Copper Fetcher Started ------")

    print("\n=== Copper IMAP Email Fetcher ===")

    # Ask for sender email
    sender = input("Enter sender email to search for: ").strip()
    if not sender:
        print("Sender email is required.")
        logger.error("Sender email missing — aborting.")
        sys.exit(1)

    # Ask IMAP account index
    imapIndex = askInt(
        "Enter IMAP account index (default = 0): ",
        default=0
    )
    logger.info(f"Using IMAP account index: {imapIndex}")

    # Ask email index
    print("\nWhich email do you want?")
    print("  0  = oldest email")
    print(" -1  = newest email")
    print(" -2  = second newest")
    print(" -3  = third newest")
    print(" etc.\n")

    msgIndex = askInt(
        "Enter email index (default = -1): ",
        default=-1
    )
    logger.info(f"Requested email msg_index: {msgIndex}")

    print("\nFetching email...\n")
    logger.info(f"Fetching email from {sender}")

    result = main(sender, index=imapIndex, msg_index=msgIndex)

    if not result:
        print("No email returned.")
        logger.warning("No email returned by main().")
        return

    print("\n=== EMAIL RESULT ===")
    print("From:    ", result["from"])
    print("Date:    ", result["date"])
    print("Subject: ", result["subject"])
    print("\nBody (first 500 chars):\n")
    print(result["body"][:500])

    logger.info("Fetch successful.")
    logger.info("------ Fetch Complete ------\n")

if __name__ == "__main__":
    mainExternal()

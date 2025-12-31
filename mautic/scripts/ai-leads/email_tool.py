import imaplib # This alows to connect to an IMAP email server. IMAP is basically the protocol used to read emails.
import email # Used to take raw email bytes from IMAP and turn into structured objects
import logging # Need to record logs
from dotenv import load_dotenv
import os # used to grab os env vars
import json # for loading IMAP creds 
import sys 
load_dotenv() # load .env

# ---- Logging Setup ----
from logging.handlers import RotatingFileHandler # Add rotating file handlers to take care of logs 

testingEmailFetch = RotatingFileHandler(
    "emailTesting.log", 
    maxBytes=1_000_000,
    backupCount=5, # Config name for handler
    encoding="utf-8"
)

logging.basicConfig( #Text format for the logs
    
    level=logging.INFO, # minimum severity level logged (not including debug)
    format="%(asctime)s [%(levelname)s] %(message)s", # time stamp
    handlers=[testingEmailFetch] # handler name set up

)

# ---- Config ----
IMAP_HOST     = os.getenv("IMAP_HOST") or "" # pyland mad so add or "" 
IMAP_PORT     = int(os.getenv("IMAP_PORT", "993"))  # get variables from .env
IMAP_ACCOUNTS = os.getenv("IMAP_ACCOUNTS") or ""
IMAP_FOLDER = os.getenv("IMAP_FOLDER") or ""

def getImapCred(index: int):
    accounts = json.loads(IMAP_ACCOUNTS)
    cred = accounts[index]
    return cred["user"], cred["pwd"]



# ----------------------------
# Main Function
# ----------------------------

def main(sender: str, index: int = 0, msg_index: int = -1):
    
    """
    Fetch a specific email from a sender.

    :param sender: email address to search for in FROM header
    :param index: which IMAP account to use from IMAP_ACCOUNTS
    :param msg_index: which matching email to fetch from the search results.
                      Works like normal Python indexing on the IDs list:
                      0 = oldest, -1 = newest, -2 = 2nd newest, etc.
    """

    
    user, pwd = getImapCred(index)

    if not all([IMAP_HOST, user, pwd]): # enusre we have variables
        logging.error("Missing one or more required env vars: IMAP_HOST, IMAP_USER, IMAP_PASS, SENDER_EMAIL")    # log error if we dont have the variables
        raise SystemExit(1)

    logging.info("Connecting to IMAP...") # logs
    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) # create the connection object mail with its credentials
    
    logging.info("Logging in...")
    mail.login(user, pwd) # use connection object to login to users email

    mail.select(IMAP_FOLDER) # use the connection object and go into desired folder
    
    logging.info(f"Searching for emails FROM {sender}...")
    status, data = mail.search(None, 'FROM', f'"{sender}"') # search for mail from sender 
    # Field one is to use IMAP server's default charset, 2 is the header, 3 is the value we are looking for (variable)

    if status != "OK":
        logging.error("Search failed.") # log fail
        mail.logout()
        return   

    ids = data[0].split()  # message IDs
    # IMAP search results are always returned as a single-element list, where data[0]
    # contains a space-separated bytes string of all matching message IDs (e.g. b"1 4 7").
    # We index data[0] to extract that raw bytes string, then .split() it to turn the
    # message IDs into a list like [b"1", b"4", b"7"]. This is the required format for
    # fetching individual emails.

    if not ids:
        logging.info("No emails found from that sender.")
        mail.logout()       # fail if we got no email from sender
        return
    
    target_id = ids[msg_index]  # last ID = most recent email (negative indexing is cool)
    logging.info(f"Fetching latest email ID {target_id.decode()}...")

    status, msg_data = mail.fetch(target_id, "(RFC822)") # fetch the email we found
    # RFCC822 = “Return the full raw contents of the email in standard email format.”

    if status != "OK":
        logging.error("Fetch failed.")
        mail.logout() # error message
        return    
    
    # Parse email 
    raw_email = msg_data[0][1]  # type: ignore # grab the raw email bytes
    msg = email.message_from_bytes(raw_email) # type: ignore # convert the bytes 
    # below is the format of the raw email
    # [
    #     (
    #         b'10 (RFC822 {2354}',       # metadata
    #         b'RAW_EMAIL_BYTES_HERE'     # actual email content
    #     ),
    #     b')'
    # ]

    fromHeader = msg.get('From')
    dateHeader = msg.get('Date')
    subjectHeader = msg.get('Subject')


    logging.info(f"From: {fromHeader}")
    logging.info(f"Date: {dateHeader}" )
    logging.info(f"Subject: {subjectHeader}")


        # Extract body safely
    if msg.is_multipart():# For multipart emails, get_payload() returns a list of parts.
    # The first part is usually the plain-text body.
        part = msg.get_payload()[0] #type: ignore # gets conent of email; text, html, attachments
        body_bytes = part.get_payload(decode=True) #type: ignore # Decode the content of that part (base64, quoted-printable, etc.)
    else:
        body_bytes = msg.get_payload(decode=True) # same for single part

    bodyText = "" # create var for text
    if body_bytes: # if theres data in body
        try:
            bodyText = body_bytes.decode("utf-8", errors="ignore") #type: ignore # convert to UTF-8
        except:
            bodyText = str(body_bytes) #in case  bad jus tconvert into python string

    #Multipart check is important as the email can be structured as below

    #    Content-Type: multipart/alternative
    #--boundary
    #   text/plain
    #--boundary
    #   text/html
    #--boundary
    #   attachment

    logging.info("Email body (first 300 chars):")
    logging.info(bodyText[:3000])

    mail.logout()
    logging.info("Done.")
    
    return {
        "from": fromHeader,
        "date": dateHeader,
        "subject": subjectHeader,
        "body": bodyText,
    }
# ----------------------------
# Entry point
# ----------------------------



if __name__ == "__main__":
    # choose which IMAP account to use
    index = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    print("Using IMAP account index:", index)
    print("Testing credentials:", getImapCred(index))

    sender = input("Enter sender email to search for: ").strip()
    main(sender, index)

    # ---- Test getImapCred ----
    print("Testing credentials:", getImapCred(index))   
# check_email.py
import testing_email_fetch
import os

def main():
    # Ask user for email to check
    sender = input("Enter the sender email address to search for: ").strip()


    print("\n----- Checking email from:", sender, "-----\n")

    # Call the main function from testing_email_fetch.py
    testing_email_fetch.main(sender)

    print("\n----- Done -----\n")


if __name__ == "__main__":
    main()

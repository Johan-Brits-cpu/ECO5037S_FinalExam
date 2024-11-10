# Description - Interact with Algorand blockchain using the Python SDK py-algorand-sdk
# Before running, make sure you have installed py-algorand-sdk i.e. pip3 install py-algorand-sdk
# Usage - $ python 3_algo_multisig.py

import json, time
import random
from typing import Dict, Any
from base64 import b64decode

from algosdk import account, transaction, mnemonic
from algosdk.v2client import algod
from datetime import datetime
import calendar

# Define the class for stokvel members: 



# setup algod client
algod_address = "https://testnet-api.algonode.cloud"
algod_token = ""

algod_client = algod.AlgodClient(algod_token, algod_address)

class Account:
    def __init__(self, name, address, contribution_amount, contribution_date, payout_date):
        self.account_data = {
            "Account name": name,
            "Account address": address,
            "Contribution amount": int(contribution_amount),
            "Opt in": "Yes",  # Default opt-in status to "Yes"
            "Contribution date": contribution_date, 
            "Payout date": payout_date

        }

    def get_account_data(self):
        return self.account_data

    def set_opt_out(self, name, accounts_list):
        """Set the opt-in status to 'No' for the account with the given name."""
        for account in accounts_list:
            if account.account_data["Account name"] == name:
                account.account_data["Opt in"] = "No"
                print(f"Account '{name}' has been opted out.")
                return
        print(f"Account '{name}' not found.")


class AccountManager:
    def __init__(self):
        self.accounts = []

    def add_account(self, name, address, contribution_amount, contribution_date, payout_date):
        account = Account(name, address, contribution_amount, contribution_date, payout_date)
        self.accounts.append(account.get_account_data())

    def get_all_accounts(self):
        return self.accounts
    
def add_multiple_accounts():
    print("Welcome to the Algo Stokvel service. Let's onboard you")
    print("Onboard the members of your stokvel (5 accounts are required to continue)")
    contribution_date = input("Choose the day of the month on which contributions and payouts will be made: ")
    payout_date = str(int(contribution_date) + 1)
    try:
        contribution_amount = float(input("Enter the contribution amount each member must make (MicroAlgos): "))
    except ValueError:
        print("Invalid amount. Please enter a numeric value.")

    manager = AccountManager()
    while True:
        # Gather input from user
        name = input("Enter the account name of a member: ")
        address = input("Enter a valid Algorand wallet address: ")
        
        # Validate wallet address length
        if len(address) != 58:
            print("Invalid wallet address. It must be exactly 58 characters long.")
            continue  # Prompt for input again if the address is invalid

        # Add account to manager
        manager.add_account(name, address, contribution_amount, contribution_date, payout_date)

        # Check if 5 accounts have been added
        if len(manager.get_all_accounts()) >= 5:
            print("Maximum of 5 accounts added.")
            break

        # Ask if the user wants to add another account
        add_another = input("Do you want to add another account? (yes/no): ").strip().lower()
        if add_another != "yes":
            break

    return manager.get_all_accounts()

class StokvelAccountManager:
    def __init__(self, accounts_list):
        self.accounts_list = accounts_list
        self.multisig_address = None
        self.payout_tracker = set()  # Set to track who has received payouts

    def create_multisig_account(self):
        # Ensure that the accounts_list contains at least 5 accounts
        if len(self.accounts_list) < 5:
            print("Error: There must 5 accounts to create a multisig account.")
            return

        # Extract the addresses from the accounts list (assuming each account has an 'Account address' key)
        signatory_addresses = [account["Account address"] for account in self.accounts_list]

        # Set the version and threshold
        version = 1  # Multisig version
        threshold = 4  # Minimum number of signatures required (threshold of 4 out of 5)

        # Create the multisig account
        msig = transaction.Multisig(
            version,
            threshold,
            signatory_addresses
        )

        self.multisig_address = msig.address()
        print("A multi-signatory account has been created to house your funds")
        print("Multisig Address: ", self.multisig_address)
        input("Go fund this wallet with the Algorand dispenser first to enable it to work. Press enter when done.")

    def contribution(self):
        # Check if any account has "Opt in" set to "No"
        input("The regular contributions from all stokvel members will now start. Press enter to continue")
        for account in self.accounts_list:
            if account["Opt in"] == "No":
                print("Error: At least one account has opted out (Opt in status is 'No'). Contribution process halted.")
                break  # Stop the function if any account is opted out

        # Ensure multisig address is created before starting contribution
        if not self.multisig_address:
            print("Error: No multisig account created. Please create the multisig account first.")
            return

        # Loop through each account in the accounts_list
        for account in self.accounts_list:
            # Retrieve user_wallet_address and contribution_amount from account
            user_wallet_address = account["Account address"]
            contribution_amount = account["Contribution amount"]

            # Prompt the user to provide their mnemonic
            user_mnemonic = input(f"Please provide your secret code for {account['Account name']} in order to authorise their contribution: ")
            member_private_key = mnemonic.to_private_key(user_mnemonic)

            # Get suggested transaction parameters from Algod
            params = algod_client.suggested_params()

            # Create the payment transaction, with the multisig address as the receiver
            unsigned_txn = transaction.PaymentTxn(
                sender=user_wallet_address,
                sp=params,
                receiver=self.multisig_address,  # Use the multisig address as the receiver
                amt=contribution_amount,
                note=b"Stokvel contribution",
            )

            # Sign the transaction
            signed_txn = unsigned_txn.sign(member_private_key)

            # Submit the transaction and get back a transaction ID
            txid = algod_client.send_transaction(signed_txn)
            print("Successfully submitted transaction with txID: {}".format(txid))

            # Wait for confirmation
            txn_result = transaction.wait_for_confirmation(algod_client, txid, 4)

            # Print transaction information and decoded note
            print(f"Transaction information: {json.dumps(txn_result, indent=4)}")
            print(f"Decoded note: {b64decode(txn_result['txn']['txn']['note'])}")
        
        print("All members of the stokvel have successfully contributed to the stokvel. Now one of the members will receive the contribution")

    def make_payout(self):
        input("The payout to a single stokvel members will now start. Press enter to continue")
        for account in self.accounts_list:
            if account["Opt in"] == "No":
                print("Error: At least one account has opted out (Opt in status is 'No'). Contribution process halted.")
                break  # Stop the function if any account is opted out

        # Ensure multisig address is created before starting contribution
        if not self.multisig_address:
            print("Error: No multisig account created. Please create the multisig account first.")
            return

        # Calculate the total contribution from all accounts
        total_contribution = sum(account['Contribution amount'] for account in self.accounts_list)
        
        # Calculate 60% of the total contributions for the payout
        payout_amount = int(total_contribution * 0.60)
        
        # Ensure we have accounts left that haven't received a payout this round
        eligible_accounts = [acc for acc in self.accounts_list if acc["Account address"] not in self.payout_tracker]
        
        # If all wallets have received a payout, reset the tracker
        if not eligible_accounts:
            self.payout_tracker.clear()
            eligible_accounts = self.accounts_list
        
        # Randomly choose a wallet from eligible accounts
        chosen_account = random.choice(eligible_accounts)
        receiver_wallet_address = chosen_account["Account address"]
        input(f"The account that will receive this month's payout is {chosen_account["Account name"]}. Press enter to continue")
        self.payout_tracker.add(receiver_wallet_address)  # Track that this wallet has received a payout

        # Fetch the suggested parameters from the Algod client
        params = algod_client.suggested_params()

        # Use the multisig address as sender
        sender_wallet_address = self.multisig_address  

        # Create the payment transaction to be signed by the multisig
        unsigned_txn = transaction.PaymentTxn(
            sender=sender_wallet_address,
            sp=params,
            receiver=receiver_wallet_address,
            amt=payout_amount,
            note=b"Stokvel payout",
        )

        # Create the multisig transaction and sign it by the required signatories        
        msig = transaction.Multisig(
            version=1,
            threshold=4,
            addresses=[account["Account address"] for account in self.accounts_list]  # The signatories  # The signatories
        )

        msig_txn = transaction.MultisigTransaction(unsigned_txn, msig)

        # Gather private keys from the signatories and sign the transaction
        for index, account in enumerate(self.accounts_list[:4], start=1):  # Sign by 4 signatories
            while True:
                # Prompt user for the mnemonic phrase
                signatory_mnemonic = input(f"Please provide the secret code from one of the signatory accounts to authorize the payout to the selected stokvel member. Signatories received: {index}/5 ")
                
                # Validate mnemonic length (should be exactly 25 words)
                if len(signatory_mnemonic.split()) != 25:
                    print("Invalid mnemonic. It must be exactly 25 words long. Please try again.")
                    continue  # Prompt for input again if the mnemonic is invalid
                
                try:
                    # Convert mnemonic to private key if validation passes
                    signatory_private_key = mnemonic.to_private_key(signatory_mnemonic)
                    # Sign the transaction
                    msig_txn.sign(signatory_private_key)
                    break  # Exit loop if the signing is successful
                except Exception as e:
                    print(f"Error signing transaction: {e}. Please ensure the mnemonic is correct.")


        # Send the multisig transaction and get the transaction ID
        txid = algod_client.send_transaction(msig_txn)
        print("Successfully submitted multisig payout transaction with txID: {}".format(txid))

        # Wait for confirmation
        txn_result = transaction.wait_for_confirmation(algod_client, txid, 4)

        # Print transaction information and decoded note
        print(f"Payout transaction information: {json.dumps(txn_result, indent=4)}")
        print(f"Decoded note: {b64decode(txn_result['txn']['txn']['note'])}")

        print(f"Success! A payout of {payout_amount} was made to {chosen_account["Account address"]},")
        print(f"The accounts that have received payouts so far are {self.payout_tracker} ")
        print("Thank you. See you next month!")

    def opt_out(self):
        # Ask if any member wants to opt out
        opt_out_response = input("Do any members want to opt out? (yes/no): ").strip().lower()
        
        if opt_out_response == 'yes':
            # Ask for the name of the account that wants to opt out
            opt_out_name = input("Please provide the name of the account that wants to opt out: ").strip()

            # Find the account with the given name and set "Opt in" to "No"
            account_found = False
            for account in self.accounts_list:
                if account["Account name"].lower() == opt_out_name.lower():
                    account["Opt in"] = "No"
                    account_found = True
                    print(f"{account['Account name']} has been marked as opted out. Stokvel payments will now stop. ")
                    break

            if not account_found:
                print("Error: No account found with that name.")

def increment_months(current_date, months_to_add):
    # Add the specified number of months to the current date
    new_month = current_date.month + months_to_add
    year_increment = (new_month - 1) // 12
    new_month = (new_month - 1) % 12 + 1  # Ensure month is between 1 and 12

    # Adjust the year
    new_year = current_date.year + year_increment

    # Get the last day of the new month to avoid date overflow
    last_day_of_new_month = calendar.monthrange(new_year, new_month)[1]

    # Return the new date, maintaining the same day if possible, or the last day of the new month
    new_day = min(current_date.day, last_day_of_new_month)
    return current_date.replace(year=new_year, month=new_month, day=new_day)

def construct_date(day):
    # Get the current month and year
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    # Create a date using the provided day, current month, and current year
    return datetime(current_year, current_month, day)

repeat = "yes"
while repeat == "yes":

    user_response = input("What would you like to do? \n 1. Create a stokvel \n 2. Trigger a payout simulation \n 3. Opt out of the stokvel \n 4. See list of accounts \nResponse: ")


    if user_response == '1':
        # Initialize the accounts list
        accounts_list = add_multiple_accounts()
        print(accounts_list)

        # Create an instance of the StokvelAccountManager
        manager = StokvelAccountManager(accounts_list)

        # Create the multisig account
        manager.create_multisig_account()
    
    elif user_response == '2':
        
        trigger_date = int(input("Please provide the day of the month specified for stokvel contributions: "))
      
        # Start date is today's date
        today = construct_date(trigger_date)
        tomorrow = construct_date(trigger_date+1)

        # Loop to simulate the payments over the next 5 months
        for i in range(5):
            # Get the current day of the month
            new_contribution_date = increment_months(today, i)
            new_payout_date = increment_months(tomorrow, i)
            #print(str(new_date.day))
            
            # Check if today's day matches the contribution date of any account
            trigger_contribution = any(account["Contribution date"] == str(new_contribution_date.day) for account in accounts_list)
            trigger_payout = any(account["Payout date"] == str(new_payout_date.day) for account in accounts_list)
            
            # Trigger contribution and payout if today matches the Contribution date
            if trigger_contribution:
                manager.contribution()  # Trigger the contribution process

            if trigger_payout:
                manager.make_payout()  # Trigger the payout process
            
            # Increment the date by one month for the next iteration
            #today = increment_month(today)

            print(f"You have made iteration number {i} in 5 of this simulation")
            another = input("Would you like to continue? (yes/no) ").strip().lower()

            if another != 'yes':
                break

    elif user_response == '3':
        manager.opt_out()

    elif user_response == '4':
        print(accounts_list)
        input('Press enter to return to the main menu')
        
        
    else: 
        print("Invalid reponse. Please try again")
    
    repeat = input("Would you like to do antything else? (yes/no): ").strip().lower()

    if repeat != "yes":
        print("Thank you. Goodbye!")
        break
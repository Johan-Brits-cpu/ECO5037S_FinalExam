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

def algo_payment(payer_address, payer_secret_phrase, receiver_address, amount, comment):

    payer_private_key = mnemonic.to_private_key(payer_secret_phrase)

    # Get suggested transaction parameters from Algod
    params = algod_client.suggested_params()

    # Create the payment transaction
    unsigned_txn = transaction.PaymentTxn(
        sender=payer_address,
        sp=params,
        receiver=receiver_address,  # Use a suspense account as the liquidity pool of the Dex
        amt=amount,
        note=comment,
    )

    # Sign the transaction
    signed_txn = unsigned_txn.sign(payer_private_key)

    # Submit the transaction and get back a transaction ID
    txid = algod_client.send_transaction(signed_txn)
    print("Successfully submitted transaction with txID: {}".format(txid))

    # Wait for confirmation
    txn_result = transaction.wait_for_confirmation(algod_client, txid, 4)

    # Print transaction information and decoded note
    print(f"Transaction information: {json.dumps(txn_result, indent=4)}")

def asset_transfer(sender_address, sender_secret_phrase, receiver_address, receiver_secret_phrase, amount, asset_code):

    asset_in_int = int(asset_code) # Add hard coded asset ID for UCTZAR
    asset_info = algod_client.asset_info(asset_in_int)
    asset_params: Dict[str, Any] = asset_info["params"]
    print(f"Asset Name: {asset_params['name']}")

    send_amt = amount
    send_amt_int = int(send_amt)

    # example: ASSET_OPTIN
    sp = algod_client.suggested_params()

    # Create opt-in transaction
    # asset transfer from sender wallet to receiver wallet for asset ID specified. Opt-in required from owner of receiving wallet
    optin_txn = transaction.AssetOptInTxn(
        sender=receiver_address, sp=sp, index = asset_in_int
    )

    receiver_private_key = mnemonic.to_private_key(receiver_secret_phrase)
    signed_optin_txn = optin_txn.sign(private_key=receiver_private_key)
    txid = algod_client.send_transaction(signed_optin_txn)
    print("Opt in successful")
    print(f"Sent opt in transaction with txid: {txid}")

    # Wait for the transaction to be confirmed
    results = transaction.wait_for_confirmation(algod_client, txid, 4)
    print(f"Result confirmed in round: {results['confirmed-round']}")
    # example: ASSET_OPTIN

    # example: ASSET_XFER
    sp = algod_client.suggested_params()
    # Create transfer transaction
    xfer_txn = transaction.AssetTransferTxn(
        sender=sender_address,
        sp=sp,
        receiver=receiver_address,
        amt=send_amt_int,
        index=asset_in_int,
    )
    sender_private_key = mnemonic.to_private_key(sender_secret_phrase)
    signed_xfer_txn = xfer_txn.sign(private_key=sender_private_key)
    txid = algod_client.send_transaction(signed_xfer_txn)
    print(f"Sent transfer transaction with txid: {txid}")

    results = transaction.wait_for_confirmation(algod_client, txid, 4)
    print(f"Result confirmed in round: {results['confirmed-round']}")
    # example: ASSET_XFER


class Account:
    def __init__(self, name, address, contributed_algo,contributed_uct_zar, date):
        self.account_data = {
            "Account name": name,
            "Account address": address,
            "Contributed Algo": int(contributed_algo),
            "Contributed UCTZAR": int(contributed_uct_zar),
            "Join date": date,
            "Status": "Active",  # Default opt-in status to "Yes"
        }

    def get_account_data(self):
        return self.account_data

class AccountManager:
    def __init__(self):
        self.accounts = []

    def add_account(self, name, address, contributed_algo,contributed_uct_zar,date):
        account = Account(name, address, contributed_algo,contributed_uct_zar,date)
        self.accounts.append(account.get_account_data())

    def get_all_accounts(self):
        return self.accounts
    
    def update_contribution(self, name, additional_algo, additional_uctzar):
        """Add an additional amount to the contribution of the account with the given name, if the account is active."""
        for account in self.accounts:
            if account["Account name"] == name:
                if account["Status"] != "Active":
                    print(f"Error: Account '{name}' is not active. Contribution update aborted.")
                    return
                account["Contributed Algo"] += int(additional_algo)
                account["Contributed UCTZAR"] += int(additional_uctzar)
                print(f"Added {additional_algo} of MicroAlgos and {additional_uctzar} of UCTZAR to {name}'s stake. New staked total: \n MicroAlgos: {account['Contributed Algo']} \n UCTZAR: {account['Contributed UCTZAR']}")
                return
        print(f"Account '{name}' not found.")

    
    def set_opt_out(self, name):
        """Set the opt-in status to 'No' for the account with the given name."""
        for account in self.accounts:
            if account["Account name"] == name:
                account["Status"] = "Left"
                print(f"Account '{name}' has left the staking pull successfully.")
                return
        print(f"Account '{name}' not found.")
    
    def distribute_transaction_fee(self, transaction_fee):
        """Distribute a transaction fee across all active accounts in proportion to their contributed Algo amount."""
        # Filter accounts to only include those with "Status" set to "Active"
        active_accounts = [account for account in self.accounts if account["Status"] == "Active"]

        # Calculate the total contributions in "Contributed Algo" for active accounts
        total_contribution = sum(account["Contributed Algo"] for account in active_accounts)

        # Check if total contribution is not zero to avoid division by zero
        if total_contribution == 0:
            print("No active contributions available to distribute.")
            return

        # Calculate each active account's share and update their "Contributed Algo"
        for account in active_accounts:
            # Calculate the proportion of the total active contribution
            contribution = account["Contributed Algo"]
            proportion = contribution / total_contribution

            # Calculate the share of the transaction fee for this account
            share = int(transaction_fee * proportion)

            # Update the "Contributed Algo" field in the active account
            account["Contributed Algo"] += share
            print(f"{account['Account name']} receives {share} MircoAlgos from the transaction fee.")

        print("Transaction fee distributed successfully among all active accounts.")
    
    def stake_algo(self, name, algo_stake_amount, uctzar_stake_amount):
        input("You will now make a contribution of MicroAlgos and UCTZAR. Press enter to continue")

        # Find the account with the specified name
        account = next((acct for acct in self.accounts if acct["Account name"] == name), None)

        # Check if the account was found
        if account is None:
            print(f"Error: Account '{name}' not found.")
            return

        # Check if the account status is "Left"
        if account["Status"] == "Left":
            print("Error: You have left the staking pool. Staking process halted.")
            return  # Stop the function if the account is opted out

        # Retrieve wallet address and contribution amount
        stake_address = account["Account address"]
        contribution_amount = int(algo_stake_amount)  # Ensure amount is an integer
        
            # Ask user for their secret phrase with validation for 25 words
        while True:
            user_mnemonic_stake = input(f"Please provide your secret code for {account['Account name']} to authorize your Algo and UCTZAR stake: ")
            
            # Validate the mnemonic length (must be exactly 25 words)
            if len(user_mnemonic_stake.split()) != 25:
                print("Invalid mnemonic. It must be exactly 25 words long. Please try again.")
            else:
                break
        
        # Dex wallet address
        dex_address = 'UB5BHGLM5Z3W7UPFLTBWOC3HQHUHPCAJSA3ENG4FLLT6UDBKFVZMK7HSCM'

        # Execute Algo payment
        algo_payment(payer_address = stake_address, payer_secret_phrase = user_mnemonic_stake, receiver_address = dex_address, amount = contribution_amount, comment = "Algo stake")

            # Administrator's mnemonic validation
        while True:
            mnemonic_dex = input(f"This step should be executed by the administrator of the Dex wallet.\nPlease provide the secret phrase to opt in to receiving UCTZAR from the staker of the staking pool with account name {account['Account name']}: ")

            # Validate that the administrator's mnemonic is also exactly 25 words
            if len(mnemonic_dex.split()) != 25:
                print("Invalid administrator mnemonic. It must be exactly 25 words long. Please try again.")
            else:
                break

        # Add a process to pay UCTZAR from the staker into the staking pool

        asset_transfer(sender_address = stake_address, sender_secret_phrase = user_mnemonic_stake, receiver_address = dex_address, receiver_secret_phrase = mnemonic_dex, amount = uctzar_stake_amount, asset_code = 728731233)

        # Add a process to pay some DEX tokens from the Staking pool to the staker
        input("You have now contributed your MircoAlgos and UCTZAR to the staking pool. You will now receive Dex tokens for you contribution. Press enter to continue")

        asset_transfer(sender_address = dex_address , sender_secret_phrase = mnemonic_dex, receiver_address = stake_address, receiver_secret_phrase = user_mnemonic_stake , amount = uctzar_stake_amount, asset_code = 728731344)

        print("You have successfully made a contribution to the staking pool")
    
    def withdraw_algo(self, name):
        input("You will now receive a payout of your staked MircoAlgos and UCTZAR. \n You will first need to transfer your DEXtoken back to the staking pool. \n Press enter to continue")

        # Find the account with the specified name
        account = next((acct for acct in self.accounts if acct["Account name"] == name), None)

        # Check if the account was found
        if account is None:
            print(f"Error: Account '{name}' not found.")
            return

            # Ask user for their secret phrase with validation for 25 words
        while True:
            user_mnemonic_stake = input(f"Please provide your secret code for {account['Account name']} to authorize: \n 1. Your DEXtoken to be paid back to the staking pool \n 2. Opt in to receive your fUCTZAR stake: ")
            
            # Validate the mnemonic length (must be exactly 25 words)
            if len(user_mnemonic_stake.split()) != 25:
                print("Invalid mnemonic. It must be exactly 25 words long. Please try again.")
            else:
                break
        
                    # Check if the account is active
        if account["Status"] != "Active":
            print(f"Error: Account '{name}' is not active. Withdrawal aborted.")
            return

        # Retrieve wallet address and contribution amount
        stake_address = account["Account address"]
        contributed_algo = int(account["Contributed Algo"])  # Ensure amount is an integer
        contributed_uctzar = int(account["Contributed UCTZAR"])  # Ensure amount is an integer
        
        # Add a process to pay their DEXtoken from the staker into the staking pool
        dex_address = 'UB5BHGLM5Z3W7UPFLTBWOC3HQHUHPCAJSA3ENG4FLLT6UDBKFVZMK7HSCM'

        # Administrator's mnemonic validation
        while True:
            mnemonic_dex = input(f"This step should be executed by the administrator of the Dex wallet.\n Please provide the secret phrase to opt in to receiving DEXtoken from the staker of the staking pool with account name {account['Account name']}: ")

            # Validate that the administrator's mnemonic is also exactly 25 words
            if len(mnemonic_dex.split()) != 25:
                print("Invalid administrator mnemonic. It must be exactly 25 words long. Please try again.")
            else:
                break

        asset_transfer(sender_address = stake_address , sender_secret_phrase = user_mnemonic_stake , receiver_address = dex_address , receiver_secret_phrase = mnemonic_dex , amount = contributed_uctzar, asset_code = 728731344)
        
        # Add a process to pay Algos from Dex wallet to wallet of staker
        algo_payment(payer_address = dex_address, payer_secret_phrase = mnemonic_dex, receiver_address = stake_address, amount = contributed_algo, comment = "Algo stake withdrawal")

        # Create the payment transaction to pay back the UCTZAR from the staking pool to the staker wallet
        asset_transfer(sender_address = dex_address  , sender_secret_phrase = mnemonic_dex , receiver_address = stake_address , receiver_secret_phrase = user_mnemonic_stake  , amount = contributed_uctzar, asset_code = 728731233)
        
        print("You have successfully withdrawn your stake from the Dex pool.")

manager = AccountManager()

def add_account():
    print("Let's onboard you")
    # Set contribution_date to only the date part
    contribution_date = datetime.today().date().strftime("%Y-%m-%d")
    
    # Prompt for contribution amount and validate
    try:
        contribution_amount = int(input("Enter the amount of MicroAlgos you want to stake: "))
        uctzar_stake_amount = contribution_amount / 1000000 * 2
    except ValueError:
        print("Invalid amount. Please enter a numeric value.")
        return None  # Exit function if input is invalid

    # Prompt for account name
    name = input("Enter your account name: ")

    # Prompt for wallet address and validate length
    while True:
        address = input("Enter a valid Algorand wallet address: ")
        
        # Validate that the wallet address is exactly 58 characters long
        if len(address) != 58:
            print("Invalid wallet address. It must be exactly 58 characters long. Please try again.")
        else:
            break  # Exit the loop if the address is valid

    # Add account to manager
    manager.add_account(name, address, 0, 0, contribution_date)

    # Trigger the stake_algo function
    manager.stake_algo(name, algo_stake_amount=contribution_amount, uctzar_stake_amount=uctzar_stake_amount)

    # Update the staking amount
    manager.update_contribution(name, additional_algo=contribution_amount, additional_uctzar=uctzar_stake_amount)

    return manager.get_all_accounts()


def buyAlgo():
    try:
        purchase_algos = int(input("How much MicroAlgos would you like to buy? "))
    except ValueError:
        print("Invalid amount. Please enter a numeric value.")
        return  # Exit if the input is invalid

    # Calculate transaction fee and required UCTZAR amount
    tx_fee = int(purchase_algos / 100)
    uctzar_amt = int(purchase_algos / 1000000 * 2)

    print(f"Your transaction fee will be {tx_fee} MicroAlgos")
    proceed = input(f"You need to provide {uctzar_amt} in UCTZAR plus transaction fee. Would you like to continue? (yes/no) ").strip().lower()

    if proceed != "yes":
        print("Thank you. Goodbye")
        return
    else:
        # Validate buyer's wallet address
        while True:
            buyer_address = input("Please provide your wallet address: ")
            if len(buyer_address) != 58:
                print("Invalid wallet address. It must be exactly 58 characters long. Please try again.")
            else:
                break

        # Validate buyer's mnemonic (25 words)
        while True:
            buyer_mnemonic = input("Please provide your secret phrase to authorize the payment of the UCTZAR and MicroAlgos transaction fee: ")
            if len(buyer_mnemonic.split()) != 25:
                print("Invalid mnemonic phrase. It must contain exactly 25 words. Please try again.")
            else:
                break

        dex_address = 'UB5BHGLM5Z3W7UPFLTBWOC3HQHUHPCAJSA3ENG4FLLT6UDBKFVZMK7HSCM'

        # Validate administrator's mnemonic (25 words)
        while True:
            mnemonic_dex = input("This step should be executed by the administrator of the Dex wallet.\nPlease provide the secret phrase to opt in to receive UCTZAR from a purchaser of Algos on the DEX: ")
            if len(mnemonic_dex.split()) != 25:
                print("Invalid mnemonic phrase. It must contain exactly 25 words. Please try again.")
            else:
                break

        # Proceed with asset transfer and payments
        asset_transfer(sender_address=buyer_address, sender_secret_phrase=buyer_mnemonic, receiver_address=dex_address, receiver_secret_phrase=mnemonic_dex, amount=uctzar_amt, asset_code=728731233)

        # Pay Algos from the Dex wallet to the buyer of UCTZAR
        algo_payment(payer_address=dex_address, payer_secret_phrase=mnemonic_dex, receiver_address=buyer_address, amount=purchase_algos, comment="Algos purchased on the Dex")

        # Pay transaction fee from buyer wallet to Dex wallet
        algo_payment(payer_address=buyer_address, payer_secret_phrase=buyer_mnemonic, receiver_address=dex_address, amount=tx_fee, comment="Algo purchase transaction fee")

        # Add transaction fee to the staking pool
        manager.distribute_transaction_fee(tx_fee)

        input("Your Algos have been successfully paid out to you")


def buyUCTZAR():
    try:
        purchase_uztzar = int(input("How much UCTZAR would you like to buy? "))
    except ValueError:
        print("Invalid amount. Please enter a numeric value.")
        return  # Exit if input is invalid

    algo_amt = int(purchase_uztzar * 1000000 / 2)
    tx_fee = int(algo_amt / 100)

    print(f"Your transaction fee will be {tx_fee} MicroAlgos")
    proceed = input(f"You need to provide {algo_amt} in MicroAlgos plus the transaction fee. Would you like to continue? (yes/no) ").strip().lower()

    if proceed != "yes":
        print("Thank you. Goodbye")
        return
    else:
        # Validate buyer's wallet address
        while True:
            buyer_address = input("Please provide your wallet address: ")
            if len(buyer_address) != 58:
                print("Invalid wallet address. It must be exactly 58 characters long. Please try again.")
            else:
                break

        # Validate buyer's mnemonic (25 words)
        while True:
            buyer_mnemonic = input("Please provide your secret phrase to authorize the payment of the Algos and transaction fee: ")
            if len(buyer_mnemonic.split()) != 25:
                print("Invalid mnemonic phrase. It must contain exactly 25 words. Please try again.")
            else:
                break

        dex_address = 'UB5BHGLM5Z3W7UPFLTBWOC3HQHUHPCAJSA3ENG4FLLT6UDBKFVZMK7HSCM'

        # Validate administrator's mnemonic (25 words)
        while True:
            mnemonic_dex = input("This step should be executed by the administrator of the Dex wallet.\nPlease provide the secret phrase to authorize sending UCTZAR to a purchaser of UCTZAR on the DEX: ")
            if len(mnemonic_dex.split()) != 25:
                print("Invalid mnemonic phrase. It must contain exactly 25 words. Please try again.")
            else:
                break

        # Pay Algos from the buyer wallet to the Dex wallet
        algo_payment(payer_address=buyer_address, payer_secret_phrase=buyer_mnemonic, receiver_address=dex_address, amount=algo_amt, comment="Algo payment for UCTZAR purchased on Dex")

        # Pay transaction fee from buyer wallet to Dex wallet
        algo_payment(payer_address=buyer_address, payer_secret_phrase=buyer_mnemonic, receiver_address=dex_address, amount=tx_fee, comment="UCTZAR purchase transaction fee")

        # Transfer UCTZAR from the Dex address to the buyer address
        asset_transfer(sender_address=dex_address, sender_secret_phrase=mnemonic_dex, receiver_address=buyer_address, receiver_secret_phrase=buyer_mnemonic, amount=purchase_uztzar, asset_code=728731233)

        # Distribute transaction fee to the staking pool
        manager.distribute_transaction_fee(tx_fee)

        input("Your UCTZAR has been successfully paid out to you. Press enter to continue.")


def stake_additional():
    name = input("Enter your account name: ")

    # Ensure contribution_amount is an integer
    try:
        contribution_amount = int(input("How much would you like to contribute (MicroAlgos): "))
        uctzar_stake_amount = contribution_amount/1000000*2
        print(f"You will also stake {int(uctzar_stake_amount)} UCTZAR to the Dex pool.")
    except ValueError:
        print("Invalid amount. Please enter a numeric value.")
        return

    # Trigger the stake_algo function
    manager.stake_algo(name, algo_stake_amount=contribution_amount, uctzar_stake_amount = uctzar_stake_amount)

    # Update the staking amount
    manager.update_contribution(name, additional_algo=contribution_amount, additional_uctzar= uctzar_stake_amount)

def withdraw_stake():
    name = input("Enter your account name you would like to withdraw: ")

    manager.withdraw_algo(name)

    manager.set_opt_out(name)


repeat = "yes"
while repeat == "yes":

    user_response = input("What would you like to do? \n 1. Add a new staking account \n 2. Contribute addtional assets to an existing account \n 3. Withdraw my staked assets \n 4. Buy UCTZAR \n 5. Buy Algos \n Response: ")

    if user_response == '1':
        contributor = add_account()
        print(contributor)

    elif user_response == '2': 
        stake_additional()
        print(contributor)

    elif user_response == '3':
        withdraw_stake()
        print(contributor)
    elif user_response == '4':
        buyUCTZAR()
        print(contributor)
    elif user_response == '5':
        buyAlgo()
        print(contributor)
    else: 
        print("Invalid reponse. Please try again")
    
    repeat = input("Would you like to do antything else? (yes/no): ").strip().lower()

    if repeat != "yes":
        print("Thank you. Goodbye!")
        break

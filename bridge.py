from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware #Necessary for POA chains
from datetime import datetime
import json
import pandas as pd


def connect_to(chain):
    if chain == 'source':  # The source contract chain is avax
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc" #AVAX C-chain testnet

    if chain == 'destination':  # The destination contract chain is bsc
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/" #BSC testnet

    if chain in ['source','destination']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        # inject the poa compatibility middleware to the innermost layer
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def get_contract_info(chain, contract_info):
    """
        Load the contract_info file into a dictionary
        This function is used by the autograder and will likely be useful to you
    """
    try:
        with open(contract_info, 'r')  as f:
            contracts = json.load(f)
    except Exception as e:
        print( f"Failed to read contract info\nPlease contact your instructor\n{e}" )
        return 0
    return contracts[chain]



def scan_blocks(chain, contract_info="contract_info.json"):
    """
        chain - (string) should be either "source" or "destination"
        Scan the last 5 blocks of the source and destination chains
        Look for 'Deposit' events on the source chain and 'Unwrap' events on the destination chain
        When Deposit events are found on the source chain, call the 'wrap' function the destination chain
        When Unwrap events are found on the destination chain, call the 'withdraw' function on the source chain
    """

    # This is different from Bridge IV where chain was "avax" or "bsc"
    if chain not in ['source','destination']:
        print( f"Invalid chain: {chain}" )
        return 0
    
    #YOUR CODE HERE
    # 1. Load on‑chain info
    info = get_contract_info(chain, contract_info)
    w3 = connect_to(chain)

    # 2. Prepare our own contract instance
    my_address    = info["address"]
    my_abi        = info["abi"]
    my_priv_key   = info["private_key"]
    my_account    = w3.eth.account.from_key(my_priv_key).address
    my_contract   = w3.eth.contract(address=my_address, abi=my_abi)

    # 3. Determine counterpart chain + contract
    if chain == "source":
        event_name      = "Deposit"
        other_chain     = "destination"
        other_info      = get_contract_info(other_chain, contract_info)
        other_w3        = connect_to(other_chain)
        other_contract  = other_w3.eth.contract(
                             address=other_info["address"],
                             abi=other_info["abi"]
                          )
        other_priv_key  = other_info["private_key"]
        other_account   = other_w3.eth.account.from_key(other_priv_key).address

    else:  # destination
        event_name      = "Unwrap"
        other_chain     = "source"
        other_info      = get_contract_info(other_chain, contract_info)
        other_w3        = connect_to(other_chain)
        other_contract  = other_w3.eth.contract(
                             address=other_info["address"],
                             abi=other_info["abi"]
                          )
        other_priv_key  = other_info["private_key"]
        other_account   = other_w3.eth.account.from_key(other_priv_key).address

    # 4. Scan the last 5 blocks
    latest     = w3.eth.get_block_number()
    start_block= max(0, latest - 5)
    print(f"Scanning {chain} blocks {start_block} → {latest}")

    # 5. Pull events in bulk
    event_obj = getattr(my_contract.events, event_name)
    filt = event_obj.createFilter(fromBlock=start_block, toBlock=latest)
    entries = filt.get_all_entries()

    for evt in entries:
        # 6. Extract common fields
        tx_hash = evt.transactionHash.hex()
        print(f"  • {event_name} @ block {evt.blockNumber}, tx {tx_hash}")

        if event_name == "Deposit":
            token     = evt.args["token"]
            recipient = evt.args["recipient"]
            amount    = evt.args["amount"]

            # 7 Build wrap() call on destination
            tx = other_contract.functions.wrap(
                     token, recipient, amount
                 ).buildTransaction({
                     "from": other_account,
                     "nonce": other_w3.eth.get_transaction_count(other_account),
                     "gas": 200_000,
                     "gasPrice": other_w3.eth.gas_price,
                 })
            sig = other_w3.eth.account.sign_transaction(tx, other_priv_key)
            sent = other_w3.eth.send_raw_transaction(sig.rawTransaction)
            print(f"    → wrap() sent: {sent.hex()}")

        else:  # Unwrap
            underlying = evt.args["underlying_token"]
            wrapped    = evt.args["wrapped_token"]
            frm        = evt.args["frm"]
            to_addr    = evt.args["to"]
            amount     = evt.args["amount"]

            # 7 Build withdraw() call on source
            tx = other_contract.functions.withdraw(
                     wrapped, to_addr, amount
                 ).buildTransaction({
                     "from": other_account,
                     "nonce": other_w3.eth.get_transaction_count(other_account),
                     "gas": 200_000,
                     "gasPrice": other_w3.eth.gas_price,
                 })
            sig = other_w3.eth.account.sign_transaction(tx, other_priv_key)
            sent = other_w3.eth.send_raw_transaction(sig.rawTransaction)
            print(f"    → withdraw() sent: {sent.hex()}")


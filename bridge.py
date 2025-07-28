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
    info         = get_contract_info(chain, contract_info)
    w3           = connect_to(chain)
    my_addr      = info["address"]
    my_abi       = info["abi"]
    my_priv      = info["private_key"]
    my_account   = w3.eth.account.from_key(my_priv).address
    my_contract  = w3.eth.contract(address=my_addr, abi=my_abi)

    if chain == "source":
        evt_name      = "Deposit"
        other_chain   = "destination"
    else:
        evt_name      = "Unwrap"
        other_chain   = "source"

    other_info    = get_contract_info(other_chain, contract_info)
    other_w3      = connect_to(other_chain)
    other_contract = other_w3.eth.contract(
        address=other_info["address"],
        abi=other_info["abi"]
    )
    other_priv    = other_info["private_key"]
    other_account = other_w3.eth.account.from_key(other_priv).address

    latest     = w3.eth.get_block_number()
    start_blk  = max(0, latest - 5)
    print(f"Scanning {chain} blocks {start_blk} → {latest}")

    event_obj = getattr(my_contract.events, evt_name)
    evfilter  = event_obj.createFilter(fromBlock=start_blk, toBlock=latest)
    entries   = evfilter.get_all_entries()

    for ev in entries:
        print(f"  • {evt_name} at block {ev.blockNumber}, tx {ev.transactionHash.hex()}")
        if evt_name == "Deposit":
            token     = ev.args["token"]
            recipient = ev.args["recipient"]
            amount    = ev.args["amount"]
            tx_fn     = other_contract.functions.wrap(token, recipient, amount)
        else:  # Unwrap
            wrapped   = ev.args["wrapped_token"]
            to_addr   = ev.args["to"]
            amount    = ev.args["amount"]
            tx_fn     = other_contract.functions.withdraw(wrapped, to_addr, amount)

        tx = tx_fn.buildTransaction({
            "from": other_account,
            "nonce": other_w3.eth.get_transaction_count(other_account),
            "gas": 200_000,
            "gasPrice": other_w3.eth.gas_price,
        })
        signed = other_w3.eth.account.sign_transaction(tx, other_priv)
        tx_hash = other_w3.eth.send_raw_transaction(signed.rawTransaction)
        print(f"    → sent tx: {tx_hash.hex()}")
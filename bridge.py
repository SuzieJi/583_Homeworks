from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware #Necessary for POA chains
from datetime import datetime
import json
import pandas as pd


def connect_to(chain):
    if chain == 'source':  # The source contract chain is avax
        api_url = f"https://avalanche-fuji.core.chainstack.com/ext/bc/C/rpc/ba45fe90bc27fb4a71a9ae07fef143f3" #AVAX C-chain testnet

    if chain == 'destination':  # The destination contract chain is bsc
        api_url = f"https://bsc-testnet.core.chainstack.com/617ec8fbe82ed75f59d20f6d3166a214" #BSC testnet

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
    w3 = connect_to(chain)
    info = get_contract_info(chain, contract_info)
    contract = w3.eth.contract(address=info['address'], abi=info['abi'])

    end_blk = w3.eth.get_block_number()
    start_blk = end_blk - 10

    print(f"[{chain.upper()}] Checking blocks {start_blk} to {end_blk}")

    if chain == 'source':
        time.sleep(60)

        dst_w3 = connect_to('destination')
        dst_info = get_contract_info('destination', contract_info)
        dst_contract = dst_w3.eth.contract(address=dst_info['address'], abi=dst_info['abi'])

        try:
            deposits = contract.events.Deposit().get_logs(from_block=start_blk, to_block=end_blk)
            deposits.sort(key=lambda log: (log.blockNumber, log.logIndex))
            print(f"Detected {len(deposits)} deposit(s)")

            for idx, evt in enumerate(deposits):
                token, user, amt = evt.args['token'], evt.args['recipient'], evt.args['amount']
                print(f"[{idx+1}] Wrapping {amt} of token {token} to {user}")

                key = dst_info.get('warden_key')
                executor = dst_w3.eth.account.from_key(key)
                nonce = dst_w3.eth.get_transaction_count(executor.address)

                try:
                    gas = dst_contract.functions.wrap(token, user, amt).estimate_gas({'from': executor.address})
                    limit = int(gas * 1.2)
                except:
                    limit = 200000

                tx = dst_contract.functions.wrap(token, user, amt).build_transaction({
                    'from': executor.address,
                    'nonce': nonce,
                    'gas': limit,
                    'gasPrice': dst_w3.eth.gas_price
                })

                signed_tx = dst_w3.eth.account.sign_transaction(tx, key)
                tx_hash = dst_w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                print(f"Wrap TX submitted: {tx_hash.hex()}")

                rcpt = dst_w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                print(f"Confirmed on block {rcpt.blockNumber}")

                if idx + 1 < len(deposits):
                    time.sleep(1)

        except Exception as err:
            print(f"[ERROR] Wrap phase failed: {err}")

    elif chain == 'destination':
        time.sleep(30)

        src_w3 = connect_to('source')
        src_info = get_contract_info('source', contract_info)
        src_contract = src_w3.eth.contract(address=src_info['address'], abi=src_info['abi'])

        unwrap_logs = []
        retries = 5
        print(f"Monitoring Unwrap events one block at a time...")

        for blk in range(start_blk, end_blk + 1):
            for attempt in range(retries):
                try:
                    logs = contract.events.Unwrap().get_logs(from_block=blk, to_block=blk)
                    logs.sort(key=lambda log: (log.blockNumber, log.logIndex))
                    unwrap_logs.extend(logs)
                    print(f"✓ Block {blk} processed")
                    break
                except Exception as e:
                    print(f"Retry {attempt + 1}/{retries} failed on block {blk}: {e}")
                    time.sleep(min(2 ** attempt + uniform(0.1, 0.6), 10))
            else:
                print(f"[WARN] Skipped block {blk} after retries")

        print(f"Found {len(unwrap_logs)} unwrap request(s)")

        for idx, evt in enumerate(unwrap_logs):
            token = evt.args['underlying_token']
            target = evt.args['to']
            amount = evt.args['amount']

            print(f"[{idx+1}] Preparing withdrawal of {amount} {token} to {target}")
            key = src_info.get('warden_key')
            signer = src_w3.eth.account.from_key(key)
            nonce = src_w3.eth.get_transaction_count(signer.address)

            try:
                gas = src_contract.functions.withdraw(token, target, amount).estimate_gas({'from': signer.address})
                limit = int(gas * 1.2)
            except:
                limit = 200000

            tx = src_contract.functions.withdraw(token, target, amount).build_transaction({
                'from': signer.address,
                'nonce': nonce,
                'gas': limit,
                'gasPrice': src_w3.eth.gas_price
            })

            signed_tx = src_w3.eth.account.sign_transaction(tx, key)
            tx_hash = src_w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            print(f"Withdraw TX sent: {tx_hash.hex()}")

            rcpt = src_w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            print(f"Confirmed withdrawal in block {rcpt.blockNumber}")

            if idx + 1 < len(unwrap_logs):
                time.sleep(2)

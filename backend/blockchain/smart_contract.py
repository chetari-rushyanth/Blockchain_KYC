"""
Smart Contract Interface
Handles interaction with KYC smart contracts on Ethereum blockchain
"""

import json
import logging
from typing import Dict, Optional, List
from web3 import Web3
from eth_account import Account
from config import Config

class SmartContract:
    """Interface for KYC smart contract operations"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.web3 = None
        self.account = None
        self.contract = None
        self.contract_address = Config.CONTRACT_ADDRESS
        self._initialize_contract()

    def _initialize_contract(self):
        """Initialize smart contract connection"""
        try:
            # Connect to Web3
            self.web3 = Web3(Web3.HTTPProvider(Config.ETHEREUM_NODE_URL))

            if not self.web3.is_connected():
                self.logger.error("Failed to connect to Ethereum node")
                return False

            # Set up account
            if Config.PRIVATE_KEY and Config.PRIVATE_KEY != '0x' + '0' * 64:
                self.account = Account.from_key(Config.PRIVATE_KEY)

            # Load contract ABI and initialize contract
            contract_abi = self._get_contract_abi()
            if contract_abi and self.contract_address and self.contract_address != '0x' + '0' * 40:
                self.contract = self.web3.eth.contract(
                    address=self.contract_address,
                    abi=contract_abi
                )
                self.logger.info(f"Smart contract initialized at address: {self.contract_address}")
            else:
                self.logger.warning("Smart contract not properly configured")

            return True

        except Exception as e:
            self.logger.error(f"Error initializing smart contract: {str(e)}")
            return False

    def _get_contract_abi(self) -> Optional[List]:
        """Get the smart contract ABI"""
        # This is a sample ABI for a KYC smart contract
        # In production, this should be loaded from a file or configuration
        contract_abi = [
            {
                "inputs": [
                    {"name": "_userId", "type": "string"},
                    {"name": "_kycId", "type": "string"},
                    {"name": "_verificationHash", "type": "string"},
                    {"name": "_verificationStatus", "type": "bool"},
                    {"name": "_adminId", "type": "string"}
                ],
                "name": "storeKYCVerification",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "_userId", "type": "string"},
                    {"name": "_kycId", "type": "string"}
                ],
                "name": "getKYCVerification",
                "outputs": [
                    {"name": "exists", "type": "bool"},
                    {"name": "verificationStatus", "type": "bool"},
                    {"name": "timestamp", "type": "uint256"},
                    {"name": "adminId", "type": "string"},
                    {"name": "verificationHash", "type": "string"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "_userId", "type": "string"},
                    {"name": "_identityHash", "type": "string"},
                    {"name": "_adminId", "type": "string"}
                ],
                "name": "updateUserIdentity",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "_userId", "type": "string"}
                ],
                "name": "getUserIdentity",
                "outputs": [
                    {"name": "exists", "type": "bool"},
                    {"name": "identityHash", "type": "string"},
                    {"name": "lastUpdated", "type": "uint256"},
                    {"name": "adminId", "type": "string"}
                ],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "_userId", "type": "string"},
                    {"name": "_kycId", "type": "string"},
                    {"name": "_reason", "type": "string"},
                    {"name": "_adminId", "type": "string"}
                ],
                "name": "revokeKYCVerification",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "userId", "type": "string"},
                    {"indexed": True, "name": "kycId", "type": "string"},
                    {"indexed": False, "name": "verificationStatus", "type": "bool"},
                    {"indexed": False, "name": "timestamp", "type": "uint256"},
                    {"indexed": False, "name": "adminId", "type": "string"}
                ],
                "name": "KYCVerificationStored",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "userId", "type": "string"},
                    {"indexed": False, "name": "identityHash", "type": "string"},
                    {"indexed": False, "name": "timestamp", "type": "uint256"},
                    {"indexed": False, "name": "adminId", "type": "string"}
                ],
                "name": "UserIdentityUpdated",
                "type": "event"
            },
            {
                "anonymous": False,
                "inputs": [
                    {"indexed": True, "name": "userId", "type": "string"},
                    {"indexed": True, "name": "kycId", "type": "string"},
                    {"indexed": False, "name": "reason", "type": "string"},
                    {"indexed": False, "name": "timestamp", "type": "uint256"},
                    {"indexed": False, "name": "adminId", "type": "string"}
                ],
                "name": "KYCVerificationRevoked",
                "type": "event"
            }
        ]

        return contract_abi

    def store_kyc_verification(self, user_id: str, kyc_id: str, verification_hash: str, 
                             verification_status: bool, admin_id: str) -> Dict:
        """Store KYC verification on smart contract"""
        try:
            if not self.contract or not self.account:
                return {
                    'success': False,
                    'message': 'Smart contract or account not initialized'
                }

            # Build transaction
            transaction = self.contract.functions.storeKYCVerification(
                user_id,
                kyc_id,
                verification_hash,
                verification_status,
                admin_id
            ).build_transaction({
                'from': self.account.address,
                'gas': Config.GAS_LIMIT,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })

            # Sign transaction
            signed_txn = self.web3.eth.account.sign_transaction(transaction, Config.PRIVATE_KEY)

            # Send transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)

            self.logger.info(f"KYC verification transaction sent: {tx_hash.hex()}")

            return {
                'success': True,
                'transaction_hash': tx_hash.hex(),
                'message': 'KYC verification stored on blockchain'
            }

        except Exception as e:
            self.logger.error(f"Error storing KYC verification: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to store KYC verification: {str(e)}'
            }

    def get_kyc_verification(self, user_id: str, kyc_id: str) -> Dict:
        """Get KYC verification from smart contract"""
        try:
            if not self.contract:
                return {
                    'success': False,
                    'message': 'Smart contract not initialized'
                }

            # Call contract function
            result = self.contract.functions.getKYCVerification(user_id, kyc_id).call()

            # Parse result
            exists, verification_status, timestamp, admin_id, verification_hash = result

            return {
                'success': True,
                'verification_exists': exists,
                'verification_status': verification_status,
                'verification_timestamp': timestamp,
                'admin_id': admin_id,
                'verification_hash': verification_hash
            }

        except Exception as e:
            self.logger.error(f"Error getting KYC verification: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to get KYC verification: {str(e)}'
            }

    def update_user_identity(self, user_id: str, identity_hash: str, admin_id: str) -> Dict:
        """Update user identity hash on smart contract"""
        try:
            if not self.contract or not self.account:
                return {
                    'success': False,
                    'message': 'Smart contract or account not initialized'
                }

            # Build transaction
            transaction = self.contract.functions.updateUserIdentity(
                user_id,
                identity_hash,
                admin_id
            ).build_transaction({
                'from': self.account.address,
                'gas': Config.GAS_LIMIT,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })

            # Sign transaction
            signed_txn = self.web3.eth.account.sign_transaction(transaction, Config.PRIVATE_KEY)

            # Send transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)

            self.logger.info(f"Identity update transaction sent: {tx_hash.hex()}")

            return {
                'success': True,
                'transaction_hash': tx_hash.hex(),
                'message': 'User identity updated on blockchain'
            }

        except Exception as e:
            self.logger.error(f"Error updating user identity: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to update user identity: {str(e)}'
            }

    def get_user_identity(self, user_id: str) -> Dict:
        """Get user identity from smart contract"""
        try:
            if not self.contract:
                return {
                    'success': False,
                    'message': 'Smart contract not initialized'
                }

            # Call contract function
            result = self.contract.functions.getUserIdentity(user_id).call()

            # Parse result
            exists, identity_hash, last_updated, admin_id = result

            return {
                'success': True,
                'identity_exists': exists,
                'identity_hash': identity_hash,
                'last_updated': last_updated,
                'admin_id': admin_id
            }

        except Exception as e:
            self.logger.error(f"Error getting user identity: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to get user identity: {str(e)}'
            }

    def revoke_kyc_verification(self, user_id: str, kyc_id: str, reason: str, admin_id: str) -> Dict:
        """Revoke KYC verification on smart contract"""
        try:
            if not self.contract or not self.account:
                return {
                    'success': False,
                    'message': 'Smart contract or account not initialized'
                }

            # Build transaction
            transaction = self.contract.functions.revokeKYCVerification(
                user_id,
                kyc_id,
                reason,
                admin_id
            ).build_transaction({
                'from': self.account.address,
                'gas': Config.GAS_LIMIT,
                'gasPrice': self.web3.eth.gas_price,
                'nonce': self.web3.eth.get_transaction_count(self.account.address)
            })

            # Sign transaction
            signed_txn = self.web3.eth.account.sign_transaction(transaction, Config.PRIVATE_KEY)

            # Send transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.rawTransaction)

            self.logger.info(f"KYC revocation transaction sent: {tx_hash.hex()}")

            return {
                'success': True,
                'transaction_hash': tx_hash.hex(),
                'message': 'KYC verification revoked on blockchain'
            }

        except Exception as e:
            self.logger.error(f"Error revoking KYC verification: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to revoke KYC verification: {str(e)}'
            }

    def get_contract_events(self, event_name: str, from_block: int = 0, to_block: str = 'latest') -> List[Dict]:
        """Get events from smart contract"""
        try:
            if not self.contract:
                return []

            # Get event filter
            event_filter = getattr(self.contract.events, event_name)

            # Get events
            events = event_filter.get_logs(fromBlock=from_block, toBlock=to_block)

            # Process events
            processed_events = []
            for event in events:
                processed_event = {
                    'event': event.event,
                    'block_number': event.blockNumber,
                    'transaction_hash': event.transactionHash.hex(),
                    'args': dict(event.args)
                }
                processed_events.append(processed_event)

            return processed_events

        except Exception as e:
            self.logger.error(f"Error getting contract events: {str(e)}")
            return []

    def estimate_gas_for_function(self, function_name: str, *args) -> Optional[int]:
        """Estimate gas required for contract function call"""
        try:
            if not self.contract or not self.account:
                return None

            # Get function
            contract_function = getattr(self.contract.functions, function_name)

            # Estimate gas
            estimated_gas = contract_function(*args).estimate_gas({
                'from': self.account.address
            })

            return estimated_gas

        except Exception as e:
            self.logger.error(f"Error estimating gas for function {function_name}: {str(e)}")
            return None

    def get_contract_info(self) -> Dict:
        """Get smart contract information"""
        try:
            return {
                'contract_address': self.contract_address,
                'is_connected': self.web3.is_connected() if self.web3 else False,
                'has_contract': self.contract is not None,
                'has_account': self.account is not None,
                'account_address': self.account.address if self.account else None,
                'network_id': self.web3.net.version if self.web3 and self.web3.is_connected() else None
            }

        except Exception as e:
            self.logger.error(f"Error getting contract info: {str(e)}")
            return {
                'error': str(e)
            }

# Global smart contract instance
smart_contract = SmartContract()


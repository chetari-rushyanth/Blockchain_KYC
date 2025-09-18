"""
Blockchain Service - Handles blockchain integration for KYC verification
Manages interaction with Ethereum blockchain and smart contracts
"""

import logging
from typing import Dict, Optional
from web3 import Web3
from eth_account import Account
from datetime import datetime
from database.kyc_repository import kyc_repo
from blockchain.blockchain_utils import blockchain_utils
from blockchain.smart_contract import smart_contract
from blockchain.transaction_handler import transaction_handler
from config import Config

class BlockchainService:
    """Service for blockchain operations"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.kyc_repo = kyc_repo
        self.blockchain_utils = blockchain_utils
        self.smart_contract = smart_contract
        self.transaction_handler = transaction_handler
        self.web3 = None
        self.account = None
        self._initialize_blockchain()

    def _initialize_blockchain(self):
        """Initialize blockchain connection"""
        try:
            # Connect to Ethereum node
            self.web3 = Web3(Web3.HTTPProvider(Config.ETHEREUM_NODE_URL))

            if not self.web3.is_connected():
                self.logger.error("Failed to connect to Ethereum node")
                return False

            # Set up account
            if Config.PRIVATE_KEY and Config.PRIVATE_KEY != '0x' + '0' * 64:
                self.account = Account.from_key(Config.PRIVATE_KEY)
                self.logger.info(f"Blockchain account initialized: {self.account.address}")
            else:
                self.logger.warning("No valid private key configured for blockchain operations")

            return True

        except Exception as e:
            self.logger.error(f"Error initializing blockchain: {str(e)}")
            return False

    def store_kyc_verification(self, user_id: str, kyc_id: str, verification_status: bool, admin_id: str) -> Dict:
        """Store KYC verification result on blockchain"""
        try:
            if not self.web3 or not self.account:
                return {
                    'success': False,
                    'message': 'Blockchain not properly initialized'
                }

            # Prepare transaction data
            verification_data = {
                'user_id': user_id,
                'kyc_id': kyc_id,
                'verification_status': verification_status,
                'admin_id': admin_id,
                'timestamp': int(datetime.utcnow().timestamp()),
                'verification_hash': self.blockchain_utils.generate_verification_hash(user_id, kyc_id, verification_status)
            }

            # Create and send transaction
            transaction_result = self.transaction_handler.create_kyc_verification_transaction(verification_data)

            if transaction_result['success']:
                # Store transaction in database
                blockchain_data = {
                    'user_id': user_id,
                    'kyc_id': kyc_id,
                    'transaction_hash': transaction_result['transaction_hash'],
                    'block_number': transaction_result.get('block_number'),
                    'verification_status': verification_status,
                    'admin_id': admin_id,
                    'gas_used': transaction_result.get('gas_used'),
                    'transaction_fee': transaction_result.get('transaction_fee')
                }

                self.kyc_repo.create_blockchain_transaction(blockchain_data)

                self.logger.info(f"KYC verification stored on blockchain: {transaction_result['transaction_hash']}")

                return {
                    'success': True,
                    'message': 'KYC verification stored on blockchain successfully',
                    'transaction_hash': transaction_result['transaction_hash'],
                    'block_number': transaction_result.get('block_number')
                }
            else:
                return {
                    'success': False,
                    'message': f"Blockchain transaction failed: {transaction_result['message']}"
                }

        except Exception as e:
            self.logger.error(f"Error storing KYC verification on blockchain: {str(e)}")
            return {
                'success': False,
                'message': 'Blockchain storage failed due to system error'
            }

    def verify_kyc_on_blockchain(self, user_id: str, kyc_id: str) -> Dict:
        """Verify KYC status from blockchain"""
        try:
            if not self.web3:
                return {
                    'success': False,
                    'message': 'Blockchain not properly initialized'
                }

            # Get verification from smart contract
            verification_result = self.smart_contract.get_kyc_verification(user_id, kyc_id)

            if verification_result['success']:
                return {
                    'success': True,
                    'verification_exists': verification_result['verification_exists'],
                    'verification_status': verification_result.get('verification_status'),
                    'verification_timestamp': verification_result.get('verification_timestamp'),
                    'admin_id': verification_result.get('admin_id')
                }
            else:
                return {
                    'success': False,
                    'message': f"Blockchain verification failed: {verification_result['message']}"
                }

        except Exception as e:
            self.logger.error(f"Error verifying KYC on blockchain: {str(e)}")
            return {
                'success': False,
                'message': 'Blockchain verification failed due to system error'
            }

    def get_user_blockchain_history(self, user_id: str) -> Dict:
        """Get user's blockchain transaction history"""
        try:
            # Get transactions from database
            transactions = self.kyc_repo.get_blockchain_transactions_by_user(user_id)

            # Enrich with blockchain data
            enriched_transactions = []
            for transaction in transactions:
                try:
                    # Get transaction details from blockchain
                    tx_details = self.blockchain_utils.get_transaction_details(transaction['transaction_hash'])

                    enriched_transaction = {
                        **transaction,
                        'blockchain_status': tx_details.get('status'),
                        'confirmations': tx_details.get('confirmations'),
                        'gas_price': tx_details.get('gas_price')
                    }

                    enriched_transactions.append(enriched_transaction)

                except Exception as tx_error:
                    self.logger.warning(f"Failed to enrich transaction {transaction['transaction_hash']}: {str(tx_error)}")
                    enriched_transactions.append(transaction)

            return {
                'success': True,
                'transactions': enriched_transactions,
                'count': len(enriched_transactions)
            }

        except Exception as e:
            self.logger.error(f"Error getting blockchain history: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to retrieve blockchain history'
            }

    def update_user_identity(self, user_id: str, identity_hash: str, admin_id: str) -> Dict:
        """Update user identity hash on blockchain"""
        try:
            if not self.web3 or not self.account:
                return {
                    'success': False,
                    'message': 'Blockchain not properly initialized'
                }

            # Create identity update transaction
            update_data = {
                'user_id': user_id,
                'identity_hash': identity_hash,
                'admin_id': admin_id,
                'timestamp': int(datetime.utcnow().timestamp())
            }

            transaction_result = self.transaction_handler.create_identity_update_transaction(update_data)

            if transaction_result['success']:
                # Store transaction in database
                blockchain_data = {
                    'user_id': user_id,
                    'transaction_hash': transaction_result['transaction_hash'],
                    'block_number': transaction_result.get('block_number'),
                    'operation_type': 'identity_update',
                    'admin_id': admin_id,
                    'gas_used': transaction_result.get('gas_used'),
                    'transaction_fee': transaction_result.get('transaction_fee')
                }

                self.kyc_repo.create_blockchain_transaction(blockchain_data)

                return {
                    'success': True,
                    'message': 'Identity updated on blockchain successfully',
                    'transaction_hash': transaction_result['transaction_hash']
                }
            else:
                return {
                    'success': False,
                    'message': f"Identity update failed: {transaction_result['message']}"
                }

        except Exception as e:
            self.logger.error(f"Error updating identity on blockchain: {str(e)}")
            return {
                'success': False,
                'message': 'Identity update failed due to system error'
            }

    def revoke_kyc_verification(self, user_id: str, kyc_id: str, admin_id: str, reason: str) -> Dict:
        """Revoke KYC verification on blockchain"""
        try:
            if not self.web3 or not self.account:
                return {
                    'success': False,
                    'message': 'Blockchain not properly initialized'
                }

            # Create revocation transaction
            revocation_data = {
                'user_id': user_id,
                'kyc_id': kyc_id,
                'admin_id': admin_id,
                'reason': reason,
                'timestamp': int(datetime.utcnow().timestamp())
            }

            transaction_result = self.transaction_handler.create_kyc_revocation_transaction(revocation_data)

            if transaction_result['success']:
                # Store transaction in database
                blockchain_data = {
                    'user_id': user_id,
                    'kyc_id': kyc_id,
                    'transaction_hash': transaction_result['transaction_hash'],
                    'block_number': transaction_result.get('block_number'),
                    'operation_type': 'kyc_revocation',
                    'admin_id': admin_id,
                    'gas_used': transaction_result.get('gas_used'),
                    'transaction_fee': transaction_result.get('transaction_fee')
                }

                self.kyc_repo.create_blockchain_transaction(blockchain_data)

                return {
                    'success': True,
                    'message': 'KYC verification revoked on blockchain successfully',
                    'transaction_hash': transaction_result['transaction_hash']
                }
            else:
                return {
                    'success': False,
                    'message': f"KYC revocation failed: {transaction_result['message']}"
                }

        except Exception as e:
            self.logger.error(f"Error revoking KYC on blockchain: {str(e)}")
            return {
                'success': False,
                'message': 'KYC revocation failed due to system error'
            }

    def get_blockchain_status(self) -> Dict:
        """Get blockchain connection status and network info"""
        try:
            if not self.web3:
                return {
                    'connected': False,
                    'message': 'Blockchain not initialized'
                }

            # Check connection
            is_connected = self.web3.is_connected()

            if is_connected:
                # Get network info
                network_id = self.web3.net.version
                latest_block = self.web3.eth.block_number
                gas_price = self.web3.eth.gas_price

                # Get account balance if account is set
                account_balance = None
                if self.account:
                    account_balance = self.web3.eth.get_balance(self.account.address)
                    account_balance = self.web3.from_wei(account_balance, 'ether')

                return {
                    'connected': True,
                    'network_id': network_id,
                    'latest_block': latest_block,
                    'gas_price': gas_price,
                    'account_address': self.account.address if self.account else None,
                    'account_balance': float(account_balance) if account_balance else None,
                    'node_url': Config.ETHEREUM_NODE_URL
                }
            else:
                return {
                    'connected': False,
                    'message': 'Failed to connect to Ethereum node',
                    'node_url': Config.ETHEREUM_NODE_URL
                }

        except Exception as e:
            self.logger.error(f"Error getting blockchain status: {str(e)}")
            return {
                'connected': False,
                'message': f'Error checking blockchain status: {str(e)}'
            }

    def estimate_transaction_cost(self, operation_type: str) -> Dict:
        """Estimate gas cost for blockchain operations"""
        try:
            if not self.web3:
                return {
                    'success': False,
                    'message': 'Blockchain not initialized'
                }

            # Get current gas price
            gas_price = self.web3.eth.gas_price

            # Estimate gas based on operation type
            gas_estimates = {
                'kyc_verification': 150000,
                'identity_update': 100000,
                'kyc_revocation': 120000
            }

            estimated_gas = gas_estimates.get(operation_type, 200000)
            estimated_cost = gas_price * estimated_gas
            estimated_cost_eth = self.web3.from_wei(estimated_cost, 'ether')

            return {
                'success': True,
                'operation_type': operation_type,
                'estimated_gas': estimated_gas,
                'gas_price': gas_price,
                'estimated_cost_wei': estimated_cost,
                'estimated_cost_eth': float(estimated_cost_eth)
            }

        except Exception as e:
            self.logger.error(f"Error estimating transaction cost: {str(e)}")
            return {
                'success': False,
                'message': 'Failed to estimate transaction cost'
            }

# Global blockchain service instance
blockchain_service = BlockchainService()

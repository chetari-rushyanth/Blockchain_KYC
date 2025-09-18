"""
Transaction Handler
Manages blockchain transaction creation, signing, and monitoring
"""

import logging
import time
from typing import Dict, Optional
from web3 import Web3
from eth_account import Account
from blockchain.smart_contract import smart_contract
from blockchain.blockchain_utils import blockchain_utils
from config import Config

class TransactionHandler:
    """Handles blockchain transaction operations"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.web3 = None
        self.account = None
        self.smart_contract = smart_contract
        self.blockchain_utils = blockchain_utils
        self._initialize_web3()

    def _initialize_web3(self):
        """Initialize Web3 connection"""
        try:
            self.web3 = Web3(Web3.HTTPProvider(Config.ETHEREUM_NODE_URL))

            if not self.web3.is_connected():
                self.logger.error("Failed to connect to Ethereum node")
                return False

            # Set up account
            if Config.PRIVATE_KEY and Config.PRIVATE_KEY != '0x' + '0' * 64:
                self.account = Account.from_key(Config.PRIVATE_KEY)
                self.logger.info(f"Transaction handler initialized with account: {self.account.address}")
            else:
                self.logger.warning("No valid private key configured")

            return True

        except Exception as e:
            self.logger.error(f"Error initializing transaction handler: {str(e)}")
            return False

    def create_kyc_verification_transaction(self, verification_data: Dict) -> Dict:
        """Create and send KYC verification transaction"""
        try:
            if not self.web3 or not self.account:
                return {
                    'success': False,
                    'message': 'Web3 or account not initialized'
                }

            # Extract data
            user_id = verification_data['user_id']
            kyc_id = verification_data['kyc_id']
            verification_status = verification_data['verification_status']
            admin_id = verification_data['admin_id']
            verification_hash = verification_data['verification_hash']

            # Store verification using smart contract
            contract_result = self.smart_contract.store_kyc_verification(
                user_id, kyc_id, verification_hash, verification_status, admin_id
            )

            if not contract_result['success']:
                return contract_result

            # Wait for transaction confirmation
            tx_hash = contract_result['transaction_hash']
            confirmation_result = self._wait_for_confirmation(tx_hash)

            if confirmation_result['success']:
                return {
                    'success': True,
                    'transaction_hash': tx_hash,
                    'block_number': confirmation_result['receipt']['blockNumber'],
                    'gas_used': confirmation_result['receipt']['gasUsed'],
                    'transaction_fee': self._calculate_transaction_fee(confirmation_result['receipt']),
                    'message': 'KYC verification transaction confirmed'
                }
            else:
                return {
                    'success': False,
                    'transaction_hash': tx_hash,
                    'message': f"Transaction confirmation failed: {confirmation_result['message']}"
                }

        except Exception as e:
            self.logger.error(f"Error creating KYC verification transaction: {str(e)}")
            return {
                'success': False,
                'message': f'Transaction creation failed: {str(e)}'
            }

    def create_identity_update_transaction(self, update_data: Dict) -> Dict:
        """Create and send identity update transaction"""
        try:
            if not self.web3 or not self.account:
                return {
                    'success': False,
                    'message': 'Web3 or account not initialized'
                }

            # Extract data
            user_id = update_data['user_id']
            identity_hash = update_data['identity_hash']
            admin_id = update_data['admin_id']

            # Update identity using smart contract
            contract_result = self.smart_contract.update_user_identity(
                user_id, identity_hash, admin_id
            )

            if not contract_result['success']:
                return contract_result

            # Wait for transaction confirmation
            tx_hash = contract_result['transaction_hash']
            confirmation_result = self._wait_for_confirmation(tx_hash)

            if confirmation_result['success']:
                return {
                    'success': True,
                    'transaction_hash': tx_hash,
                    'block_number': confirmation_result['receipt']['blockNumber'],
                    'gas_used': confirmation_result['receipt']['gasUsed'],
                    'transaction_fee': self._calculate_transaction_fee(confirmation_result['receipt']),
                    'message': 'Identity update transaction confirmed'
                }
            else:
                return {
                    'success': False,
                    'transaction_hash': tx_hash,
                    'message': f"Transaction confirmation failed: {confirmation_result['message']}"
                }

        except Exception as e:
            self.logger.error(f"Error creating identity update transaction: {str(e)}")
            return {
                'success': False,
                'message': f'Transaction creation failed: {str(e)}'
            }

    def create_kyc_revocation_transaction(self, revocation_data: Dict) -> Dict:
        """Create and send KYC revocation transaction"""
        try:
            if not self.web3 or not self.account:
                return {
                    'success': False,
                    'message': 'Web3 or account not initialized'
                }

            # Extract data
            user_id = revocation_data['user_id']
            kyc_id = revocation_data['kyc_id']
            reason = revocation_data['reason']
            admin_id = revocation_data['admin_id']

            # Revoke KYC using smart contract
            contract_result = self.smart_contract.revoke_kyc_verification(
                user_id, kyc_id, reason, admin_id
            )

            if not contract_result['success']:
                return contract_result

            # Wait for transaction confirmation
            tx_hash = contract_result['transaction_hash']
            confirmation_result = self._wait_for_confirmation(tx_hash)

            if confirmation_result['success']:
                return {
                    'success': True,
                    'transaction_hash': tx_hash,
                    'block_number': confirmation_result['receipt']['blockNumber'],
                    'gas_used': confirmation_result['receipt']['gasUsed'],
                    'transaction_fee': self._calculate_transaction_fee(confirmation_result['receipt']),
                    'message': 'KYC revocation transaction confirmed'
                }
            else:
                return {
                    'success': False,
                    'transaction_hash': tx_hash,
                    'message': f"Transaction confirmation failed: {confirmation_result['message']}"
                }

        except Exception as e:
            self.logger.error(f"Error creating KYC revocation transaction: {str(e)}")
            return {
                'success': False,
                'message': f'Transaction creation failed: {str(e)}'
            }

    def _wait_for_confirmation(self, tx_hash: str, timeout: int = 120) -> Dict:
        """Wait for transaction confirmation"""
        try:
            self.logger.info(f"Waiting for transaction confirmation: {tx_hash}")

            # Wait for transaction receipt
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)

            # Check if transaction was successful
            if receipt['status'] != 1:
                return {
                    'success': False,
                    'message': 'Transaction failed',
                    'receipt': dict(receipt)
                }

            self.logger.info(f"Transaction confirmed: {tx_hash}")

            return {
                'success': True,
                'message': 'Transaction confirmed successfully',
                'receipt': dict(receipt)
            }

        except Exception as e:
            self.logger.error(f"Error waiting for confirmation: {str(e)}")
            return {
                'success': False,
                'message': f'Confirmation timeout or error: {str(e)}'
            }

    def _calculate_transaction_fee(self, receipt: Dict) -> Dict:
        """Calculate transaction fee from receipt"""
        try:
            # Get transaction details
            tx_hash = receipt['transactionHash'].hex()
            transaction = self.web3.eth.get_transaction(tx_hash)

            gas_used = receipt['gasUsed']
            gas_price = transaction['gasPrice']

            return self.blockchain_utils.calculate_transaction_fee(gas_used, gas_price)

        except Exception as e:
            self.logger.error(f"Error calculating transaction fee: {str(e)}")
            return {}

    def get_transaction_status(self, tx_hash: str) -> Dict:
        """Get status of a transaction"""
        try:
            if not self.web3:
                return {
                    'success': False,
                    'message': 'Web3 not initialized'
                }

            # Validate transaction hash
            if not self.blockchain_utils.validate_transaction_hash(tx_hash):
                return {
                    'success': False,
                    'message': 'Invalid transaction hash format'
                }

            # Get transaction details
            transaction_details = self.blockchain_utils.get_transaction_details(tx_hash)

            if not transaction_details['success']:
                return transaction_details

            # Determine status
            status = 'pending'
            if 'status' in transaction_details:
                if transaction_details['status'] == 1:
                    status = 'confirmed'
                elif transaction_details['status'] == 0:
                    status = 'failed'

            return {
                'success': True,
                'transaction_hash': tx_hash,
                'status': status,
                'block_number': transaction_details.get('block_number'),
                'confirmations': transaction_details.get('confirmations', 0),
                'gas_used': transaction_details.get('gas_used'),
                'transaction_fee': transaction_details.get('transaction_fee')
            }

        except Exception as e:
            self.logger.error(f"Error getting transaction status: {str(e)}")
            return {
                'success': False,
                'message': f'Error getting transaction status: {str(e)}'
            }

    def create_batch_transaction(self, operations: list) -> Dict:
        """Create batch transaction for multiple operations"""
        try:
            if not self.web3 or not self.account:
                return {
                    'success': False,
                    'message': 'Web3 or account not initialized'
                }

            successful_transactions = []
            failed_transactions = []

            for operation in operations:
                operation_type = operation.get('type')
                operation_data = operation.get('data')

                try:
                    if operation_type == 'kyc_verification':
                        result = self.create_kyc_verification_transaction(operation_data)
                    elif operation_type == 'identity_update':
                        result = self.create_identity_update_transaction(operation_data)
                    elif operation_type == 'kyc_revocation':
                        result = self.create_kyc_revocation_transaction(operation_data)
                    else:
                        result = {
                            'success': False,
                            'message': f'Unknown operation type: {operation_type}'
                        }

                    if result['success']:
                        successful_transactions.append({
                            'operation': operation,
                            'result': result
                        })
                    else:
                        failed_transactions.append({
                            'operation': operation,
                            'error': result['message']
                        })

                except Exception as op_error:
                    failed_transactions.append({
                        'operation': operation,
                        'error': str(op_error)
                    })

            return {
                'success': len(failed_transactions) == 0,
                'successful_transactions': successful_transactions,
                'failed_transactions': failed_transactions,
                'total_operations': len(operations),
                'successful_count': len(successful_transactions),
                'failed_count': len(failed_transactions)
            }

        except Exception as e:
            self.logger.error(f"Error creating batch transaction: {str(e)}")
            return {
                'success': False,
                'message': f'Batch transaction failed: {str(e)}'
            }

    def monitor_transaction(self, tx_hash: str, callback_function=None) -> Dict:
        """Monitor transaction until confirmation"""
        try:
            if not self.web3:
                return {
                    'success': False,
                    'message': 'Web3 not initialized'
                }

            max_attempts = 120  # 2 minutes with 1-second intervals
            attempt = 0

            while attempt < max_attempts:
                try:
                    receipt = self.web3.eth.get_transaction_receipt(tx_hash)

                    # Transaction confirmed
                    status = 'confirmed' if receipt['status'] == 1 else 'failed'

                    result = {
                        'success': True,
                        'transaction_hash': tx_hash,
                        'status': status,
                        'block_number': receipt['blockNumber'],
                        'gas_used': receipt['gasUsed'],
                        'confirmations': self.web3.eth.block_number - receipt['blockNumber']
                    }

                    # Call callback if provided
                    if callback_function:
                        callback_function(result)

                    return result

                except Exception:
                    # Transaction not yet mined
                    pass

                attempt += 1
                time.sleep(1)

            # Timeout reached
            return {
                'success': False,
                'transaction_hash': tx_hash,
                'status': 'timeout',
                'message': 'Transaction monitoring timeout'
            }

        except Exception as e:
            self.logger.error(f"Error monitoring transaction: {str(e)}")
            return {
                'success': False,
                'message': f'Transaction monitoring failed: {str(e)}'
            }

    def estimate_transaction_costs(self, operation_type: str, operation_data: Dict) -> Dict:
        """Estimate costs for different transaction types"""
        try:
            if not self.web3:
                return {
                    'success': False,
                    'message': 'Web3 not initialized'
                }

            # Get current gas price
            gas_price = self.web3.eth.gas_price

            # Estimate gas based on operation type
            if operation_type == 'kyc_verification':
                estimated_gas = self.smart_contract.estimate_gas_for_function(
                    'storeKYCVerification',
                    operation_data['user_id'],
                    operation_data['kyc_id'],
                    operation_data['verification_hash'],
                    operation_data['verification_status'],
                    operation_data['admin_id']
                )
            elif operation_type == 'identity_update':
                estimated_gas = self.smart_contract.estimate_gas_for_function(
                    'updateUserIdentity',
                    operation_data['user_id'],
                    operation_data['identity_hash'],
                    operation_data['admin_id']
                )
            elif operation_type == 'kyc_revocation':
                estimated_gas = self.smart_contract.estimate_gas_for_function(
                    'revokeKYCVerification',
                    operation_data['user_id'],
                    operation_data['kyc_id'],
                    operation_data['reason'],
                    operation_data['admin_id']
                )
            else:
                return {
                    'success': False,
                    'message': f'Unknown operation type: {operation_type}'
                }

            if estimated_gas is None:
                return {
                    'success': False,
                    'message': 'Gas estimation failed'
                }

            # Calculate costs
            estimated_cost = gas_price * estimated_gas
            estimated_cost_eth = self.web3.from_wei(estimated_cost, 'ether')

            return {
                'success': True,
                'operation_type': operation_type,
                'estimated_gas': estimated_gas,
                'gas_price_wei': gas_price,
                'gas_price_gwei': self.web3.from_wei(gas_price, 'gwei'),
                'estimated_cost_wei': estimated_cost,
                'estimated_cost_eth': float(estimated_cost_eth)
            }

        except Exception as e:
            self.logger.error(f"Error estimating transaction costs: {str(e)}")
            return {
                'success': False,
                'message': f'Cost estimation failed: {str(e)}'
            }

# Global transaction handler instance
transaction_handler = TransactionHandler()

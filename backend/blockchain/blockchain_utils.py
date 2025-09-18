"""
Blockchain Utilities
Common utility functions for blockchain operations
"""

import hashlib
import logging
from typing import Dict, Optional
from web3 import Web3
from eth_account import Account
from config import Config

class BlockchainUtils:
    """Utility class for blockchain operations"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.web3 = None
        self._initialize_web3()

    def _initialize_web3(self):
        """Initialize Web3 connection"""
        try:
            self.web3 = Web3(Web3.HTTPProvider(Config.ETHEREUM_NODE_URL))
            if self.web3.is_connected():
                self.logger.info("Web3 connection established")
            else:
                self.logger.error("Failed to establish Web3 connection")
        except Exception as e:
            self.logger.error(f"Error initializing Web3: {str(e)}")

    def generate_verification_hash(self, user_id: str, kyc_id: str, verification_status: bool) -> str:
        """Generate verification hash for blockchain storage"""
        try:
            # Combine user_id, kyc_id, and verification_status
            data_to_hash = f"{user_id}:{kyc_id}:{verification_status}".encode('utf-8')

            # Generate SHA256 hash
            verification_hash = hashlib.sha256(data_to_hash).hexdigest()

            return verification_hash

        except Exception as e:
            self.logger.error(f"Error generating verification hash: {str(e)}")
            return ""

    def generate_identity_hash(self, personal_info: Dict) -> str:
        """Generate identity hash from personal information"""
        try:
            # Extract key identity fields
            identity_data = {
                'full_name': personal_info.get('full_name', '').lower().strip(),
                'date_of_birth': personal_info.get('date_of_birth', ''),
                'document_type': personal_info.get('document_type', ''),
                'nationality': personal_info.get('nationality', '')
            }

            # Create consistent string representation
            identity_string = "|".join([
                identity_data['full_name'],
                identity_data['date_of_birth'],
                identity_data['document_type'],
                identity_data['nationality']
            ])

            # Generate SHA256 hash
            identity_hash = hashlib.sha256(identity_string.encode('utf-8')).hexdigest()

            return identity_hash

        except Exception as e:
            self.logger.error(f"Error generating identity hash: {str(e)}")
            return ""

    def validate_ethereum_address(self, address: str) -> bool:
        """Validate Ethereum address format"""
        try:
            return self.web3.is_address(address) if self.web3 else False
        except Exception as e:
            self.logger.error(f"Error validating address: {str(e)}")
            return False

    def validate_transaction_hash(self, tx_hash: str) -> bool:
        """Validate transaction hash format"""
        try:
            # Check if it's a valid hex string of correct length
            if not tx_hash.startswith('0x'):
                return False

            # Remove '0x' prefix and check length (should be 64 hex characters)
            hex_part = tx_hash[2:]
            if len(hex_part) != 64:
                return False

            # Check if all characters are valid hex
            int(hex_part, 16)
            return True

        except (ValueError, TypeError):
            return False

    def get_transaction_details(self, tx_hash: str) -> Dict:
        """Get transaction details from blockchain"""
        try:
            if not self.web3 or not self.web3.is_connected():
                return {
                    'success': False,
                    'message': 'Web3 not connected'
                }

            # Validate transaction hash
            if not self.validate_transaction_hash(tx_hash):
                return {
                    'success': False,
                    'message': 'Invalid transaction hash format'
                }

            # Get transaction
            try:
                transaction = self.web3.eth.get_transaction(tx_hash)
            except Exception:
                return {
                    'success': False,
                    'message': 'Transaction not found'
                }

            # Get transaction receipt
            try:
                receipt = self.web3.eth.get_transaction_receipt(tx_hash)
            except Exception:
                receipt = None

            # Get current block number for confirmations
            current_block = self.web3.eth.block_number

            transaction_details = {
                'success': True,
                'hash': tx_hash,
                'from_address': transaction['from'],
                'to_address': transaction['to'],
                'value': transaction['value'],
                'gas': transaction['gas'],
                'gas_price': transaction['gasPrice'],
                'nonce': transaction['nonce'],
                'block_number': transaction.get('blockNumber'),
                'block_hash': transaction.get('blockHash'),
                'transaction_index': transaction.get('transactionIndex')
            }

            if receipt:
                transaction_details.update({
                    'status': receipt['status'],
                    'gas_used': receipt['gasUsed'],
                    'cumulative_gas_used': receipt['cumulativeGasUsed'],
                    'logs': receipt['logs']
                })

                # Calculate confirmations
                if receipt['blockNumber']:
                    confirmations = current_block - receipt['blockNumber']
                    transaction_details['confirmations'] = confirmations

            return transaction_details

        except Exception as e:
            self.logger.error(f"Error getting transaction details: {str(e)}")
            return {
                'success': False,
                'message': f'Error retrieving transaction details: {str(e)}'
            }

    def get_gas_price_recommendation(self) -> Dict:
        """Get gas price recommendations"""
        try:
            if not self.web3 or not self.web3.is_connected():
                return {
                    'success': False,
                    'message': 'Web3 not connected'
                }

            # Get current gas price
            current_gas_price = self.web3.eth.gas_price

            # Calculate recommendations (in Wei)
            slow_gas_price = int(current_gas_price * 0.8)  # 20% below current
            standard_gas_price = current_gas_price
            fast_gas_price = int(current_gas_price * 1.2)   # 20% above current

            return {
                'success': True,
                'current_gas_price': current_gas_price,
                'recommendations': {
                    'slow': {
                        'gas_price_wei': slow_gas_price,
                        'gas_price_gwei': self.web3.from_wei(slow_gas_price, 'gwei'),
                        'estimated_time': '> 10 minutes'
                    },
                    'standard': {
                        'gas_price_wei': standard_gas_price,
                        'gas_price_gwei': self.web3.from_wei(standard_gas_price, 'gwei'),
                        'estimated_time': '< 5 minutes'
                    },
                    'fast': {
                        'gas_price_wei': fast_gas_price,
                        'gas_price_gwei': self.web3.from_wei(fast_gas_price, 'gwei'),
                        'estimated_time': '< 2 minutes'
                    }
                }
            }

        except Exception as e:
            self.logger.error(f"Error getting gas price recommendations: {str(e)}")
            return {
                'success': False,
                'message': f'Error getting gas price recommendations: {str(e)}'
            }

    def calculate_transaction_fee(self, gas_used: int, gas_price: int) -> Dict:
        """Calculate transaction fee in various units"""
        try:
            # Calculate fee in Wei
            fee_wei = gas_used * gas_price

            # Convert to other units
            fee_gwei = self.web3.from_wei(fee_wei, 'gwei')
            fee_eth = self.web3.from_wei(fee_wei, 'ether')

            return {
                'gas_used': gas_used,
                'gas_price_wei': gas_price,
                'gas_price_gwei': self.web3.from_wei(gas_price, 'gwei'),
                'fee_wei': fee_wei,
                'fee_gwei': float(fee_gwei),
                'fee_eth': float(fee_eth)
            }

        except Exception as e:
            self.logger.error(f"Error calculating transaction fee: {str(e)}")
            return {}

    def wait_for_transaction_confirmation(self, tx_hash: str, timeout: int = 120, required_confirmations: int = 1) -> Dict:
        """Wait for transaction confirmation"""
        try:
            if not self.web3 or not self.web3.is_connected():
                return {
                    'success': False,
                    'message': 'Web3 not connected'
                }

            # Wait for transaction receipt
            try:
                receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            except Exception as e:
                return {
                    'success': False,
                    'message': f'Transaction confirmation timeout: {str(e)}'
                }

            # Check if transaction was successful
            if receipt['status'] != 1:
                return {
                    'success': False,
                    'message': 'Transaction failed',
                    'receipt': dict(receipt)
                }

            # Wait for required confirmations
            current_block = self.web3.eth.block_number
            confirmations = current_block - receipt['blockNumber']

            if confirmations < required_confirmations:
                return {
                    'success': False,
                    'message': f'Insufficient confirmations: {confirmations}/{required_confirmations}',
                    'receipt': dict(receipt)
                }

            return {
                'success': True,
                'message': 'Transaction confirmed successfully',
                'receipt': dict(receipt),
                'confirmations': confirmations
            }

        except Exception as e:
            self.logger.error(f"Error waiting for transaction confirmation: {str(e)}")
            return {
                'success': False,
                'message': f'Error waiting for confirmation: {str(e)}'
            }

    def estimate_gas_for_transaction(self, transaction_data: Dict) -> Optional[int]:
        """Estimate gas required for a transaction"""
        try:
            if not self.web3 or not self.web3.is_connected():
                return None

            # Estimate gas
            estimated_gas = self.web3.eth.estimate_gas(transaction_data)

            # Add 20% buffer for safety
            estimated_gas_with_buffer = int(estimated_gas * 1.2)

            return estimated_gas_with_buffer

        except Exception as e:
            self.logger.error(f"Error estimating gas: {str(e)}")
            return None

    def create_transaction_data(self, to_address: str, data: str, value: int = 0, gas_price: Optional[int] = None) -> Dict:
        """Create transaction data structure"""
        try:
            if not self.web3 or not self.web3.is_connected():
                return {}

            # Use current gas price if not provided
            if gas_price is None:
                gas_price = self.web3.eth.gas_price

            transaction_data = {
                'to': to_address,
                'value': value,
                'gas': Config.GAS_LIMIT,
                'gasPrice': gas_price,
                'data': data,
                'nonce': None  # Will be set when sending
            }

            return transaction_data

        except Exception as e:
            self.logger.error(f"Error creating transaction data: {str(e)}")
            return {}

# Global blockchain utils instance
blockchain_utils = BlockchainUtils()

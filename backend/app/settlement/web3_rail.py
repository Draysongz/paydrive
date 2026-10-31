import json
import logging
from pathlib import Path

from web3 import AsyncWeb3, AsyncHTTPProvider
from eth_account import Account
from eth_account.messages import encode_typed_data

from app.config import settings
from app.db.models import Invoice

logger = logging.getLogger(__name__)

CONTRACTS_DIR = Path(__file__).parent.parent.parent.parent / "contracts" / "artifacts"


class Web3Rail:
    """Web3 settlement rail using EVM smart contracts."""

    def __init__(self):
        self._w3: AsyncWeb3 | None = None
        self._account = None

    def _get_web3(self) -> AsyncWeb3:
        if not self._w3:
            self._w3 = AsyncWeb3(AsyncHTTPProvider(settings.web3_rpc_url))
        return self._w3

    def _get_account(self):
        if not self._account and settings.web3_private_key:
            self._account = Account.from_key(settings.web3_private_key)
        return self._account

    def _load_abi(self, contract_name: str) -> list:
        abi_path = CONTRACTS_DIR / f"{contract_name}.json"
        if abi_path.exists():
            with open(abi_path) as f:
                artifact = json.load(f)
                return artifact.get("abi", artifact)
        raise FileNotFoundError(f"ABI not found: {abi_path}")

    def _build_eip712_data(self, invoice: Invoice, nonce: int) -> dict:
        return {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "InvoicePayment": [
                    {"name": "invoiceId", "type": "string"},
                    {"name": "amount", "type": "uint256"},
                    {"name": "recipient", "type": "address"},
                    {"name": "nonce", "type": "uint256"},
                ],
            },
            "primaryType": "InvoicePayment",
            "domain": {
                "name": "PayDrive Escrow",
                "version": "1",
                "chainId": settings.web3_chain_id,
                "verifyingContract": settings.simple_vault_address or settings.multisig_vault_address,
            },
            "message": {
                "invoiceId": invoice.invoice_id,
                "amount": int(invoice.total_amount * 10**18),  # Convert to wei
                "recipient": invoice.recipient,
                "nonce": nonce,
            },
        }

    async def execute(self, invoice: Invoice) -> dict:
        """Execute a Web3 settlement for the invoice."""
        w3 = self._get_web3()
        account = self._get_account()

        if not account:
            raise ValueError("Web3 private key not configured")

        if settings.escrow_mode == "multisig":
            return await self._execute_multisig(w3, account, invoice)
        else:
            return await self._execute_simple(w3, account, invoice)

    async def _execute_simple(self, w3: AsyncWeb3, account, invoice: Invoice) -> dict:
        """Release funds from SimpleVault."""
        abi = self._load_abi("SimpleVault")
        contract = w3.eth.contract(
            address=w3.to_checksum_address(settings.simple_vault_address),
            abi=abi,
        )

        amount_wei = int(invoice.total_amount * 10**18)
        invoice_id_bytes = w3.keccak(text=invoice.invoice_id)

        # Build and sign transaction
        nonce = await w3.eth.get_transaction_count(account.address)

        # Sign EIP-712 data for audit trail
        eip712_data = self._build_eip712_data(invoice, nonce)
        signable = encode_typed_data(full_message=eip712_data)
        signature = account.sign_message(signable)

        tx = await contract.functions.release(
            w3.to_checksum_address(invoice.recipient),
            amount_wei,
            invoice_id_bytes,
        ).build_transaction({
            "from": account.address,
            "nonce": nonce,
            "gas": min(await w3.eth.estimate_gas({
                "from": account.address,
                "to": settings.simple_vault_address,
            }), settings.gas_limit_cap),
            "chainId": settings.web3_chain_id,
        })

        signed_tx = account.sign_transaction(tx)
        tx_hash = await w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = await w3.eth.wait_for_transaction_receipt(tx_hash)

        logger.info(f"Web3 settlement: tx={tx_hash.hex()}, block={receipt['blockNumber']}")

        return {
            "provider_ref": tx_hash.hex(),
            "block_number": receipt["blockNumber"],
            "status": "completed" if receipt["status"] == 1 else "failed",
            "metadata": {
                "tx_hash": tx_hash.hex(),
                "block_number": receipt["blockNumber"],
                "gas_used": receipt["gasUsed"],
                "eip712_signature": signature.signature.hex(),
            },
        }

    async def _execute_multisig(self, w3: AsyncWeb3, account, invoice: Invoice) -> dict:
        """Submit a release via MultiSigVault."""
        abi = self._load_abi("MultiSigVault")
        contract = w3.eth.contract(
            address=w3.to_checksum_address(settings.multisig_vault_address),
            abi=abi,
        )

        amount_wei = int(invoice.total_amount * 10**18)
        invoice_id_bytes = w3.keccak(text=invoice.invoice_id)

        nonce = await w3.eth.get_transaction_count(account.address)

        tx = await contract.functions.submitRelease(
            w3.to_checksum_address(invoice.recipient),
            amount_wei,
            invoice_id_bytes,
        ).build_transaction({
            "from": account.address,
            "nonce": nonce,
            "gas": settings.gas_limit_cap,
            "chainId": settings.web3_chain_id,
        })

        signed_tx = account.sign_transaction(tx)
        tx_hash = await w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = await w3.eth.wait_for_transaction_receipt(tx_hash)

        logger.info(f"MultiSig submit: tx={tx_hash.hex()}, block={receipt['blockNumber']}")

        return {
            "provider_ref": tx_hash.hex(),
            "block_number": receipt["blockNumber"],
            "status": "completed" if receipt["status"] == 1 else "failed",
            "metadata": {
                "tx_hash": tx_hash.hex(),
                "block_number": receipt["blockNumber"],
                "gas_used": receipt["gasUsed"],
                "type": "multisig_submit",
            },
        }

"""Web3 implementation of the Task 09 blockchain adapter."""

from __future__ import annotations

import time

from app.config import settings

from .base import BlockchainAdapter, ReceiptResult


VERIFICATION_REGISTRY_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "bytes32",
                "name": "verificationRef",
                "type": "bytes32",
            },
            {
                "indexed": False,
                "internalType": "bytes32",
                "name": "eventDigest",
                "type": "bytes32",
            },
            {
                "indexed": False,
                "internalType": "uint8",
                "name": "outcomeCode",
                "type": "uint8",
            },
            {
                "indexed": False,
                "internalType": "uint256",
                "name": "recordedAt",
                "type": "uint256",
            },
        ],
        "name": "VerificationRecorded",
        "type": "event",
    },
    {
        "inputs": [
            {
                "internalType": "bytes32",
                "name": "verificationRef",
                "type": "bytes32",
            },
            {
                "internalType": "bytes32",
                "name": "eventDigest",
                "type": "bytes32",
            },
            {
                "internalType": "uint8",
                "name": "outcomeCode",
                "type": "uint8",
            },
        ],
        "name": "recordVerification",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


class Web3BlockchainAdapter(BlockchainAdapter):
    def __init__(self):
        from web3 import Web3
        from web3.providers import HTTPProvider

        self._Web3 = Web3

        self.w3 = Web3(
            HTTPProvider(
                settings.BLOCKCHAIN_RPC_URL,
                request_kwargs={"timeout": 5},
            )
        )

        if not self.w3.is_connected():
            raise ConnectionError("RPC unavailable")

        chain_id = int(self.w3.eth.chain_id)

        if chain_id != settings.BLOCKCHAIN_CHAIN_ID:
            raise RuntimeError(
                "BLOCKCHAIN_CHAIN_ID mismatch: "
                f"configured={settings.BLOCKCHAIN_CHAIN_ID}, "
                f"actual={chain_id}"
            )

        accounts = self.w3.eth.accounts

        if not accounts:
            raise RuntimeError("No local blockchain account available")

        self.account = accounts[0]

        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(
                settings.BLOCKCHAIN_CONTRACT_ADDRESS
            ),
            abi=VERIFICATION_REGISTRY_ABI,
        )

    def submit_event(
        self,
        verification_ref: bytes,
        event_digest: bytes,
        outcome_code: int,
    ) -> str:
        last_error = None

        for attempt in range(settings.BLOCKCHAIN_MAX_RETRIES + 1):
            try:
                tx_hash = (
                    self.contract.functions.recordVerification(
                        verification_ref,
                        event_digest,
                        outcome_code,
                    ).transact(
                        {"from": self.account}
                    )
                )

                return self.w3.to_hex(tx_hash)

            except Exception as exc:
                last_error = exc

                if attempt >= settings.BLOCKCHAIN_MAX_RETRIES:
                    break

                time.sleep(0.25 * (2 ** attempt))

        raise ConnectionError(
            "Blockchain transaction submission failed"
        ) from last_error

    def get_receipt(
        self,
        tx_hash: str,
        timeout_seconds: int,
    ) -> ReceiptResult:
        from web3.exceptions import TimeExhausted

        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(
                tx_hash,
                timeout=timeout_seconds,
            )
        except TimeExhausted as exc:
            raise TimeoutError("Receipt timeout") from exc
        except Exception as exc:
            raise ConnectionError(
                "Unable to retrieve transaction receipt"
            ) from exc

        status = int(receipt["status"])
        block_number = int(receipt["blockNumber"])

        if status != 1:
            return ReceiptResult(
                status=status,
                block_number=block_number,
                verification_ref=None,
                event_digest=None,
                outcome_code=None,
                recorded_at=None,
            )

        try:
            events = (
                self.contract.events.VerificationRecorded()
                .process_receipt(receipt)
            )
        except Exception:
            events = []

        if not events:
            return ReceiptResult(
                status=status,
                block_number=block_number,
                verification_ref=None,
                event_digest=None,
                outcome_code=None,
                recorded_at=None,
            )

        args = events[-1]["args"]

        return ReceiptResult(
            status=status,
            block_number=block_number,
            verification_ref=bytes(args["verificationRef"]),
            event_digest=bytes(args["eventDigest"]),
            outcome_code=int(args["outcomeCode"]),
            recorded_at=int(args["recordedAt"]),
        )

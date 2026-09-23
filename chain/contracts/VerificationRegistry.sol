 // SPDX-License-Identifier: UNLICENSED
 pragma solidity ^0.8.24;

contract VerificationRegistry {
    event VerificationRecorded(
        bytes32 indexed verificationRef,
        bytes32 eventDigest,
        uint8 outcomeCode,
        uint256 recordedAt
    );

    function recordVerification(
        bytes32 verificationRef,
        bytes32 eventDigest,
        uint8 outcomeCode
    ) external {
        emit VerificationRecorded(
            verificationRef,
            eventDigest,
            outcomeCode,
            block.timestamp
        );
    }
}

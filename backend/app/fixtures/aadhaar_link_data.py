"""Synthetic Aadhaar-link demo metadata.

This file is intentionally separate from the locked verification fixtures. It
maps Supabase demo linked-record references to local, whitelisted sample assets.
"""

from __future__ import annotations

from dataclasses import dataclass


WATERMARK_TEXT = "SYNTHETIC DEMO — NOT A REAL DOCUMENT"
AADHAAR_UPLOAD_MARKER = "DOCUTRUST SYNTHETIC AADHAAR DEMO CARD"


@dataclass(frozen=True)
class AadhaarLinkedAsset:
    document_ref: str
    document_type: str
    title: str
    issuer_label: str
    asset_filename: str
    mime_type: str
    demo_value: str
    secondary_value: str
    status_label: str


LINKED_ASSETS: dict[str, AadhaarLinkedAsset] = {
    "PAN-20001": AadhaarLinkedAsset(
        document_ref="PAN-20001",
        document_type="PAN",
        title="PAN-Like Demo Record",
        issuer_label="Synthetic Tax Registry",
        asset_filename="aadhaar_link_pan_20001.png",
        mime_type="image/png",
        demo_value="Demo PAN code: DP2001",
        secondary_value="Holder: Aarav Demo",
        status_label="Linked in synthetic registry",
    ),
    "DL-30001": AadhaarLinkedAsset(
        document_ref="DL-30001",
        document_type="DRIVING_LICENSE",
        title="Demo Driving Licence Record",
        issuer_label="Synthetic Transport Registry",
        asset_filename="aadhaar_link_dl_30001.pdf",
        mime_type="application/pdf",
        demo_value="Licence ref: DL-30001",
        secondary_value="Demo validity: 14-Aug-2038",
        status_label="Linked in synthetic registry",
    ),
    "BRC-40001": AadhaarLinkedAsset(
        document_ref="BRC-40001",
        document_type="BIRTH_CERTIFICATE",
        title="Demo Birth Certificate Record",
        issuer_label="Synthetic Civil Records Registry",
        asset_filename="aadhaar_link_brc_40001.pdf",
        mime_type="application/pdf",
        demo_value="Certificate ref: BRC-40001",
        secondary_value="Citizen ref: CIT-10001",
        status_label="Linked in synthetic registry",
    ),
    "BNK-60001": AadhaarLinkedAsset(
        document_ref="BNK-60001",
        document_type="BANK_ACCOUNT",
        title="Demo Bank Account Record",
        issuer_label="Synthetic Banking Registry",
        asset_filename="aadhaar_link_bnk_60001.pdf",
        mime_type="application/pdf",
        demo_value="Demo account ref: BNK-60001",
        secondary_value="Branch: Demo City",
        status_label="Linked in synthetic registry",
    ),
    "VTR-70001": AadhaarLinkedAsset(
        document_ref="VTR-70001",
        document_type="VOTER_ID",
        title="Demo Voter Record",
        issuer_label="Synthetic Electoral Registry",
        asset_filename="aadhaar_link_vtr_70001.png",
        mime_type="image/png",
        demo_value="Voter ref: VTR-70001",
        secondary_value="Constituency: Demo North",
        status_label="Linked in synthetic registry",
    ),
    "PAN-20002": AadhaarLinkedAsset(
        document_ref="PAN-20002",
        document_type="PAN",
        title="PAN-Like Demo Record",
        issuer_label="Synthetic Tax Registry",
        asset_filename="aadhaar_link_pan_20002.png",
        mime_type="image/png",
        demo_value="Demo PAN code: DP2002",
        secondary_value="Holder: Meera Demo",
        status_label="Linked in synthetic registry",
    ),
    "BNK-60002": AadhaarLinkedAsset(
        document_ref="BNK-60002",
        document_type="BANK_ACCOUNT",
        title="Demo Bank Account Record",
        issuer_label="Synthetic Banking Registry",
        asset_filename="aadhaar_link_bnk_60002.pdf",
        mime_type="application/pdf",
        demo_value="Demo account ref: BNK-60002",
        secondary_value="Branch: Demo West",
        status_label="Linked in synthetic registry",
    ),
}


DOCUMENT_TYPE_LABELS = {
    "PAN": "Permanent Account Number Demo",
    "DRIVING_LICENSE": "Driving Licence Demo",
    "BIRTH_CERTIFICATE": "Birth Certificate Demo",
    "MOBILE": "Mobile Connection Demo",
    "BANK_ACCOUNT": "Bank Account Demo",
    "VOTER_ID": "Voter Record Demo",
}


DOCUMENT_ORDER = {
    "PAN-20001": 10,
    "DL-30001": 20,
    "BRC-40001": 30,
    "MOB-50001": 40,
    "BNK-60001": 50,
    "VTR-70001": 60,
    "PAN-20002": 10,
    "MOB-50002": 20,
    "BNK-60002": 30,
}

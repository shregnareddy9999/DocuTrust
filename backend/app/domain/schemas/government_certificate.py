"""Government certificate field definitions for Task 06."""

from . import FieldDef


FIELDS = [
    FieldDef(
        name="holder_name",
        label="Holder Name",
        type="text",
        required=True,
        match_field=True,
        labels=("holder name", "name", "applicant name"),
    ),
    FieldDef(
        name="certificate_type_label",
        label="Certificate Type",
        type="text",
        required=True,
        match_field=True,
        labels=("certificate type", "type of certificate", "certificate"),
    ),
    FieldDef(
        name="certificate_number",
        label="Certificate Number",
        type="text",
        required=True,
        match_field=True,
        labels=("certificate number", "certificate no", "certificate id"),
    ),
    FieldDef(
        name="issuing_authority_label",
        label="Issuing Authority",
        type="text",
        required=True,
        match_field=True,
        labels=("issuing authority", "issued by", "issuing office"),
    ),
    FieldDef(
        name="issue_date",
        label="Issue Date",
        type="date",
        required=False,
        match_field=False,
        labels=("issue date", "date of issue"),
    ),
]

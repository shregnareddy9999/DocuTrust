"""Institutional ID field definitions for Task 06."""

from . import FieldDef


FIELDS = [
    FieldDef(
        name="holder_name",
        label="Holder Name",
        type="text",
        required=True,
        match_field=True,
        labels=("holder name", "name", "card holder"),
    ),
    FieldDef(
        name="institution_name",
        label="Institution Name",
        type="text",
        required=True,
        match_field=True,
        labels=("institution name", "name of institution", "college name"),
    ),
    FieldDef(
        name="id_number",
        label="ID Number",
        type="text",
        required=True,
        match_field=True,
        labels=("id number", "id no", "identification number"),
    ),
    FieldDef(
        name="designation_or_role",
        label="Designation or Role",
        type="text",
        required=False,
        match_field=False,
        labels=("designation", "role", "designation or role"),
    ),
    FieldDef(
        name="valid_until",
        label="Valid Until",
        type="date",
        required=False,
        match_field=False,
        labels=("valid until", "valid through", "expiry date"),
    ),
]

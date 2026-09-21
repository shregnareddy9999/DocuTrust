"""Synthetic PAN-like demo field definitions for Task 06."""

from . import FieldDef


FIELDS = [
    FieldDef(
        name="holder_name",
        label="Holder Name",
        type="text",
        required=True,
        match_field=True,
        labels=("holder name", "name", "name of holder"),
    ),
    FieldDef(
        name="demo_pan_code",
        label="Demo PAN Code",
        type="text",
        required=True,
        match_field=True,
        labels=(
            "demo pan-like code",
            "demo pan like code",
            "demo pan code",
            "demo code",
            "pan-like demo code",
        ),
    ),
    FieldDef(
        name="date_of_birth",
        label="Date of Birth",
        type="date",
        required=True,
        match_field=True,
        labels=("date of birth", "dob", "birth date"),
    ),
    FieldDef(
        name="father_or_guardian_name",
        label="Father or Guardian Name",
        type="text",
        required=False,
        match_field=False,
        labels=("father name", "guardian name", "father or guardian name"),
    ),
]

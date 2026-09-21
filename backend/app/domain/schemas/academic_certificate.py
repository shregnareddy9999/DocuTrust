"""Academic certificate field definitions for Task 06."""

from . import FieldDef


FIELDS = [
    FieldDef(
        name="student_name",
        label="Student Name",
        type="text",
        required=True,
        match_field=True,
        labels=("student name", "name of student", "candidate name"),
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
        name="student_id",
        label="Student ID",
        type="text",
        required=True,
        match_field=True,
        labels=("student id", "student identifier", "enrollment number"),
    ),
    FieldDef(
        name="course_name",
        label="Course Name",
        type="text",
        required=True,
        match_field=True,
        labels=("course name", "course", "program"),
    ),
    FieldDef(
        name="semester_or_year",
        label="Semester or Year",
        type="text",
        required=True,
        match_field=True,
        labels=("semester or year", "semester", "year"),
    ),
    FieldDef(
        name="certificate_or_marksheet_id",
        label="Certificate or Marksheet ID",
        type="text",
        required=True,
        match_field=True,
        labels=(
            "certificate or marksheet id",
            "certificate id",
            "marksheet id",
        ),
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

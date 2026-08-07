from django.db.models import Max
from samples.models import Sample


def generate_case_code(lab_code: str) -> str:
    """
    Generates case codes like:

    KD26/0001
    KD26/0002
    AB26/0001
    """

    year = str(__import__("datetime").date.today().year)[2:]

    prefix = f"{lab_code}{year}/"

    latest = (
        Sample.objects
        .filter(case_code__startswith=prefix)
        .aggregate(Max("case_code"))
    )["case_code__max"]

    if latest:
        number = int(latest.split("/")[1]) + 1
    else:
        number = 1

    return f"{prefix}{number:04d}"
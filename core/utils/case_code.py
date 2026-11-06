from django.utils import timezone
from samples.models import Sample


def generate_case_code(lab_code: str) -> str:
    """
    Generates case codes like:

    KD26/0001
    KD26/0002
    AB26/0001
    """

    year = str(timezone.localdate().year)[2:]

    prefix = f"{lab_code}{year}/"

    existing_numbers = []
    for case_code in Sample.objects.filter(
        case_code__startswith=prefix
    ).values_list("case_code", flat=True):
        suffix = case_code[len(prefix):]
        if suffix.isdigit():
            existing_numbers.append(int(suffix))

    number = max(existing_numbers, default=0) + 1
    while Sample.objects.filter(case_code=f"{prefix}{number:04d}").exists():
        number += 1

    return f"{prefix}{number:04d}"

from django.conf import settings
from django.db import transaction

from assays.models import AssayOrder, SampleTypeAssay
from core.utils.case_code import generate_case_code
from core.utils.laboratory import determine_laboratory


class RegisterSampleService:

    @staticmethod
    @transaction.atomic
    def execute(*, form, user):

        sample = form.save(commit=False)

        sample.registered_by = user
        sample.case_code = generate_case_code(settings.LAB_CODE)
        sample.laboratory = determine_laboratory(
            sample.sample_type
        )

        sample.save()

        mappings = SampleTypeAssay.objects.filter(
            sample_type=sample.sample_type
        ).select_related("assay")

        AssayOrder.objects.bulk_create(
            [
                AssayOrder(
                    sample=sample,
                    assay=mapping.assay,
                )
                for mapping in mappings
            ]
        )

        return sample
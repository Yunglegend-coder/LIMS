from django.conf import settings
from django.db import transaction

from assays.models import AssayOrder, AssayStatus, SampleTypeAssay
from core.utils.case_code import generate_case_code
from core.utils.laboratory import determine_laboratory
from .choices import DocSubtype, SampleType


class RegisterSampleService:

    @staticmethod
    @transaction.atomic
    def execute(*, form, user):

        sample = form.save(commit=False)

        sample.registered_by = user
        sample.case_code = (
            (form.cleaned_data.get("case_code") or "").strip()
            or generate_case_code(settings.LAB_CODE)
        )
        sample.laboratory = determine_laboratory(
            sample.sample_type
        )

        sample.save()

        mappings = list(
            SampleTypeAssay.objects.filter(
                sample_type=sample.sample_type,
            ).values_list("assay_id", "doc_subtype")
        )
        assay_orders = []
        if sample.sample_type == SampleType.DOC:
            by_assay = {}
            for assay_id, subtype in mappings:
                by_assay.setdefault(assay_id, set()).add(subtype)
            for assay_id, subtypes in by_assay.items():
                specific_subtypes = [
                    value for value, _ in DocSubtype.choices if value in subtypes
                ]
                order_subtypes = specific_subtypes or ([""] if "" in subtypes else [])
                assay_orders.extend(
                    AssayOrder(sample=sample, assay_id=assay_id, doc_subtype=subtype)
                    for subtype in order_subtypes
                )
        else:
            assay_orders = [
                AssayOrder(sample=sample, assay_id=assay_id)
                for assay_id, subtype in mappings
                if not subtype
            ]

        AssayOrder.objects.bulk_create(assay_orders)

        from accounts.messaging import notify_staff_of_new_sample
        transaction.on_commit(
            lambda registered_sample=sample: notify_staff_of_new_sample(registered_sample)
        )

        return sample


def sync_pending_assay_orders(sample):
    """Add pending orders required by the current assay mapping for a sample."""
    existing_orders = list(
        sample.assay_orders.values_list("assay_id", "doc_subtype")
    )
    if not existing_orders:
        return

    mappings = list(
        SampleTypeAssay.objects.filter(
            sample_type=sample.sample_type,
        ).values_list("assay_id", "doc_subtype")
    )
    expected = set()
    if sample.sample_type == SampleType.DOC:
        by_assay = {}
        for assay_id, subtype in mappings:
            by_assay.setdefault(assay_id, set()).add(subtype)
        for assay_id, subtypes in by_assay.items():
            specific = {value for value in subtypes if value}
            expected.update((assay_id, value) for value in specific)
            if not specific and "" in subtypes:
                expected.add((assay_id, ""))
    else:
        expected = {(assay_id, "") for assay_id, subtype in mappings if not subtype}

    existing = set(existing_orders)
    missing = expected - existing
    new_orders = []
    for assay_id, subtype in sorted(missing):
        if subtype:
            generic_pending = sample.assay_orders.filter(
                assay_id=assay_id,
                doc_subtype="",
                status__in=(AssayStatus.PENDING, AssayStatus.IN_PROGRESS),
                result__isnull=True,
            ).first()
            if generic_pending:
                generic_pending.doc_subtype = subtype
                generic_pending.save(update_fields=["doc_subtype"])
                continue
        new_orders.append(
            AssayOrder(sample=sample, assay_id=assay_id, doc_subtype=subtype)
        )
    if new_orders:
        AssayOrder.objects.bulk_create(new_orders)

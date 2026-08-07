from .models import AssayOrder, SampleTypeAssay


def create_default_assays(sample):
    """
    Automatically create all assay orders
    required for a newly registered sample.
    """

    mappings = (
        SampleTypeAssay.objects
        .filter(sample_type=sample.sample_type)
        .select_related("assay")
    )

    assay_orders = [
        AssayOrder(
            sample=sample,
            assay=mapping.assay,
        )
        for mapping in mappings
    ]

    AssayOrder.objects.bulk_create(assay_orders)
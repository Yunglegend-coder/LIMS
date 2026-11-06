from django.db import migrations


def sync_existing_pending_orders(apps, schema_editor):
    Sample = apps.get_model('samples', 'Sample')
    SampleTypeAssay = apps.get_model('assays', 'SampleTypeAssay')
    AssayOrder = apps.get_model('assays', 'AssayOrder')

    for sample in Sample.objects.all().iterator():
        mappings = list(
            SampleTypeAssay.objects.filter(
                sample_type=sample.sample_type,
            ).values_list('assay_id', 'doc_subtype')
        )
        expected = set()
        if sample.sample_type == 'DOC':
            by_assay = {}
            for assay_id, subtype in mappings:
                by_assay.setdefault(assay_id, set()).add(subtype)
            for assay_id, subtypes in by_assay.items():
                specific = {subtype for subtype in subtypes if subtype}
                expected.update((assay_id, subtype) for subtype in specific)
                if not specific and '' in subtypes:
                    expected.add((assay_id, ''))
        else:
            expected = {(assay_id, '') for assay_id, subtype in mappings if not subtype}

        existing = set(
            AssayOrder.objects.filter(sample_id=sample.pk).values_list(
                'assay_id', 'doc_subtype'
            )
        )
        if not existing:
            continue
        for assay_id, subtype in sorted(expected - existing):
            if subtype:
                generic_pending = AssayOrder.objects.filter(
                    sample_id=sample.pk,
                    assay_id=assay_id,
                    doc_subtype='',
                    status__in=('PENDING', 'IN_PROGRESS'),
                    result__isnull=True,
                ).first()
                if generic_pending:
                    generic_pending.doc_subtype = subtype
                    generic_pending.save(update_fields=['doc_subtype'])
                    continue
            AssayOrder.objects.create(
                sample_id=sample.pk,
                assay_id=assay_id,
                doc_subtype=subtype,
            )


class Migration(migrations.Migration):

    dependencies = [
        ('assays', '0006_remove_assayorder_unique_sample_assay_and_more'),
        ('samples', '0008_remove_sample_doc_subtype_sample_doc_subtypes'),
    ]

    operations = [
        migrations.RunPython(sync_existing_pending_orders, migrations.RunPython.noop),
    ]

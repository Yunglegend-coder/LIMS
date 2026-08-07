from samples.models import (
    Laboratory,
    SampleType,
)


LAB_MAPPING = {

    SampleType.CARCASS: Laboratory.MICROBIOLOGY,

    SampleType.DOC_TISSUE: Laboratory.MICROBIOLOGY,

    SampleType.DOC_INTESTINE: Laboratory.MICROBIOLOGY,

    SampleType.DOC_YOLK_SAC: Laboratory.MICROBIOLOGY,

    SampleType.WATER: Laboratory.MICROBIOLOGY,

    SampleType.FEED: Laboratory.MICROBIOLOGY,

    SampleType.BOOT_SWAB: Laboratory.MICROBIOLOGY,

    SampleType.FLUFF: Laboratory.MICROBIOLOGY,

    SampleType.EGG: Laboratory.MICROBIOLOGY,

    SampleType.HYGIENE_AUDIT: Laboratory.MICROBIOLOGY,

    SampleType.SERUM: Laboratory.SEROLOGY,

    SampleType.TRACHEAL_SWAB: Laboratory.MOLECULAR,

    SampleType.CLOACAL_SWAB: Laboratory.MOLECULAR,
}


def determine_laboratory(sample_type):
    return LAB_MAPPING[sample_type]
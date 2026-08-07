from core.models import LaboratorySite
from django.db import models
from locations.models import House
from django.conf import settings
from locations.models import Farm



class SampleType(models.TextChoices):

    CARCASS = "CARCASS", "Carcass/Tissue"

    SERUM = "SERUM", "Serum"

    DOC_TISSUE = "DOC_TISSUE", "DOC Tissue"

    DOC_INTESTINE = "DOC_INTESTINE", "DOC Intestine"

    DOC_YOLK_SAC = "DOC_YOLK_SAC", "DOC Yolk Sac"

    WATER = "WATER", "Water"

    FEED = "FEED", "Feed"

    BOOT_SWAB = "BOOT_SWAB", "Boot Swab"

    TRACHEAL_SWAB = "TRACHEAL_SWAB", "Tracheal Swab"

    CLOACAL_SWAB = "CLOACAL_SWAB", "Cloacal Swab"

    FLUFF = "FLUFF", "Fluff"

    HYGIENE_AUDIT = "HYGIENE_AUDIT", "Hygiene Audit"

    EGG = "EGG", "Egg"

class SampleCondition(models.TextChoices):
    GOOD = "GOOD", "Good"
    POOR = "POOR", "Poor"
    LEAKING = "LEAKING", "Leaking"
    DECOMPOSED = "DECOMPOSED", "Decomposed"

class Laboratory(models.TextChoices):
    MICROBIOLOGY = "MICRO", "Microbiology"
    SEROLOGY = "SERO", "Serology"
    MOLECULAR = "PCR", "Molecular Biology"

class SampleStatus(models.TextChoices):
    RECEIVED = "RECEIVED", "Received"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    REPORTED = "REPORTED", "Reported"

class Priority(models.TextChoices):
    NORMAL = "NORMAL", "Normal"
    URGENT = "URGENT", "Urgent"
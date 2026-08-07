from django.db import models

class LaboratorySite(models.Model):

    code = models.CharField(
        max_length=5,
        unique=True,
    )

    name = models.CharField(
        max_length=100,
    )

    active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return self.name
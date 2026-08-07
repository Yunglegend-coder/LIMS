from django.db import models

from customers.models import Customer


class Farm(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="farms",
    )

    name = models.CharField(max_length=200)

    address = models.TextField(blank=True)

    state = models.CharField(max_length=100, blank=True)

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "name"],
                name="unique_customer_farm",
            )
        ]

    def __str__(self):
        return self.name


class House(models.Model):
    farm = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        related_name="houses",
    )

    name = models.CharField(max_length=100)

    bird_type = models.CharField(
        max_length=100,
        blank=True,
    )

    capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["farm", "name"],
                name="unique_farm_house",
            )
        ]

    def __str__(self):
        return f"{self.farm.name} - {self.name}"
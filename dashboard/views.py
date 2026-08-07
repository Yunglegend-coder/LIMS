from django.views.generic import TemplateView

from samples.models import Sample
from customers.models import Customer
from locations.models import Farm, House


class DashboardView(TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["sample_count"] = Sample.objects.count()
        context["customer_count"] = Customer.objects.count()
        context["farm_count"] = Farm.objects.count()
        context["house_count"] = House.objects.count()

        context["pending_count"] = Sample.objects.filter(
            status="RECEIVED"
        ).count()

        context["recent_samples"] = (
            Sample.objects
            .select_related("farm", "house")
            .order_by("-created_at")[:10]
        )

        return context
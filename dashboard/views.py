from django.views.generic import TemplateView

from samples.models import Sample
from customers.models import Customer
from locations.models import Farm, House
from assays.models import AssayOrder, AssayStatus, LaboratorySection
from django.utils import timezone


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

        today = timezone.localdate()
        month_start = today.replace(day=1)
        department_stats = []
        display_names = {
            LaboratorySection.MICROBIOLOGY: "Microbiology",
            LaboratorySection.SEROLOGY: "Serology",
            LaboratorySection.MOLECULAR: "PCR / Molecular",
        }
        for section, label in LaboratorySection.choices:
            orders = AssayOrder.objects.filter(assay__laboratory_section=section)
            month_samples = Sample.objects.filter(
                received_date__gte=month_start,
                received_date__lte=today,
                assay_orders__assay__laboratory_section=section,
            ).distinct().count()
            department_stats.append({
                "key": section,
                "name": display_names.get(section, label),
                "month_samples": month_samples,
                "pending": orders.filter(status__in=[AssayStatus.PENDING, AssayStatus.IN_PROGRESS]).count(),
                "completed_this_month": orders.filter(
                    status=AssayStatus.COMPLETED,
                    completed_at__date__gte=month_start,
                    completed_at__date__lte=today,
                ).count(),
                "total_open": orders.filter(status__in=[AssayStatus.PENDING, AssayStatus.IN_PROGRESS]).count(),
            })
        context["department_stats"] = department_stats
        context["month_label"] = today.strftime("%B %Y")

        return context

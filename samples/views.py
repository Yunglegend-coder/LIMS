from django.db.models import Q
from .forms import SampleForm
from .services import RegisterSampleService
from .models import Sample
from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import (
    ListView,
    CreateView,
    DetailView,
)
from accounts.models import UserRole
from core.access import RoleRequiredMixin


class SampleListView(ListView):
    model = Sample
    template_name = "samples/sample_list.html"
    context_object_name = "samples"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            Sample.objects
            .select_related(
                "farm",
                "farm__customer",
                "house",
            )
            .order_by("-received_date", "-id")
        )

        search = self.request.GET.get("search")

        if search:
            queryset = queryset.filter(
                Q(case_code__icontains=search)
                | Q(farm__customer__name__icontains=search)
                | Q(farm__name__icontains=search)
                | Q(house__name__icontains=search)
            )

        return queryset

class SampleCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = (UserRole.RECEPTIONIST, UserRole.MANAGER)
    allow_receptionist = True
    model = Sample
    form_class = SampleForm
    template_name = "samples/sample_form.html"

    def form_valid(self, form):

        sample = RegisterSampleService.execute(
            form=form,
            user=self.request.user,
        )

        messages.success(
            self.request,
            "Sample registered successfully."
        )

        if self.request.user.profile.role == UserRole.RECEPTIONIST:
            return redirect("sample_create")
        return redirect("sample_detail", pk=sample.pk)


class SampleDetailView(DetailView):
    model = Sample
    template_name = "samples/sample_detail.html"
    context_object_name = "sample"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sample = context["sample"]
        details = [
            ("Age", sample.age),
            ("Breed/Species", sample.breed_species),
            ("Source of Birds", sample.source_of_birds),
            ("Feed", sample.feed_type),
            ("Population", sample.population),
            ("Water Source", sample.source_of_water),
            ("Housing", sample.housing),
            ("Major Complaint", sample.major_complaint),
            ("Mortality pattern", sample.mortality_pattern),
            ("Medication", sample.medication),
            ("Vaccination History", sample.vaccination_history),
            ("Drugs", sample.drugs),
            ("Vaccination", sample.vaccination),
            ("Last vaccination date", sample.last_vaccination),
        ]
        context["clinical_details"] = details
        context["has_clinical_details"] = any(value for _, value in details)
        return context

    def get_queryset(self):
        return (
            Sample.objects
            .select_related(
                "farm",
                "farm__customer",
                "house",
                "registered_by",
            )
            .prefetch_related(
                "assay_orders__assay",
            )
        )



class SampleFinalResultView(DetailView):
    model = Sample
    template_name = "samples/sample_final_result.html"
    context_object_name = "sample"

    def get_queryset(self):
        return (
            Sample.objects
            .select_related(
                "farm",
                "house",
                "farm__customer",
                "registered_by",
            )
            .prefetch_related(
                "assay_orders__assay",
                "assay_orders__result",
                "assay_orders__result__binary_result",
                "assay_orders__result__gram_result",
                "assay_orders__result__tsi_result",
                "assay_orders__result__ast_result",
                "assay_orders__result__ast_result__items",
                "assay_orders__result__ast_result__items__antibiotic",
                "assay_orders__result__ndhi_result",
                "assay_orders__result__pcr_result",
                "assay_orders__result__instrument_result",
                "assay_orders__result__count_result",
                "assay_orders__result__fungal_result",
            )
        )

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

class SampleCreateView(CreateView):
    model = Sample
    form_class = SampleForm
    template_name = "samples/sample_form.html"

    def form_valid(self, form):

        RegisterSampleService.execute(
            form=form,
            user=self.request.user,
        )

        messages.success(
            self.request,
            "Sample registered successfully."
        )

        return redirect("sample_list")


class SampleDetailView(DetailView):
    model = Sample
    template_name = "samples/sample_detail.html"
    context_object_name = "sample"

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
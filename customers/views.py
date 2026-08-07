from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)

from .forms import CustomerForm
from .models import Customer
from django.db.models import Q
from django.contrib import messages

class CustomerListView(ListView):
    model = Customer

    template_name = "customers/customer_list.html"

    context_object_name = "customers"

    paginate_by = 20

    ordering = ["name"]

    def get_queryset(self):

        queryset = Customer.objects.all().order_by("name")

        search = self.request.GET.get("search")

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(whatsapp__icontains=search)
            )

        return queryset

class CustomerDetailView(DetailView):
    model = Customer

    template_name = "customers/customer_detail.html"

    context_object_name = "customer"

class CustomerCreateView(CreateView):

    model = Customer

    form_class = CustomerForm

    template_name = "customers/customer_form.html"

    success_url = reverse_lazy("customer_list")

    def form_valid(self, form):

        response = super().form_valid(form)

        messages.success(
            self.request,
            "Customer registered successfully."
        )

        return response


class CustomerUpdateView(UpdateView):

    model = Customer

    form_class = CustomerForm

    template_name = "customers/customer_form.html"

    success_url = reverse_lazy("customer_list")

    def form_valid(self, form):

        response = super().form_valid(form)

        messages.success(
            self.request,
            "Customer updated successfully."
        )

        return response

class CustomerDeleteView(DeleteView):

    model = Customer

    template_name = "customers/customer_confirm_delete.html"

    success_url = reverse_lazy("customer_list")

    def form_valid(self, form):

        messages.success(
            self.request,
            "Customer deleted successfully."
        )

        return super().form_valid(form)
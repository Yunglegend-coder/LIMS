from django.conf import settings
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    FormView,
)
from django.core.mail import send_mass_mail
from django.shortcuts import redirect
from django.db import transaction
from accounts.models import UserRole
from accounts.messaging import email_delivery_status
from core.access import RoleRequiredMixin

from .forms import CustomerEmailCampaignForm, CustomerFarmFormSet, CustomerForm
from .models import Customer, CustomerEmailCampaign
from django.db.models import Q
from django.contrib import messages

class CustomerListView(ListView):
    model = Customer

    template_name = "customer/customer_list.html"

    context_object_name = "customers"

    paginate_by = 20

    ordering = ["name"]

    def get_queryset(self):

        queryset = Customer.objects.prefetch_related("farms").order_by("name")

        search = self.request.GET.get("search")

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(farms__name__icontains=search) |
                Q(email__icontains=search) |
                Q(whatsapp__icontains=search)
            ).distinct()

        return queryset

class CustomerDetailView(DetailView):
    model = Customer

    template_name = "customer/customer_detail.html"

    context_object_name = "customer"

    def get_queryset(self):
        return Customer.objects.prefetch_related("farms")

class CustomerFormsetMixin:
    formset_prefix = "farms"
    success_message = "Customer saved successfully."

    def get_farm_formset(self, data=None):
        return CustomerFarmFormSet(
            data=data,
            instance=getattr(self, "object", None),
            prefix=self.formset_prefix,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["farm_formset"] = kwargs.get(
            "farm_formset",
            self.get_farm_formset(self.request.POST if self.request.method == "POST" else None),
        )
        return context

    def form_valid(self, form):
        farm_formset = self.get_farm_formset(self.request.POST)
        if not farm_formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form, farm_formset=farm_formset))

        with transaction.atomic():
            self.object = form.save()
            farm_formset.instance = self.object
            farm_formset.save()
        messages.success(self.request, self.success_message)
        return redirect(self.get_success_url())


class CustomerCreateView(CustomerFormsetMixin, RoleRequiredMixin, CreateView):
    allowed_roles = (UserRole.RECEPTIONIST, UserRole.MANAGER)

    model = Customer

    form_class = CustomerForm

    template_name = "customer/customer_form.html"

    success_url = reverse_lazy("customer_list")

    success_message = "Customer registered successfully."


class CustomerUpdateView(CustomerFormsetMixin, RoleRequiredMixin, UpdateView):
    allowed_roles = (UserRole.RECEPTIONIST, UserRole.MANAGER)

    model = Customer

    form_class = CustomerForm

    template_name = "customer/customer_form.html"

    success_url = reverse_lazy("customer_list")

    success_message = "Customer updated successfully."

class CustomerDeleteView(RoleRequiredMixin, DeleteView):
    allowed_roles = (UserRole.RECEPTIONIST, UserRole.MANAGER)

    model = Customer

    template_name = "customer/customer_confirm_delete.html"

    success_url = reverse_lazy("customer_list")

    def form_valid(self, form):

        messages.success(
            self.request,
            "Customer deleted successfully."
        )

        return super().form_valid(form)


class CustomerEmailCampaignView(RoleRequiredMixin, FormView):
    allowed_roles = (UserRole.RECEPTIONIST, UserRole.MANAGER)
    form_class = CustomerEmailCampaignForm
    template_name = "customers/email_campaign.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ready, status = email_delivery_status()
        context["email_delivery_ready"] = ready
        context["email_delivery_status"] = status
        return context

    def form_valid(self, form):
        email_ready, email_status = email_delivery_status()
        if not email_ready:
            messages.error(self.request, email_status)
            return self.form_invalid(form)

        recipients = list(form.cleaned_data["customers"])
        subject = form.cleaned_data["subject"]
        body = form.cleaned_data["body"]
        messages_to_send = [
            (
                subject,
                f"Dear {customer.name},\n\n{body}",
                settings.DEFAULT_FROM_EMAIL,
                [customer.email],
            )
            for customer in recipients
        ]
        try:
            send_mass_mail(messages_to_send, fail_silently=False)
        except Exception:
            messages.error(
                self.request,
                "Email delivery failed. Check the email settings and try again.",
            )
            return self.form_invalid(form)

        CustomerEmailCampaign.objects.create(
            subject=subject,
            body=body,
            sent_by=self.request.user,
            recipient_count=len(recipients),
        )
        messages.success(
            self.request,
            f"Email sent to {len(recipients)} customer(s).",
        )
        return redirect("customer_list")

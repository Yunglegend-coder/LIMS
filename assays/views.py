from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import DetailView, View

from .models import AssayOrder


class AssayOrderDetailView(DetailView):
    model = AssayOrder
    template_name = "assays/assay_order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        return (
            AssayOrder.objects
            .select_related(
                "sample",
                "sample__farm",
                "sample__farm__customer",
                "sample__house",
                "assay",
                "assigned_to",
                "result",
                "result__binary_result",
                "result__gram_result",
                "result__ast_result",
                "result__ndhi_result",
                "result__pcr_result",
            )
            .prefetch_related(
                "result__ast_result__items__antibiotic",
            )
        )

class AssayOrderStartView(LoginRequiredMixin, View):

    def post(self, request, pk):

        order = AssayOrder.objects.get(pk=pk)

        if order.status != "PENDING":
            messages.warning(
                request,
                "This assay cannot be started because it is no longer pending."
            )
            return redirect(
                "assay_order_detail",
                pk=order.pk,
            )

        order.status = "IN_PROGRESS"

        if order.assigned_to is None:
            order.assigned_to = request.user

        order.save(
            update_fields=[
                "status",
                "assigned_to",
            ]
        )

        messages.success(
            request,
            f"{order.assay.name} has been started."
        )

        return redirect(
            "assay_order_detail",
            pk=order.pk,
        )
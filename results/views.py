from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import (
    CreateView,
    TemplateView,
    ListView,
)
from assays.models import (
    AssayOrder,
    AssayStatus,
    AssayCategory,
    LaboratorySection,
    AssayType,
)

from .models import (
    AssayResult,
    BinaryResult,
)

from .forms import (
    BinaryResultForm,
    GramStainResultForm,
    ASTResultForm,
    ASTResultItemFormSet,
    NDHIResultForm,
    PCRResultForm,
    TSIResultForm,
    CultureResultForm,
)


class AssayResultCreateView(LoginRequiredMixin, CreateView):

    model = AssayResult

    def dispatch(self, request, *args, **kwargs):

        self.assay_order = get_object_or_404(
            AssayOrder.objects.select_related(
                "sample",
                "assay",
            ),
            pk=kwargs["pk"],
        )

        # ---------------------------------------------------------
        # Prevent duplicate result entry
        # ---------------------------------------------------------

        if hasattr(self.assay_order, "result"):

            messages.info(
                request,
                "A result has already been recorded for this assay.",
            )

            return redirect(
                "assay_order_detail",
                pk=self.assay_order.pk,
            )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    # ============================================================
    # FORM SELECTION
    # ============================================================

    def get_form_class(self):

        category = self.assay_order.assay.category

        form_classes = {

            AssayCategory.BINARY:
                BinaryResultForm,

            AssayCategory.GRAM:
                GramStainResultForm,

            AssayCategory.TSI:
                TSIResultForm,

            AssayCategory.CULTURE:
                CultureResultForm,

            AssayCategory.AST:
                ASTResultForm,

            AssayCategory.NDHI:
                NDHIResultForm,

            AssayCategory.PCR:
                PCRResultForm,
        }

        form_class = form_classes.get(category)

        if form_class is None:

            raise NotImplementedError(
                f"No result form has been implemented for "
                f"assay category: {category}"
            )

        return form_class

    # ============================================================
    # TEMPLATE
    # ============================================================

    def get_template_names(self):

        category = self.assay_order.assay.category

        templates = {

            AssayCategory.BINARY:
                "results/binary_result_form.html",

            AssayCategory.GRAM:
                "results/gram_stain_result_form.html",

            AssayCategory.TSI:
                "results/tsi_result_form.html",

            AssayCategory.CULTURE:
                "results/culture_result_form.html",

            AssayCategory.AST:
                "results/ast_result_form.html",

            AssayCategory.NDHI:
                "results/ndhi_result_form.html",

            AssayCategory.PCR:
                "results/pcr_result_form.html",
        }

        template = templates.get(category)

        if template is None:

            raise NotImplementedError(
                f"No result template has been implemented for "
                f"assay category: {category}"
            )

        return [template]

    # ============================================================
    # CONTEXT
    # ============================================================

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["order"] = self.assay_order
        context["sample"] = self.assay_order.sample
        context["assay"] = self.assay_order.assay

        # ---------------------------------------------------------
        # AST formset
        # ---------------------------------------------------------

        if self.assay_order.assay.category == AssayCategory.AST:

            if self.request.POST:

                context["formset"] = ASTResultItemFormSet(
                    self.request.POST,
                    prefix="ast",
                )

            else:

                context["formset"] = ASTResultItemFormSet(
                    prefix="ast",
                )

        return context

    # ============================================================
    # FORM VALIDATION
    # ============================================================

    def post(self, request, *args, **kwargs):

        self.object = None

        self.assay_order = get_object_or_404(
            AssayOrder.objects.select_related(
                "sample",
                "assay",
            ),
            pk=kwargs["pk"],
        )

        form = self.get_form()

        # ---------------------------------------------------------
        # AST requires both the main form and formset
        # ---------------------------------------------------------

        if self.assay_order.assay.category == AssayCategory.AST:

            formset = ASTResultItemFormSet(
                request.POST,
                prefix="ast",
            )

            if form.is_valid() and formset.is_valid():

                return self.form_valid(
                    form,
                    formset=formset,
                )

            return self.form_invalid(
                form,
                formset=formset,
            )

        # ---------------------------------------------------------
        # All other result types
        # ---------------------------------------------------------

        if form.is_valid():

            return self.form_valid(form)

        return self.form_invalid(form)

    # ============================================================
    # SAVE RESULT
    # ============================================================

    @transaction.atomic
    def form_valid(self, form, *, formset=None):

        # ---------------------------------------------------------
        # 1. Create common AssayResult
        # ---------------------------------------------------------

        assay_result = AssayResult.objects.create(
            assay_order=self.assay_order,
            performed_by=self.request.user,
        )

        # ---------------------------------------------------------
        # 2. Save category-specific result
        # ---------------------------------------------------------

        form.save(
            commit=True,
            assay_result=assay_result,
        )

        # ---------------------------------------------------------
        # 3. AST items
        # ---------------------------------------------------------

        if formset is not None:

            ast_result = assay_result.ast_result

            formset.instance = ast_result

            formset.save()

        # ---------------------------------------------------------
        # 4. Complete assay order
        # ---------------------------------------------------------

        self.assay_order.status = AssayStatus.COMPLETED

        self.assay_order.completed_at = timezone.now()

        self.assay_order.save(
            update_fields=[
                "status",
                "completed_at",
            ]
        )

        # ============================================================
        # 5. Update overall sample status
        # ============================================================

        self.assay_order.sample.update_status_from_assays()

        # ---------------------------------------------------------
        # 5. Success message
        # ---------------------------------------------------------

        messages.success(
            self.request,
            "Laboratory result recorded successfully.",
        )

        # ============================================================
        # 6. Return to pending results
        # ============================================================

        return redirect(
            "pending_results",
            laboratory=self.assay_order.assay.laboratory_section,
        )

    # ============================================================
    # INVALID FORM
    # ============================================================

    def form_invalid(self, form, *, formset=None):

        context = self.get_context_data(
            form=form,
        )

        if formset is not None:

            context["formset"] = formset

        return self.render_to_response(
            context
        )

class PendingResultsView(LoginRequiredMixin, ListView):

    model = AssayOrder
    template_name = "results/pending_results.html"
    context_object_name = "assay_orders"

    def get_queryset(self):

        laboratory = self.kwargs["laboratory"]

        return (
            AssayOrder.objects
            .filter(
                assay__laboratory_section=laboratory,
            )
            .exclude(
                status=AssayStatus.COMPLETED,
            )
            .select_related(
                "sample",
                "assay",
                "sample__farm",
            )
            .order_by(
                "assay__name",
                "sample__case_code",
            )
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        laboratory = self.kwargs["laboratory"]

        context["laboratory"] = laboratory

        context["laboratory_display"] = dict(
            LaboratorySection.choices
        ).get(
            laboratory,
            laboratory,
        )

        return context


class PendingAssayResultsView(LoginRequiredMixin, ListView):

    model = AssayOrder
    template_name = "results/pending_assay_results.html"
    context_object_name = "orders"

    def dispatch(self, request, *args, **kwargs):

        self.assay = get_object_or_404(
            AssayType,
            pk=kwargs["assay_pk"],
        )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def get_queryset(self):

        return (
            AssayOrder.objects
            .filter(
                assay=self.assay,
            )
            .exclude(
                status=AssayStatus.COMPLETED,
            )
            .select_related(
                "sample",
                "sample__farm",
                "sample__farm__customer",
                "sample__house",
                "assay",
            )
            .order_by(
                "sample__case_code",
            )
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["assay"] = self.assay

        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):

        orders = self.get_queryset()

        # -----------------------------------------------------
        # Only binary assays for now
        # -----------------------------------------------------

        if self.assay.category != AssayCategory.BINARY:

            messages.error(
                request,
                "Bulk result entry for this assay category has not "
                "been implemented yet.",
            )

            return redirect(
                "pending_assay_results",
                laboratory=self.assay.laboratory_section,
                assay_pk=self.assay.pk,
            )

        saved_count = 0

        for order in orders:

            result_value = request.POST.get(
                f"result_{order.pk}"
            )

            # No result entered for this sample.
            if not result_value:
                continue

            # -------------------------------------------------
            # Create common AssayResult
            # -------------------------------------------------

            assay_result = AssayResult.objects.create(
                assay_order=order,
                performed_by=request.user,
            )

            # -------------------------------------------------
            # Create BinaryResult
            # -------------------------------------------------

            BinaryResult.objects.create(
                assay_result=assay_result,
                result=result_value,
            )

            # -------------------------------------------------
            # Complete assay order
            # -------------------------------------------------

            order.status = AssayStatus.COMPLETED
            order.completed_at = timezone.now()

            order.save(
                update_fields=[
                    "status",
                    "completed_at",
                ]
            )

            # -------------------------------------------------
            # Update sample status
            # -------------------------------------------------

            order.sample.update_status_from_assays()

            saved_count += 1

        if saved_count == 0:

            messages.warning(
                request,
                "No results were entered.",
            )

        else:

            messages.success(
                request,
                f"{saved_count} result(s) saved successfully.",
            )

        return redirect(
            "pending_assay_results",
            laboratory=self.assay.laboratory_section,
            assay_pk=self.assay.pk,
        )

class LaboratoryResultsDashboardView(
    LoginRequiredMixin,
    TemplateView,
):
    template_name = "results/laboratory_results_dashboard.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        pending_orders = (
            AssayOrder.objects
            .filter(
                status__in=[
                    AssayStatus.PENDING,
                    AssayStatus.IN_PROGRESS,
                ]
            )
            .select_related(
                "sample",
                "assay",
            )
        )

        # --------------------------------------------------
        # Group pending assays by laboratory section
        # --------------------------------------------------

        laboratories = {}

        for order in pending_orders:

            section = order.assay.laboratory_section

            if section not in laboratories:
                laboratories[section] = []

            laboratories[section].append(order)

        # --------------------------------------------------
        # Group each laboratory by assay
        # --------------------------------------------------

        grouped_results = {}

        for section, orders in laboratories.items():

            assays = {}

            for order in orders:

                assay_id = order.assay_id

                if assay_id not in assays:

                    assays[assay_id] = {
                        "assay": order.assay,
                        "count": 0,
                    }

                assays[assay_id]["count"] += 1

            grouped_results[section] = list(
                assays.values()
            )

        context["grouped_results"] = grouped_results

        context["total_pending"] = pending_orders.count()

        return context
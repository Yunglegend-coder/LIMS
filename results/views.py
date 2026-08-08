from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import CreateView

from assays.models import (
    AssayOrder,
    AssayStatus,
    AssayCategory,
)

from .models import AssayResult

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

        # ---------------------------------------------------------
        # 5. Success message
        # ---------------------------------------------------------

        messages.success(
            self.request,
            "Laboratory result recorded successfully.",
        )

        # ---------------------------------------------------------
        # 6. Return to assay order
        # ---------------------------------------------------------

        return redirect(
            "assay_order_detail",
            pk=self.assay_order.pk,
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
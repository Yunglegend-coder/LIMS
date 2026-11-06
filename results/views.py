from samples.choices import SampleStatus
from django.conf import settings
from django.db.models import Prefetch
from samples.models import Sample
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.db import transaction
from django.core.mail import EmailMessage
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import (
    CreateView,
    TemplateView,
    ListView,
    UpdateView,
    View,
)
from django.db import transaction
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from results.models import (
    AssayResult,
    BinaryResult,
    ASTResult,
    ASTResultItem,
    Antibiotic,
    TSIChoice,
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
    BinaryChoice,
    GramStainChoice,
    CultureGrowthChoice,
    CountResult,
    GramStainResult,
    TSIResult,
    SampleReport,
    PathologyFinding,
    SampleReportFinding,

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
    SampleReportForm,
)
from .reporting import docx_response, pdf_response
from .reporting import build_report_data
from accounts.messaging import (
    email_delivery_status,
    send_whatsapp_text,
    whatsapp_delivery_status,
)
from accounts.models import UserRole
from core.access import RoleRequiredMixin


class AssayResultCreateView(RoleRequiredMixin, CreateView):
    allowed_roles = (UserRole.LAB_SCIENTIST, UserRole.MANAGER)

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

        # ========================================================
        # TSI
        # ========================================================

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



class PendingAssayResultsView(
    RoleRequiredMixin,
    ListView,
):

    allowed_roles = (UserRole.LAB_SCIENTIST, UserRole.MANAGER)

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

    # ============================================================
    # QUERYSET
    # ============================================================

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

    # ============================================================
    # CONTEXT
    # ============================================================

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["assay"] = self.assay

        # --------------------------------------------------------
        # Antibiotics for AST
        # --------------------------------------------------------

        if self.assay.category == AssayCategory.AST:

            context["antibiotics"] = (
                Antibiotic.objects
                .order_by("code")
            )

        context["bulk_binary_choices"] = BinaryChoice.choices
        context["bulk_gram_choices"] = GramStainChoice.choices
        context["bulk_culture_growth_choices"] = CultureGrowthChoice.choices

        if self.assay.category == AssayCategory.TSI:
            context["tsi_choices"] = TSIChoice.choices

        return context

    # ============================================================
    # POST
    # ============================================================

    @transaction.atomic
    def post(self, request, *args, **kwargs):

        orders = self.get_queryset()

        # ============================================================
        # BINARY BULK ENTRY
        # ============================================================

        if self.assay.category == AssayCategory.BINARY:

            saved_count = 0

            for order in orders:

                result_value = request.POST.get(
                    f"result_{order.pk}"
                )

                # No result entered for this sample
                if not result_value:
                    continue

                # ----------------------------------------------------
                # Create common AssayResult
                # ----------------------------------------------------

                assay_result = AssayResult.objects.create(
                    assay_order=order,
                    performed_by=request.user,
                )

                # ----------------------------------------------------
                # Create BinaryResult
                # ----------------------------------------------------

                BinaryResult.objects.create(
                    assay_result=assay_result,
                    result=result_value,
                )

                # ----------------------------------------------------
                # Complete assay order
                # ----------------------------------------------------

                order.status = AssayStatus.COMPLETED
                order.completed_at = timezone.now()

                order.save(
                    update_fields=[
                        "status",
                        "completed_at",
                    ]
                )

                # ----------------------------------------------------
                # Update sample status
                # ----------------------------------------------------

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

        # ============================================================
        # AST BULK ENTRY
        # ============================================================

        if self.assay.category == AssayCategory.AST:

            saved_count = 0

            for order in orders:

                # ----------------------------------------------------
                # Collect AST entries for this sample
                # ----------------------------------------------------

                ast_items = []

                for antibiotic in Antibiotic.objects.all().order_by(
                        "code"
                ):

                    interpretation = request.POST.get(
                        f"ast_{order.pk}_{antibiotic.pk}"
                    )

                    # Ignore blank cells
                    if not interpretation:
                        continue

                    ast_items.append(
                        (
                            antibiotic,
                            interpretation,
                        )
                    )

                # ----------------------------------------------------
                # Do not create an empty AST result
                # ----------------------------------------------------

                if not ast_items:
                    continue

                # ----------------------------------------------------
                # Create common AssayResult
                # ----------------------------------------------------

                assay_result = AssayResult.objects.create(
                    assay_order=order,
                    performed_by=request.user,
                )

                # ----------------------------------------------------
                # Create ASTResult
                # ----------------------------------------------------

                ast_result = ASTResult.objects.create(
                    assay_result=assay_result,
                )

                # ----------------------------------------------------
                # Create ASTResultItems
                # ----------------------------------------------------

                for antibiotic, interpretation in ast_items:
                    ASTResultItem.objects.create(
                        ast_result=ast_result,
                        antibiotic=antibiotic,
                        interpretation=interpretation,
                    )

                # ----------------------------------------------------
                # Complete assay order
                # ----------------------------------------------------

                order.status = AssayStatus.COMPLETED
                order.completed_at = timezone.now()

                order.save(
                    update_fields=[
                        "status",
                        "completed_at",
                    ]
                )

                # ----------------------------------------------------
                # Update sample status
                # ----------------------------------------------------

                order.sample.update_status_from_assays()

                saved_count += 1

            # ========================================================
            # AST SUCCESS / WARNING
            # ========================================================

            if saved_count == 0:

                messages.warning(
                    request,
                    "No AST results were entered.",
                )

            else:

                messages.success(
                    request,
                    f"{saved_count} AST result(s) saved successfully.",
                )

            return redirect(
                "pending_assay_results",
                laboratory=self.assay.laboratory_section,
                assay_pk=self.assay.pk,
            )

        # ========================================================
        # GRAM STAIN
        # ========================================================

        if (
                self.assay.category
                == AssayCategory.GRAM
        ):

            saved_count = 0

            for order in orders:

                # ------------------------------------------------
                # Get submitted result
                # ------------------------------------------------

                result_value = request.POST.get(
                    f"gram_{order.pk}"
                )

                # No result entered
                if not result_value:
                    continue

                # ------------------------------------------------
                # Create common AssayResult
                # ------------------------------------------------

                assay_result = (
                    AssayResult.objects.create(
                        assay_order=order,
                        performed_by=request.user,
                    )
                )

                # ------------------------------------------------
                # Create GramStainResult
                # ------------------------------------------------

                GramStainResult.objects.create(
                    assay_result=assay_result,
                    result=result_value,
                )

                # ------------------------------------------------
                # Complete assay order
                # ------------------------------------------------

                order.status = (
                    AssayStatus.COMPLETED
                )

                order.completed_at = (
                    timezone.now()
                )

                order.save(
                    update_fields=[
                        "status",
                        "completed_at",
                    ]
                )

                # ------------------------------------------------
                # Update sample status
                # ------------------------------------------------

                order.sample.update_status_from_assays()

                saved_count += 1

            # ----------------------------------------------------
            # Message
            # ----------------------------------------------------

            if saved_count == 0:

                messages.warning(
                    request,
                    "No Gram Stain results were entered.",
                )

            else:

                messages.success(
                    request,
                    f"{saved_count} Gram Stain result(s) "
                    f"saved successfully.",
                )

            return redirect(
                "pending_assay_results",
                laboratory=(
                    self.assay.laboratory_section
                ),
                assay_pk=self.assay.pk,
            )

        # ========================================================
        # TSI BULK ENTRY
        # ========================================================

        if self.assay.category == AssayCategory.TSI:
            valid_values = {value for value, _label in TSIChoice.choices}
            tsi_results = []
            invalid_cases = []

            for order in orders:
                result_value = request.POST.get(f"tsi_{order.pk}", "").strip()
                remarks = request.POST.get(f"tsi_{order.pk}_remarks", "").strip()
                if not result_value:
                    if remarks:
                        invalid_cases.append(order.sample.case_code)
                    continue
                if result_value not in valid_values:
                    invalid_cases.append(order.sample.case_code)
                    continue
                tsi_results.append((order, result_value, remarks))

            if invalid_cases:
                messages.error(
                    request,
                    "Invalid or incomplete TSI result for: "
                    + ", ".join(invalid_cases)
                    + ". No TSI results were saved.",
                )
            elif not tsi_results:
                messages.warning(request, "No TSI results were entered.")
            else:
                for order, result_value, remarks in tsi_results:
                    assay_result = AssayResult.objects.create(
                        assay_order=order,
                        performed_by=request.user,
                        remarks=remarks,
                    )
                    TSIResult.objects.create(
                        assay_result=assay_result,
                        result=result_value,
                    )
                    order.status = AssayStatus.COMPLETED
                    order.completed_at = timezone.now()
                    order.save(update_fields=["status", "completed_at"])
                    order.sample.update_status_from_assays()

                messages.success(
                    request,
                    f"{len(tsi_results)} TSI result(s) saved successfully.",
                )

            return redirect(
                "pending_assay_results",
                laboratory=self.assay.laboratory_section,
                assay_pk=self.assay.pk,
            )

        if self.assay.category == AssayCategory.COUNT:
            count_forms = []
            form_errors = []
            for order in orders:
                raw_count = request.POST.get(f"count_{order.pk}", "").strip()
                unit = request.POST.get(f"count_{order.pk}_unit", "CFU/ml").strip() or "CFU/ml"
                if not raw_count:
                    continue
                try:
                    count_value = int(raw_count)
                    if count_value < 0:
                        raise ValueError
                except ValueError:
                    form_errors.append(order.sample.case_code)
                    continue
                count_forms.append((order, count_value, unit))

            if form_errors:
                messages.error(request, "Enter a whole, non-negative count for: " + ", ".join(form_errors) + ". No count results were saved.")
            elif not count_forms:
                messages.warning(request, "No count results were entered.")
            else:
                for order, count_value, unit in count_forms:
                    assay_result = AssayResult.objects.create(assay_order=order, performed_by=request.user)
                    CountResult.objects.create(assay_result=assay_result, count=count_value, unit=unit)
                    order.status = AssayStatus.COMPLETED
                    order.completed_at = timezone.now()
                    order.save(update_fields=["status", "completed_at"])
                    order.sample.update_status_from_assays()
                messages.success(request, f"{len(count_forms)} count result(s) saved successfully.")

            return redirect("pending_assay_results", laboratory=self.assay.laboratory_section, assay_pk=self.assay.pk)

        # ========================================================
        # CULTURE BULK ENTRY
        # ========================================================

        if self.assay.category == AssayCategory.CULTURE:
            culture_forms = []
            form_errors = []

            for order in orders:
                prefix = f"culture_{order.pk}_"
                form_data = {
                    field: request.POST.get(f"{prefix}{field}", "")
                    for field in (
                        "growth",
                        "organism_name",
                        "colony_description",
                        "identification_notes",
                        "remarks",
                    )
                }
                if not any(value.strip() for value in form_data.values()):
                    continue

                form = CultureResultForm(
                    data=form_data,
                )

                if form.is_valid():
                    culture_forms.append((order, form))
                else:
                    form_errors.append(order.sample.case_code)

            if form_errors:
                messages.error(
                    request,
                    "Invalid culture result for: "
                    + ", ".join(form_errors)
                    + ". No culture results were saved.",
                )
            elif not culture_forms:
                messages.warning(request, "No culture results were entered.")
            else:
                for order, form in culture_forms:
                    assay_result = AssayResult.objects.create(
                        assay_order=order,
                        performed_by=request.user,
                    )
                    form.save(commit=True, assay_result=assay_result)

                    order.status = AssayStatus.COMPLETED
                    order.completed_at = timezone.now()
                    order.save(update_fields=["status", "completed_at"])
                    order.sample.update_status_from_assays()

                messages.success(
                    request,
                    f"{len(culture_forms)} culture result(s) saved successfully.",
                )

            return redirect(
                "pending_assay_results",
                laboratory=self.assay.laboratory_section,
                assay_pk=self.assay.pk,
            )

        if self.assay.category == AssayCategory.NDHI:
            result_forms = []
            form_errors = []
            for order in orders:
                values = {
                    "result": request.POST.get(f"ndhi_{order.pk}", "").strip(),
                    "remarks": request.POST.get(f"ndhi_{order.pk}_remarks", "").strip(),
                }
                if not any(values.values()):
                    continue
                form = NDHIResultForm(data=values)
                if form.is_valid():
                    result_forms.append((order, form))
                else:
                    form_errors.append(order.sample.case_code)

            if form_errors:
                messages.error(request, "Invalid NDHI result for: " + ", ".join(form_errors) + ". No NDHI results were saved.")
            elif not result_forms:
                messages.warning(request, "No NDHI results were entered.")
            else:
                for order, form in result_forms:
                    assay_result = AssayResult.objects.create(assay_order=order, performed_by=request.user)
                    form.save(commit=True, assay_result=assay_result)
                    order.status = AssayStatus.COMPLETED
                    order.completed_at = timezone.now()
                    order.save(update_fields=["status", "completed_at"])
                    order.sample.update_status_from_assays()
                messages.success(request, f"{len(result_forms)} NDHI result(s) saved successfully.")

            return redirect("pending_assay_results", laboratory=self.assay.laboratory_section, assay_pk=self.assay.pk)

        if self.assay.category == AssayCategory.PCR:
            result_forms = []
            form_errors = []
            pcr_fields = ("target", "cq_ct", "result", "interpretation", "remarks")
            for order in orders:
                prefix = f"pcr_{order.pk}_"
                values = {field: request.POST.get(f"{prefix}{field}", "").strip() for field in pcr_fields}
                if not any(values.values()):
                    continue
                form = PCRResultForm(data=values)
                if form.is_valid():
                    result_forms.append((order, form))
                else:
                    form_errors.append(order.sample.case_code)

            if form_errors:
                messages.error(request, "Invalid PCR result for: " + ", ".join(form_errors) + ". No PCR results were saved.")
            elif not result_forms:
                messages.warning(request, "No PCR results were entered.")
            else:
                for order, form in result_forms:
                    assay_result = AssayResult.objects.create(assay_order=order, performed_by=request.user)
                    form.save(commit=True, assay_result=assay_result)
                    order.status = AssayStatus.COMPLETED
                    order.completed_at = timezone.now()
                    order.save(update_fields=["status", "completed_at"])
                    order.sample.update_status_from_assays()
                messages.success(request, f"{len(result_forms)} PCR result(s) saved successfully.")

            return redirect("pending_assay_results", laboratory=self.assay.laboratory_section, assay_pk=self.assay.pk)

        # ============================================================
        # OTHER ASSAY TYPES
        # ============================================================

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



class LaboratoryResultsDashboardView(
    LoginRequiredMixin,
    TemplateView,
):
    template_name = "results/laboratory_results_dashboard.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        # ============================================================
        # PENDING RESULTS
        # ============================================================

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

        # ============================================================
        # COMPLETED RESULTS
        # ============================================================

        completed_orders = (
            AssayOrder.objects
            .filter(
                status=AssayStatus.COMPLETED,
                result__isnull=False,
            )
            .select_related(
                "sample",
                "assay",
            )
        )

        # ============================================================
        # LABORATORY SECTIONS
        # ============================================================

        laboratories = {}

        for laboratory, laboratory_display in LaboratorySection.choices:

            laboratories[laboratory] = {
                "value": laboratory,
                "display": laboratory_display,
                "pending_count": 0,
                "completed_count": 0,
            }

        # ============================================================
        # COUNT PENDING
        # ============================================================

        for order in pending_orders:

            laboratory = order.assay.laboratory_section

            if laboratory not in laboratories:
                laboratories[laboratory] = {
                    "value": laboratory,
                    "display": dict(
                        LaboratorySection.choices
                    ).get(
                        laboratory,
                        laboratory,
                    ),
                    "pending_count": 0,
                    "completed_count": 0,
                }

            laboratories[laboratory]["pending_count"] += 1

        # ============================================================
        # COUNT COMPLETED
        # ============================================================

        for order in completed_orders:

            laboratory = order.assay.laboratory_section

            if laboratory not in laboratories:
                laboratories[laboratory] = {
                    "value": laboratory,
                    "display": dict(
                        LaboratorySection.choices
                    ).get(
                        laboratory,
                        laboratory,
                    ),
                    "pending_count": 0,
                    "completed_count": 0,
                }

            laboratories[laboratory]["completed_count"] += 1

        # ============================================================
        # REMOVE EMPTY LABORATORIES
        # ============================================================

        laboratories = {
            key: value
            for key, value in laboratories.items()
            if (
                value["pending_count"] > 0
                or value["completed_count"] > 0
            )
        }

        context["laboratories"] = laboratories

        context["total_pending"] = pending_orders.count()

        context["total_completed"] = completed_orders.count()

        return context

# ============================================================
# COMPLETED SAMPLE RESULTS
# ============================================================

class CompletedResultsView(
    LoginRequiredMixin,
    ListView,
):

    template_name = "results/completed_results.html"

    context_object_name = "samples"

    paginate_by = 20

    # =========================================================
    # QUERYSET
    # =========================================================

    def get_queryset(self):

        # -----------------------------------------------------
        # Laboratory
        # -----------------------------------------------------

        laboratory = self.kwargs.get(
            "laboratory"
        )

        queryset = (
            Sample.objects
            .filter(
                status=SampleStatus.COMPLETED,
            )
            .distinct()
            .select_related(
                "farm",
                "farm__customer",
                "house",
                "site",
            )
        )

        # -----------------------------------------------------
        # Filter by laboratory when supplied
        #
        # Example:
        # /results/completed/MICRO/
        # -----------------------------------------------------

        if laboratory:

            queryset = queryset.filter(
                assay_orders__assay__laboratory_section=laboratory,
                assay_orders__status=AssayStatus.COMPLETED,
            )

        # -----------------------------------------------------
        # SEARCH
        # -----------------------------------------------------

        search = self.request.GET.get(
            "search",
            "",
        ).strip()

        if search:

            queryset = queryset.filter(
                Q(
                    case_code__icontains=search
                )
                | Q(
                    farm__name__icontains=search
                )
                | Q(
                    farm__customer__name__icontains=search
                )
            )

        # -----------------------------------------------------
        # FARM FILTER
        # -----------------------------------------------------

        farm = self.request.GET.get(
            "farm",
        )

        if farm:

            queryset = queryset.filter(
                farm_id=farm,
            )

        # -----------------------------------------------------
        # CUSTOMER FILTER
        # -----------------------------------------------------

        customer = self.request.GET.get(
            "customer",
        )

        if customer:

            queryset = queryset.filter(
                farm__customer_id=customer,
            )

        # -----------------------------------------------------
        # DATE FILTER
        # -----------------------------------------------------

        date_from = self.request.GET.get(
            "date_from",
        )

        date_to = self.request.GET.get(
            "date_to",
        )

        if date_from:

            queryset = queryset.filter(
                received_date__gte=date_from,
            )

        if date_to:

            queryset = queryset.filter(
                received_date__lte=date_to,
            )

        # -----------------------------------------------------
        # SORTING
        # -----------------------------------------------------

        sort = self.request.GET.get(
            "sort",
            "date_desc",
        )

        allowed_sorting = {

            "date_asc":
                "received_date",

            "date_desc":
                "-received_date",

            "case_asc":
                "case_code",

            "case_desc":
                "-case_code",

            "customer_asc":
                "farm__customer__name",

            "customer_desc":
                "-farm__customer__name",

            "farm_asc":
                "farm__name",

            "farm_desc":
                "-farm__name",
        }

        sort_field = allowed_sorting.get(
            sort,
            "-received_date",
        )

        queryset = queryset.order_by(
            sort_field,
            "-created_at",
        )

        return queryset

    # =========================================================
    # CONTEXT
    # =========================================================

    def get_context_data(
        self,
        **kwargs,
    ):

        context = super().get_context_data(
            **kwargs
        )

        # -----------------------------------------------------
        # Laboratory
        # -----------------------------------------------------

        laboratory = self.kwargs.get(
            "laboratory",
            "",
        )

        context["laboratory"] = laboratory

        context["laboratory_display"] = dict(
            LaboratorySection.choices
        ).get(
            laboratory,
            laboratory,
        )

        # -----------------------------------------------------
        # Filter options
        # -----------------------------------------------------

        from locations.models import Farm
        from customers.models import Customer

        context["farms"] = (
            Farm.objects
            .order_by(
                "name"
            )
        )

        context["customers"] = (
            Customer.objects
            .order_by(
                "name"
            )
        )

        # -----------------------------------------------------
        # Current filters
        # -----------------------------------------------------

        context["search"] = (
            self.request.GET.get(
                "search",
                "",
            )
        )

        context["selected_farm"] = (
            self.request.GET.get(
                "farm",
                "",
            )
        )

        context["selected_customer"] = (
            self.request.GET.get(
                "customer",
                "",
            )
        )

        context["date_from"] = (
            self.request.GET.get(
                "date_from",
                "",
            )
        )

        context["date_to"] = (
            self.request.GET.get(
                "date_to",
                "",
            )
        )

        context["sort"] = (
            self.request.GET.get(
                "sort",
                "date_desc",
            )
        )

        return context


# ============================================================
# FINAL SAMPLE LABORATORY RESULT
# ============================================================

class SampleFinalResultView(
    RoleRequiredMixin,
    TemplateView,
):

    allowed_roles = (UserRole.VET_DOCTOR, UserRole.MANAGER)

    template_name = "results/sample_final_result.html"

    def post(self, request, *args, **kwargs):
        try:
            report = self.sample.report
        except SampleReport.DoesNotExist:
            report = None
        form = SampleReportForm(request.POST, instance=report)
        finding_values = {}
        pathology_errors = []
        for key, value in request.POST.items():
            if key.startswith("pathology_"):
                try:
                    finding_values[int(key.removeprefix("pathology_"))] = int(value) if value.strip() else 0
                except (TypeError, ValueError):
                    pathology_errors.append("Enter a whole number for each pathology count.")
        new_names = request.POST.getlist("new_pathology_name")
        new_counts = request.POST.getlist("new_pathology_count")
        new_rows = list(zip(new_names, new_counts)) or [("", "")]

        if form.is_valid():
            total = form.cleaned_data["carcass_count"]
            if any(count < 0 for count in finding_values.values()):
                pathology_errors.append("Pathology counts cannot be negative.")
            if any(count > 0 for count in finding_values.values()) and not total:
                pathology_errors.append("Enter the total number of carcasses before adding pathology counts.")
            if total and any(count > total for count in finding_values.values()):
                pathology_errors.append("A pathology count cannot exceed the total carcasses examined.")
            normalized_names = set()
            for name, raw_count in new_rows:
                name = name.strip()
                if not name and not raw_count.strip():
                    continue
                try:
                    count = int(raw_count)
                except (TypeError, ValueError):
                    pathology_errors.append(f"Enter a whole number for {name or 'the new pathology'}.")
                    continue
                normalized = name.casefold()
                if not name:
                    pathology_errors.append("Enter a name for each new pathology.")
                elif len(name) > 120:
                    pathology_errors.append("Pathology names must be 120 characters or fewer.")
                elif count < 1:
                    pathology_errors.append(f"The count for {name} must be at least 1.")
                elif total and count > total:
                    pathology_errors.append(f"The count for {name} cannot exceed the total carcasses examined.")
                if normalized in normalized_names:
                    pathology_errors.append(f"{name} was entered more than once.")
                normalized_names.add(normalized)
                existing = PathologyFinding.objects.filter(name__iexact=name).first() if name else None
                if existing and existing.pk in finding_values and finding_values[existing.pk]:
                    pathology_errors.append(f"{name} is already selected above.")
            if pathology_errors:
                context = self.get_context_data(
                    report_form=form,
                    pathology_count_values=finding_values,
                    new_pathology_rows=new_rows,
                    pathology_errors=pathology_errors,
                )
                return self.render_to_response(context)

            report = form.save(commit=False)
            report.sample = self.sample
            report.updated_by = request.user
            report.save()
            report.pathology_findings.all().delete()
            total = report.carcass_count
            for finding_id, count in finding_values.items():
                if count > 0:
                    finding = PathologyFinding.objects.get(pk=finding_id, is_active=True)
                    SampleReportFinding.objects.create(sample_report=report, finding=finding, carcass_count=count)
            for name, raw_count in new_rows:
                name = name.strip()
                if name and raw_count.strip():
                    finding = PathologyFinding.objects.filter(name__iexact=name).first()
                    if finding is None:
                        finding = PathologyFinding.objects.create(name=name)
                    if not finding.is_active:
                        finding.is_active = True
                        finding.save(update_fields=["is_active"])
                    SampleReportFinding.objects.create(sample_report=report, finding=finding, carcass_count=int(raw_count))
            messages.success(request, "Report narrative and necropsy findings saved.")
            return redirect("sample_final_result", pk=self.sample.pk)

        context = self.get_context_data(report_form=form, pathology_count_values=finding_values, new_pathology_rows=new_rows)
        return self.render_to_response(context)

    def dispatch(
        self,
        request,
        *args,
        **kwargs,
    ):

        self.sample = get_object_or_404(
            Sample.objects.select_related(
                "farm",
                "farm__customer",
                "house",
                "site",
                "registered_by",
            ),
            pk=kwargs["pk"],
        )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    # =========================================================
    # CONTEXT
    # =========================================================

    def get_context_data(
        self,
        **kwargs,
    ):

        context = super().get_context_data(
            **kwargs
        )

        # -----------------------------------------------------
        # All completed assay orders for this sample
        # -----------------------------------------------------

        assay_orders = (
            AssayOrder.objects
            .filter(
                sample=self.sample,
                status=AssayStatus.COMPLETED,
                assay__is_biochemical=False,
                assay__is_client_visible=True,
            )
            .select_related(
                "assay",
                "result",
                "result__binary_result",
                "result__gram_result",
                "result__ast_result",
                "result__ndhi_result",
                "result__pcr_result",
                "result__tsi_result",
                "result__culture_result",
                "result__count_result",
            )
            .prefetch_related(
                "result__ast_result__items",
                "result__ast_result__items__antibiotic",
            )
            .order_by(
                "assay__laboratory_section",
                "assay__name",
            )
        )

        # -----------------------------------------------------
        # Group results by laboratory section
        # -----------------------------------------------------

        grouped_results = {}

        for order in assay_orders:

            section = order.assay.laboratory_section

            if section not in grouped_results:

                grouped_results[section] = []

            grouped_results[section].append(
                order
            )

        # -----------------------------------------------------
        # Determine laboratory for Back button
        #
        # We use the first completed assay's laboratory.
        # -----------------------------------------------------

        laboratory = (
            assay_orders
            .first()
            .assay
            .laboratory_section
            if assay_orders.exists()
            else None
        )

        # -----------------------------------------------------
        # Context
        # -----------------------------------------------------

        context["sample"] = self.sample

        try:
            report = self.sample.report
        except SampleReport.DoesNotExist:
            report = None
        context["report"] = report
        try:
            signature = self.request.user.profile.signature
            context["exporting_signature_url"] = signature.url if signature else ""
        except (AttributeError, ObjectDoesNotExist, ValueError):
            context["exporting_signature_url"] = ""
        context["exporting_user_name"] = self.request.user.get_full_name() or self.request.user.username
        context["report_form"] = kwargs.get(
            "report_form",
            SampleReportForm(instance=report),
        )
        stored_counts = {
            item.finding_id: item.carcass_count
            for item in report.pathology_findings.all()
        } if report else {}
        counts = kwargs.get("pathology_count_values", stored_counts)
        context["pathology_options"] = [
            (finding, counts.get(finding.pk, 0))
            for finding in PathologyFinding.objects.filter(is_active=True).order_by("name")
        ]
        context["new_pathology_rows"] = kwargs.get("new_pathology_rows", [("", "")])
        context["pathology_errors"] = kwargs.get("pathology_errors", [])
        customer_phone = (
            self.sample.farm.customer.whatsapp
            if self.sample.farm_id
            else ""
        )
        context["whatsapp_delivery_ready"], context["whatsapp_delivery_message"] = (
            whatsapp_delivery_status(customer_phone)
        )
        context["email_delivery_ready"], context["email_delivery_message"] = (
            email_delivery_status()
        )

        context["assay_orders"] = assay_orders

        context["grouped_results"] = (
            grouped_results
        )

        context["laboratory"] = laboratory

        context["laboratory_display"] = (
            dict(
                LaboratorySection.choices
            ).get(
                laboratory,
                laboratory,
            )
        )

        context["laboratory_sections"] = (
            dict(
                LaboratorySection.choices
            )
        )

        return context


class SampleReportPDFView(RoleRequiredMixin, View):
    allowed_roles = (UserRole.VET_DOCTOR, UserRole.MANAGER)
    def get(self, request, *args, **kwargs):
        sample = get_object_or_404(
            Sample.objects.select_related(
                "farm", "farm__customer", "house", "report"
            ),
            pk=kwargs["pk"],
        )
        return pdf_response(sample, exporting_user=request.user)


class SampleReportDOCXView(RoleRequiredMixin, View):
    allowed_roles = (UserRole.VET_DOCTOR, UserRole.MANAGER)
    def get(self, request, *args, **kwargs):
        sample = get_object_or_404(
            Sample.objects.select_related(
                "farm", "farm__customer", "house", "report"
            ),
            pk=kwargs["pk"],
        )
        return docx_response(sample, exporting_user=request.user)


class SampleReportDeliveryView(RoleRequiredMixin, View):
    allowed_roles = (UserRole.VET_DOCTOR, UserRole.MANAGER)

    def post(self, request, *args, **kwargs):
        sample = get_object_or_404(
            Sample.objects.select_related(
                "farm", "farm__customer", "house", "report"
            ),
            pk=kwargs["pk"],
        )
        channel = kwargs["channel"]
        data = build_report_data(sample, exporting_user=request.user)
        customer = sample.farm.customer if sample.farm_id else None
        subject = f"Laboratory result — {sample.case_code}"

        if channel == "email":
            if not customer or not customer.email:
                messages.error(request, "This customer does not have an email address.")
            else:
                email_ready, email_status = email_delivery_status()
                if not email_ready:
                    messages.error(request, email_status)
                    return redirect("sample_final_result", pk=sample.pk)
                email = EmailMessage(
                    subject=subject,
                    body=(
                        f"Dear {customer.name},\n\n"
                        "Please find your laboratory result attached.\n\n"
                        "Kaduna Poultry Disease Diagnostic Laboratory"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[customer.email],
                )
                pdf = pdf_response(sample, exporting_user=request.user)
                email.attach(
                    f"{sample.case_code}-report.pdf",
                    pdf.content,
                    "application/pdf",
                )
                try:
                    email.send(fail_silently=False)
                    messages.success(request, f"Result emailed to {customer.email}.")
                except Exception:
                    messages.error(request, "Email delivery failed. Check the email settings and try again.")
        elif channel == "whatsapp":
            if not customer or not customer.whatsapp:
                messages.error(request, "This customer does not have a WhatsApp number.")
            else:
                summary = [
                    "KADUNA POULTRY DISEASE DIAGNOSTIC LABORATORY",
                    f"Case No: {data['case_code']}",
                    f"Sample: {data['sample_type']}",
                ]
                if data["clinical_diagnosis"]:
                    summary.append(f"Clinical diagnosis: {data['clinical_diagnosis']}")
                if data["laboratory_diagnosis"]:
                    summary.append(f"Laboratory diagnosis: {data['laboratory_diagnosis']}")
                for assay in data["assay_results"]:
                    values = [
                        f"{label}: {value}" for label, value in assay["rows"]
                    ]
                    values.extend(
                        f"{name}: {interpretation}"
                        for name, interpretation in assay["table"]
                    )
                    summary.append(f"{assay['assay']}: " + "; ".join(values))
                if data["comments"]:
                    summary.append(f"Comments: {data['comments']}")
                sent, detail = send_whatsapp_text(
                    customer.whatsapp,
                    "\n".join(summary),
                )
                if sent:
                    messages.success(request, f"Result sent to {customer.whatsapp} via WhatsApp.")
                else:
                    messages.error(request, detail)
        else:
            messages.error(request, "Unsupported delivery method.")

        return redirect("sample_final_result", pk=sample.pk)


# ============================================================
# EDIT ASSAY RESULT
# ============================================================

# ============================================================
# EDIT ASSAY RESULT
# ============================================================

class AssayResultEditView(
    RoleRequiredMixin,
    UpdateView,
):

    allowed_roles = (UserRole.LAB_SCIENTIST, UserRole.MANAGER)

    model = AssayResult

    def dispatch(
        self,
        request,
        *args,
        **kwargs,
    ):

        self.assay_result = get_object_or_404(
            AssayResult.objects.select_related(
                "assay_order",
                "assay_order__sample",
                "assay_order__assay",
                "binary_result",
                "gram_result",
                "ast_result",
                "ndhi_result",
                "pcr_result",
                "tsi_result",
                "culture_result",
            ),
            pk=kwargs["pk"],
        )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    # =========================================================
    # FORM SELECTION
    # =========================================================

    def get_form_class(self):

        category = (
            self.assay_result
            .assay_order
            .assay
            .category
        )

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
                f"No edit form has been implemented for "
                f"assay category: {category}"
            )

        return form_class

    # =========================================================
    # FORM INSTANCE
    # =========================================================

    def get_form_kwargs(self):

        kwargs = super().get_form_kwargs()

        category = (
            self.assay_result
            .assay_order
            .assay
            .category
        )

        result_relations = {
            AssayCategory.BINARY: "binary_result",
            AssayCategory.GRAM: "gram_result",
            AssayCategory.TSI: "tsi_result",
            AssayCategory.CULTURE: "culture_result",
            AssayCategory.AST: "ast_result",
            AssayCategory.NDHI: "ndhi_result",
            AssayCategory.PCR: "pcr_result",
        }

        try:
            kwargs["instance"] = getattr(
                self.assay_result,
                result_relations[category],
            )
        except ObjectDoesNotExist as error:
            raise Http404("The assay result details are missing.") from error

        return kwargs

    # =========================================================
    # TEMPLATE
    # =========================================================

    def get_template_names(self):

        category = (
            self.assay_result
            .assay_order
            .assay
            .category
        )

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

    # =========================================================
    # CONTEXT
    # =========================================================

    def get_context_data(
        self,
        **kwargs,
    ):

        context = super().get_context_data(
            **kwargs
        )

        order = self.assay_result.assay_order

        context["order"] = order
        context["sample"] = order.sample
        context["assay"] = order.assay
        context["editing"] = True

        # -----------------------------------------------------
        # AST FORMSET
        # -----------------------------------------------------

        if (
            order.assay.category
            == AssayCategory.AST
        ):

            if self.request.POST:

                context["formset"] = (
                    ASTResultItemFormSet(
                        self.request.POST,
                        instance=(
                            self.assay_result.ast_result
                        ),
                        prefix="ast",
                    )
                )

            else:

                context["formset"] = (
                    ASTResultItemFormSet(
                        instance=(
                            self.assay_result.ast_result
                        ),
                        prefix="ast",
                    )
                )

        return context

    # =========================================================
    # FORM VALIDATION
    # =========================================================

    def post(
        self,
        request,
        *args,
        **kwargs,
    ):

        self.object = self.assay_result

        form = self.get_form()

        # -----------------------------------------------------
        # AST requires both form and formset
        # -----------------------------------------------------

        if (
            self.assay_result.assay_order.assay.category
            == AssayCategory.AST
        ):

            formset = ASTResultItemFormSet(
                request.POST,
                instance=(
                    self.assay_result.ast_result
                ),
                prefix="ast",
            )

            if (
                form.is_valid()
                and formset.is_valid()
            ):

                return self.form_valid(
                    form,
                    formset=formset,
                )

            return self.form_invalid(
                form,
                formset=formset,
            )

        # -----------------------------------------------------
        # Other result categories
        # -----------------------------------------------------

        if form.is_valid():

            return self.form_valid(form)

        return self.form_invalid(form)

    # =========================================================
    # SAVE
    # =========================================================

    @transaction.atomic
    def form_valid(
        self,
        form,
        *,
        formset=None,
    ):

        # -----------------------------------------------------
        # Save category-specific result
        # -----------------------------------------------------

        form.save(
            commit=True,
            assay_result=self.assay_result,
        )

        # -----------------------------------------------------
        # Save AST items
        # -----------------------------------------------------

        if formset is not None:

            formset.instance = (
                self.assay_result.ast_result
            )

            formset.save()

        # -----------------------------------------------------
        # Update remarks
        # -----------------------------------------------------

        remarks = form.cleaned_data.get(
            "remarks"
        )

        if remarks is not None:

            self.assay_result.remarks = remarks

            self.assay_result.save(
                update_fields=[
                    "remarks"
                ]
            )

        # -----------------------------------------------------
        # Update sample status
        # -----------------------------------------------------

        self.assay_result.assay_order.sample.update_status_from_assays()

        # -----------------------------------------------------
        # Success message
        # -----------------------------------------------------

        messages.success(
            self.request,
            "Laboratory result updated successfully.",
        )

        # -----------------------------------------------------
        # Return to final sample result
        # -----------------------------------------------------

        return redirect(
            "sample_final_result",
            pk=(
                self.assay_result
                .assay_order
                .sample
                .pk
            ),
        )

    # =========================================================
    # INVALID FORM
    # =========================================================

    def form_invalid(
        self,
        form,
        *,
        formset=None,
    ):

        context = self.get_context_data(
            form=form
        )

        if formset is not None:

            context["formset"] = formset

        return self.render_to_response(
            context
        )

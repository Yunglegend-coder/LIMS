from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import UserNotification, UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "whatsapp", "signature")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email", "whatsapp")


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "recipient", "sample", "created_at", "read_at")
    list_filter = ("created_at", "read_at")
    search_fields = ("title", "message", "recipient__username", "sample__case_code")


User = get_user_model()
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    inlines = (UserProfileInline,)

    def save_related(self, request, form, formsets, change):
        profile_formsets = [
            formset for formset in formsets
            if formset.model is UserProfile
        ]
        other_formsets = [
            formset for formset in formsets
            if formset.model is not UserProfile
        ]

        if change or not profile_formsets:
            return super().save_related(
                request,
                form,
                formsets,
                change,
            )

        # The post_save signal has already created the default profile when
        # the new auth.User was saved. Apply the add-page inline values to
        # that row instead of having the inline formset insert a duplicate.
        super().save_related(
            request,
            form,
            other_formsets,
            change,
        )
        profile = UserProfile.objects.get(user=form.instance)
        for profile_formset in profile_formsets:
            # Admin's change-message builder inspects these after save_related.
            # Since the profile row was created by the user signal, it is
            # edited in place and must not be reported as a newly inserted row.
            profile_formset.new_objects = []
            profile_formset.changed_objects = []
            profile_formset.deleted_objects = []
            for profile_form in profile_formset.forms:
                if not profile_form.has_changed():
                    continue
                cleaned_data = profile_form.cleaned_data
                if cleaned_data.get("DELETE"):
                    continue
                profile.role = cleaned_data.get("role", profile.role)
                profile.whatsapp = cleaned_data.get("whatsapp", profile.whatsapp)
                profile.save(update_fields=["role", "whatsapp"])

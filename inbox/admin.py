from django.contrib import admin

from .models import ClinicMembership


@admin.register(ClinicMembership)
class ClinicMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "clinic")
    list_filter = ("clinic",)
    search_fields = ("user__username", "clinic__name")
    autocomplete_fields = ("clinic",)

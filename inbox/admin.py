from django.contrib import admin

from .models import BusinessMembership


@admin.register(BusinessMembership)
class BusinessMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "business")
    list_filter = ("business",)
    search_fields = ("user__username", "business__name")
    autocomplete_fields = ("business",)

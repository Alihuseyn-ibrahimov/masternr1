from django.contrib import admin

from .models import Clinic, Doctor, FAQItem, Service


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1


class DoctorInline(admin.TabularInline):
    model = Doctor
    extra = 1


class FAQItemInline(admin.TabularInline):
    model = FAQItem
    extra = 1


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "phone", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ServiceInline, DoctorInline, FAQItemInline]

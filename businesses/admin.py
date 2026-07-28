from django.contrib import admin

from .models import Business, StaffMember, FAQItem, Service


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1


class StaffMemberInline(admin.TabularInline):
    model = StaffMember
    extra = 1


class FAQItemInline(admin.TabularInline):
    model = FAQItem
    extra = 1


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "phone", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ServiceInline, StaffMemberInline, FAQItemInline]

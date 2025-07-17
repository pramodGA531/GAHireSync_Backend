from django.contrib.admin import AdminSite, ModelAdmin, TabularInline
from .models import Plan, Feature, PlanFeature, OrganizationPlan, PlanHistory, Organization


# ✅ 1. Define your custom admin site
class PricingAdminSite(AdminSite):
    site_header = "Pricing Module"
    site_title = "Pricing Admin"
    index_title = "Manage Pricing"


pricing_admin_site = PricingAdminSite(name='pricing_admin')


# ✅ 2. Inline relationships
class PlanFeatureInline(TabularInline):
    model = PlanFeature
    extra = 1
    autocomplete_fields = ['feature']
    verbose_name = "Feature with Limit"
    verbose_name_plural = "Features with Limits"


# ✅ 3. Admin classes for each model
class PlanAdmin(ModelAdmin):
    list_display = ['name', 'price', 'duration_days']
    search_fields = ['name', 'price']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [PlanFeatureInline]


class FeatureAdmin(ModelAdmin):
    list_display = ['code', 'name']
    search_fields = ['code', 'name']

class OrganizationAdmin(ModelAdmin):
    list_display = ('name', 'manager')
    search_fields = ('name',)
    list_filter = ('manager',)
    ordering = ('name',)


class OrganizationPlanAdmin(ModelAdmin):
    list_display = ['organization', 'plan', 'start_date', 'expiry_date', 'payment_status', 'is_active']
    list_filter = ['payment_status', 'is_active', 'plan']
    search_fields = ['organization__name', 'plan__name', 'payment_reference']
    readonly_fields = ['start_date']
    autocomplete_fields = ['organization', 'plan']


class PlanHistoryAdmin(ModelAdmin):
    list_display = ['organization', 'plan', 'subscribed_at', 'expired_at', 'amount_paid']
    list_filter = ['plan']
    search_fields = ['organization__name', 'plan__name', 'payment_reference']
    readonly_fields = ['subscribed_at', 'expired_at', 'amount_paid']


# ✅ 4. Register them with the **custom admin site**
pricing_admin_site.register(Organization, OrganizationAdmin)
pricing_admin_site.register(Plan, PlanAdmin)
pricing_admin_site.register(Feature, FeatureAdmin)
pricing_admin_site.register(PlanFeature)  # No custom admin needed
pricing_admin_site.register(OrganizationPlan, OrganizationPlanAdmin)
pricing_admin_site.register(PlanHistory, PlanHistoryAdmin)

from django.contrib import admin
from .models import Tenant, TenantMembership, IngestionRun, RawRecord, NormalizedRecord, AuditLog

admin.site.register(Tenant)
admin.site.register(TenantMembership)
admin.site.register(IngestionRun)
admin.site.register(RawRecord)
admin.site.register(NormalizedRecord)
admin.site.register(AuditLog)

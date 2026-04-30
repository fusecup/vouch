from django.contrib import admin

from .models import (
    ApprovalAttestation,
    ApprovalSession,
    Counterparty,
    LedgerEntry,
    PaymentIntent,
    PolicyConfigEvent,
    Receipt,
)

admin.site.register(Counterparty)
admin.site.register(PaymentIntent)
admin.site.register(LedgerEntry)
admin.site.register(Receipt)
admin.site.register(ApprovalSession)
admin.site.register(ApprovalAttestation)
admin.site.register(PolicyConfigEvent)

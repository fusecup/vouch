from django.urls import path

from activity.views import (
    ActivityDashboardView,
    create_payment_intent_api,
    payment_reverse_view,
    specter_vendor_detail_api,
    tier1_queue_api,
    tier1_swipe_action_api,
    tier2_attestation_api,
    tier2_session_api,
    transaction_detail_partial,
)

app_name = "activity"

urlpatterns = [
    path("", ActivityDashboardView.as_view(), name="dashboard"),
    path("transactions/detail/", transaction_detail_partial, name="transaction_detail"),
    path("transactions/<str:transaction_id>/", transaction_detail_partial, name="transaction_detail_legacy"),
    path("payments/<int:payment_id>/reverse/", payment_reverse_view, name="payment_reverse"),
    path("api/payments/create/", create_payment_intent_api, name="create_payment"),
    path("api/tier1/queue/", tier1_queue_api, name="tier1_queue"),
    path("api/tier1/swipe/", tier1_swipe_action_api, name="tier1_swipe"),
    path("api/tier2/session/", tier2_session_api, name="tier2_session"),
    path("api/tier2/attestation/", tier2_attestation_api, name="tier2_attestation"),
    path("api/vendors/specter/", specter_vendor_detail_api, name="specter_vendor"),
]

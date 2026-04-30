from django.urls import path

from activity.api import api as activity_api
from activity.views import (
    ActivityCounterpartiesView,
    ActivityDashboardView,
    ActivityOverviewView,
    ActivityProfileView,
    ActivityReceiptsReversalsView,
    ActivityRulesThresholdsView,
    ActivitySimulationSettingsView,
    ActivitySimulatorView,
    ActivityTier1ReviewView,
    ActivityTier2SessionsView,
    ActivityTransactionsView,
    payment_reverse_view,
    transaction_detail_partial,
)

app_name = "activity"

urlpatterns = [
    path("", ActivityDashboardView.as_view(), name="dashboard"),
    path("overview/", ActivityOverviewView.as_view(), name="overview"),
    path("transactions/", ActivityTransactionsView.as_view(), name="transactions"),
    path("tier1-review/", ActivityTier1ReviewView.as_view(), name="tier1_review"),
    path("tier2-sessions/", ActivityTier2SessionsView.as_view(), name="tier2_sessions"),
    path("counterparties/", ActivityCounterpartiesView.as_view(), name="counterparties"),
    path("rules-thresholds/", ActivityRulesThresholdsView.as_view(), name="rules_thresholds"),
    path("receipts-reversals/", ActivityReceiptsReversalsView.as_view(), name="receipts_reversals"),
    path("simulator/", ActivitySimulatorView.as_view(), name="simulator"),
    path("simulation-settings/", ActivitySimulationSettingsView.as_view(), name="simulation_settings"),
    path("profile/", ActivityProfileView.as_view(), name="profile"),
    path("transactions/detail/", transaction_detail_partial, name="transaction_detail"),
    path("transactions/<str:transaction_id>/", transaction_detail_partial, name="transaction_detail_legacy"),
    path("payments/<int:payment_id>/reverse/", payment_reverse_view, name="payment_reverse"),
    path("api/", activity_api.urls),
]

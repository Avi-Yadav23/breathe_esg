from django.urls import path
from . import views

urlpatterns = [
    path("auth/login/", views.LoginView.as_view()),
    path("auth/logout/", views.LogoutView.as_view()),
    path("auth/me/", views.MeView.as_view()),
    path("ingest/upload/", views.UploadView.as_view()),
    path("ingest/runs/", views.IngestionRunListView.as_view()),
    path("ingest/runs/<uuid:pk>/", views.IngestionRunDetailView.as_view()),
    path("records/", views.NormalizedRecordListView.as_view()),
    path("records/bulk-approve/", views.BulkApproveView.as_view()),
    path("records/bulk-reject/", views.BulkRejectView.as_view()),
    path("records/<uuid:pk>/", views.NormalizedRecordDetailView.as_view()),
    path("records/<uuid:pk>/approve/", views.RecordApproveView.as_view()),
    path("records/<uuid:pk>/reject/", views.RecordRejectView.as_view()),
    path("records/<uuid:pk>/flag/", views.RecordFlagView.as_view()),
    path("records/<uuid:pk>/audit/", views.RecordAuditView.as_view()),
    path("dashboard/summary/", views.DashboardSummaryView.as_view()),
]

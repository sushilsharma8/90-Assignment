from django.urls import path
from .views import google_auth, google_callback, upload_to_drive, list_drive_files

urlpatterns = [
    # Google OAuth
    path('auth/google/', google_auth, name='google-auth'),
    path('auth/callback/', google_callback, name='google-callback'),

    # Google Drive Integration
    path('drive/upload/', upload_to_drive, name='drive-upload'),
    path('drive/files/', list_drive_files, name='drive-files'),
]

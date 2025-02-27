import os
import json
from django.http import JsonResponse
from io import BytesIO
from googleapiclient.http import MediaIoBaseUpload
from django.views.decorators.csrf import csrf_exempt
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from django.conf import settings



# Load environment variables
GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
REDIRECT_URI = "http://127.0.0.1:8000/api/auth/callback/"

# Path to client secret file
CLIENT_SECRET_FILE = os.path.join(settings.BASE_DIR, "client_secret.json")


# 1️⃣ Google OAuth Authentication Flow
def google_auth(request):
    """
    Generates the Google OAuth 2.0 authentication URL.
    """
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
            ],
            redirect_uri=REDIRECT_URI,
        )
        auth_url, _ = flow.authorization_url(prompt="consent")
        return JsonResponse({"auth_url": auth_url})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def google_callback(request):
    """
    Handles the callback from Google OAuth and exchanges the code for an access token.
    """
    try:
        code = request.GET.get("code")
        if not code:
            return JsonResponse({"error": "Authorization code not provided"}, status=400)

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
            ],
            redirect_uri=REDIRECT_URI,
        )
        flow.fetch_token(code=code)

        credentials = flow.credentials
        return JsonResponse({
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expires_in": credentials.expiry.timestamp()
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# 2️⃣ Google Drive Integration
@csrf_exempt
def upload_to_drive(request):
    """
    Uploads a file to Google Drive.
    """
    try:
        if request.method != "POST":
            return JsonResponse({"error": "Invalid request method"}, status=405)

        access_token = request.headers.get("Authorization")
        if not access_token:
            return JsonResponse({"error": "Missing access token"}, status=401)

        file_obj = request.FILES.get("file")
        if not file_obj:
            return JsonResponse({"error": "No file provided"}, status=400)

        credentials = Credentials(access_token)
        drive_service = build("drive", "v3", credentials=credentials)

        # Convert InMemoryUploadedFile to a byte stream
        file_stream = BytesIO(file_obj.read())
        media = MediaIoBaseUpload(file_stream, mimetype=file_obj.content_type, resumable=True)

        file_metadata = {"name": file_obj.name}
        uploaded_file = drive_service.files().create(
            body=file_metadata, media_body=media, fields="id"
        ).execute()

        return JsonResponse({"file_id": uploaded_file.get("id")})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def list_drive_files(request):
    """
    Lists files in the user's Google Drive.
    """
    try:
        access_token = request.headers.get("Authorization")
        if not access_token:
            return JsonResponse({"error": "Missing access token"}, status=401)

        credentials = Credentials(access_token)
        drive_service = build("drive", "v3", credentials=credentials)

        results = drive_service.files().list().execute()
        files = results.get("files", [])

        return JsonResponse({"files": files})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

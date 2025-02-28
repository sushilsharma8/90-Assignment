from django.contrib.auth.models import User
from django.utils.timezone import make_aware
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from datetime import datetime, timedelta
import os
import requests
import base64
import json
from io import BytesIO
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
from core.models import UserToken
from Backend.logger import log
from logging import INFO, ERROR
import art


# OAuth Configuration
GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET
if settings.DEBUG:
    REDIRECT_URI = "http://127.0.0.1:8000/api/auth/callback/"
else:
    REDIRECT_URI = "https://nine0-assignment.onrender.com/api/auth/callback/"
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly"
]

# Decode client_secret.json from Base64 if using environment variable
base64_secret = os.getenv("GOOGLE_CLIENT_SECRET_JSON")
if base64_secret:
    try:
        decoded_secret = base64.b64decode(base64_secret).decode("utf-8")
        with open(os.path.join(settings.BASE_DIR, "client_secret.json"), "w") as f:
            f.write(decoded_secret)
    except Exception as e:
        log(level=ERROR, function="decode_client_secret", message=f"Failed to decode client_secret.json: {str(e)}")

# Helper Functions
def get_user_tokens(user_email):
    try:
        user = User.objects.get(username=user_email)
        return UserToken.objects.get(user=user)
    except (User.DoesNotExist, UserToken.DoesNotExist):
        return None

def build_credentials(token_data):
    return Credentials(
        token=token_data.access_token,
        refresh_token=token_data.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=SCOPES
    )

# Views
@csrf_exempt
def google_auth(request):
    """Initiate Google OAuth flow"""
    try:
        log(level=INFO, function="google_auth", message="OAuth flow initiated.")
        flow = Flow.from_client_secrets_file(
            os.path.join(settings.BASE_DIR, "client_secret.json"),
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        auth_url, _ = flow.authorization_url(
            prompt="consent",
            access_type="offline",
            include_granted_scopes="true"
        )
        return JsonResponse({"auth_url": auth_url})
    except Exception as e:
        log(level=ERROR, function="google_auth", message=str(e))
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def google_callback(request):
    """Handle OAuth callback"""
    try:
        code = request.GET.get("code")
        if not code:
            return JsonResponse({"error": "Missing authorization code"}, status=400)

        flow = Flow.from_client_secrets_file(
            os.path.join(settings.BASE_DIR, "client_secret.json"),
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        flow.fetch_token(code=code)

        credentials = flow.credentials
        user_info = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {credentials.token}"}
        ).json()

        user, _ = User.objects.get_or_create(
            username=user_info["email"],
            defaults={"email": user_info["email"]}
        )

        UserToken.objects.update_or_create(
            user=user,
            defaults={
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "expires_at": make_aware(credentials.expiry)
            }
        )

        log(level=INFO, function="google_callback", message=f"User authenticated: {user.email}")
        return JsonResponse({
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expires_in": credentials.expiry.timestamp(),
            "user": user_info
        })
    except Exception as e:
        log(level=ERROR, function="google_callback", message=str(e))
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def upload_to_drive(request):
    """Upload file to Google Drive"""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        user_email = request.headers.get("User-Email")
        token_data = get_user_tokens(user_email)
        if not token_data:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        credentials = build_credentials(token_data)
        
        # Auto-refresh token
        if credentials.expired:
            credentials.refresh(Request())
            token_data.access_token = credentials.token
            token_data.expires_at = make_aware(credentials.expiry)
            token_data.save()
            log(level=INFO, function="upload_to_drive", message="Access token refreshed.")

        drive_service = build("drive", "v3", credentials=credentials)
        
        file_obj = request.FILES["file"]
        media = MediaIoBaseUpload(
            BytesIO(file_obj.read()),
            mimetype=file_obj.content_type
        )
        
        file_metadata = {"name": file_obj.name}
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()

        log(level=INFO, function="upload_to_drive", message=f"File uploaded successfully: {uploaded_file['id']}")
        return JsonResponse({"file_id": uploaded_file["id"]})

    except HttpError as e:
        log(level=ERROR, function="upload_to_drive", message=str(e))
        return JsonResponse({"error": f"Google API Error: {str(e)}"}, status=500)
    except Exception as e:
        log(level=ERROR, function="upload_to_drive", message=str(e))
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def list_drive_files(request):
    """List files in Google Drive"""
    try:
        user_email = request.headers.get("User-Email")
        token_data = get_user_tokens(user_email)
        if not token_data:
            return JsonResponse({"error": "Unauthorized"}, status=401)

        credentials = build_credentials(token_data)
        
        # Refresh if expired
        if credentials.expired:
            credentials.refresh(Request())
            token_data.access_token = credentials.token
            token_data.expires_at = make_aware(credentials.expiry)
            token_data.save()
            log(level=INFO, function="list_drive_files", message="Access token refreshed.")

        drive_service = build("drive", "v3", credentials=credentials)

        response = drive_service.files().list(
            pageSize=100,
            fields="files(id, name, mimeType, createdTime)"
        ).execute()
            
        log(level=INFO, function="list_drive_files", message=f"Retrieved {len(response.get('files', []))} files.")
        return JsonResponse({"files": response.get("files", [])})

    except HttpError as e:
        log(level=ERROR, function="list_drive_files", message=str(e))
        return JsonResponse({"error": f"Google API Error: {e._get_reason()}"}, status=e.status_code)
    except Exception as e:
        log(level=ERROR, function="list_drive_files", message=str(e))
        return JsonResponse({"error": str(e)}, status=500)

def health_check(request):
    return JsonResponse({"status": "ok"})

def cool_terminal(request):
    ascii_banner = art.text2art("I left this for the frontend dev!", font="block")
    message = "My work here is done. Time for the frontend dev to take over! 😎🎨"
    return HttpResponse(f"<pre>{ascii_banner}</pre><p>{message}</p>", content_type="text/html")


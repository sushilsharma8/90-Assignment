import os
import json
import requests
from io import BytesIO
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

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
                "https://www.googleapis.com/auth/drive.file",
            ],
            redirect_uri=REDIRECT_URI,
        )
        # 🔹 Ensure refresh_token is returned
        auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
        return JsonResponse({"auth_url": auth_url})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


from datetime import datetime, timedelta
from django.utils.timezone import make_aware
from .models import UserToken
from django.contrib.auth.models import User

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
                "https://www.googleapis.com/auth/drive.file",
            ],
            redirect_uri=REDIRECT_URI,
        )
        flow.fetch_token(code=code)

        credentials = flow.credentials
        access_token = credentials.token
        refresh_token = credentials.refresh_token or request.session.get("refresh_token")
        expires_in = credentials.expiry.timestamp()

        # Fetch user info from Google
        user_info = requests.get(
            "https://www.googleapis.com/oauth2/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        ).json()

        # Store user in Django User model
        user, _ = User.objects.get_or_create(username=user_info["email"], defaults={"email": user_info["email"]})

        # Convert expires_in timestamp to a Django DateTimeField
        expires_at = make_aware(datetime.utcfromtimestamp(expires_in))

        # Save tokens in the database
        UserToken.objects.update_or_create(
            user=user,
            defaults={"access_token": access_token, "refresh_token": refresh_token, "expires_at": expires_at}
        )

        return JsonResponse({
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "user": user_info
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

        user_email = request.headers.get("User-Email")
        if not user_email:
            return JsonResponse({"error": "Missing user email"}, status=401)

        try:
            user = User.objects.get(username=user_email)
            token_data = UserToken.objects.get(user=user)
        except (User.DoesNotExist, UserToken.DoesNotExist):
            return JsonResponse({"error": "User not found or not authenticated"}, status=401)

        # Create credentials object
        credentials = Credentials(
            token=token_data.access_token,
            refresh_token=token_data.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET
        )

        # Refresh token if expired
        if not credentials.valid:
            try:
                credentials.refresh(requests.Request())

                # Update the new access token in the database
                token_data.access_token = credentials.token
                token_data.expires_at = make_aware(datetime.utcnow() + timedelta(seconds=3600))
                token_data.save()

            except Exception as e:
                return JsonResponse({"error": f"Failed to refresh token: {str(e)}"}, status=401)

        drive_service = build("drive", "v3", credentials=credentials)

        file_obj = request.FILES.get("file")
        if not file_obj:
            return JsonResponse({"error": "No file provided"}, status=400)

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
        refresh_token = request.headers.get("Refresh-Token") or request.session.get("refresh_token")

        if not access_token:
            return JsonResponse({"error": "Missing access token"}, status=401)

        if not refresh_token:
            return JsonResponse({"error": "Missing refresh token. Re-authentication required."}, status=401)

        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET
        )

        # Refresh token if access token is expired
        if not credentials.valid:
            try:
                credentials.refresh(requests.Request())
            except Exception as e:
                return JsonResponse({"error": f"Failed to refresh token: {str(e)}"}, status=401)

        drive_service = build("drive", "v3", credentials=credentials)

        results = drive_service.files().list().execute()
        files = results.get("files", [])

        return JsonResponse({"files": files})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# 3️⃣ Token Refresh Endpoint
@csrf_exempt
def refresh_access_token(request):
    """
    Refreshes the access token using the refresh token.
    """
    try:
        # 🔹 Fetch refresh_token from headers or session
        refresh_token = request.headers.get("Refresh-Token") or request.session.get("refresh_token")

        if not refresh_token:
            return JsonResponse({"error": "Missing refresh token. Please re-authenticate."}, status=401)

        # 🔹 Send request to Google OAuth endpoint
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
        )

        # 🔹 Check if Google responded successfully
        if response.status_code != 200:
            return JsonResponse({
                "error": "Failed to refresh access token",
                "details": response.json()
            }, status=400)

        new_tokens = response.json()

        # 🔹 Update session with new tokens
        request.session["refresh_token"] = refresh_token

        return JsonResponse(new_tokens)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

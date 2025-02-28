# Google Drive API Integration with Django

This project implements Google OAuth authentication and Google Drive file management (uploading and listing) using Django.

## Features

- 🔐 Google OAuth 2.0 authentication
- 📂 Upload files to Google Drive
- 📜 List uploaded files from Google Drive
- 🔄 Token refresh mechanism
- 📝 Logging for debugging
- 🚀 Deployment ready for **Render, Railway, or any cloud platform**

## Tech Stack

- **Backend**: Django, Django Rest Framework, Channels
- **Google APIs**: OAuth 2.0, Google Drive API
- **Database**: PostgreSQL (via NeonDB)
- **Deployment**: Render (Live at [nine0-assignment.onrender.com](https://nine0-assignment.onrender.com))

## Setup Instructions

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/sushilsharma8/google-drive-django.git
cd google-drive-django
```

### 2️⃣ Create a Virtual Environment

```bash
python -m venv env
source env/bin/activate  # On Windows use `env\Scripts\activate`
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Set Up Environment Variables

Create a `.env` file in the root directory and add:

```
GOOGLE_CLIENT_ID=<your_google_client_id>
GOOGLE_CLIENT_SECRET=<your_google_client_secret>
DATABASE_URL=<your_postgresql_url>
DEBUG=True
```

#### Base64 Encode `client_secret.json`

```bash
cat client_secret.json | base64
```

Copy the output and set it in `.env`:

```
GOOGLE_CLIENT_SECRET_JSON=<your_base64_encoded_json>
```

### 5️⃣ Apply Migrations

```bash
python manage.py migrate
```

### 6️⃣ Run the Server

```bash
daphne -b 0.0.0.0 -p 8000 Backend.asgi:application
```

## API Endpoints

### 🔐 Authentication

- `GET /api/auth/google/` - Initiates Google OAuth
- `GET /api/auth/callback/` - Handles OAuth callback

### 📂 Google Drive

- `POST /api/drive/upload/` - Uploads a file to Google Drive (Header: `User-Email` required)
- `GET /api/drive/files/` - Lists user’s uploaded files (Header: `User-Email` required)

### 🔄 Token Management

- `POST /api/auth/refresh/` - Refreshes access token

### ⚡ Health Check & Root Page

- `GET /` - Shows ASCII welcome message
- `GET /health/` - Health check endpoint

## 🚀 Deployment on Render

1. **Push to GitHub**
2. **Create a new Web Service on Render**
3. **Set Environment Variables** (Use `.env` values)
4. **Use this start command**:
   ```bash
   cd Backend && python manage.py migrate && daphne -b 0.0.0.0 -p 8000 Backend.asgi:application
   ```

Project is live at [nine0-assignment.onrender.com](https://nine0-assignment.onrender.com) 🎉

## 📜 Logging

Custom logging has been implemented for tracking authentication, uploads, and errors.

## 🔥 Author

**Sushil Sharma**\
🚀 [GitHub](https://github.com/sushilsharma8) | 💼 [LinkedIn](https://linkedin.com/in/itzsushilsharma)

---

✨ **Contributions & Issues**: PRs are welcome! Feel free to raise issues if needed.


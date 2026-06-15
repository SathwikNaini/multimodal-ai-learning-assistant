# Deployment Guide

This document provides step-by-step instructions to deploy the **AI-Based Intelligent Notes Summarizer & Learning Assistant** to cloud environments.

---

## 1. Environment Variables Checklist

### Backend Environment Variables (`.env`)
Create these variables on your server host (e.g. Render, Heroku):

* `GEMINI_API_KEY`: Your Google Gemini API Key. Get it from [Google AI Studio](https://aistudio.google.com/app/apikeys).
* `FLASK_ENV`: Set to `production` in production hosting.
* `FLASK_DEBUG`: Set to `0` in production to disable stack traces in output.

### Frontend Environment Variables (`.env.production`)
Define this variable on your static build host (e.g. Vercel, Netlify):

* `VITE_API_URL`: The full URL of your deployed backend application (e.g., `https://my-backend-app.onrender.com`). **Do not include a trailing slash.**

---

## 2. Backend Deployment (e.g. Render)

1. **Create Web Service**: Link your GitHub repository to [Render](https://render.com) and create a new **Web Service**.
2. **Build Configuration**:
   * **Runtime**: `Python`
   * **Build Command**: `pip install -r backend/requirements.txt`
   * **Start Command**: `gunicorn --bind 0.0.0.0:$PORT backend.app:app`
     *(Make sure to add `gunicorn` to your `requirements.txt` if using standard Linux hosting).*
3. **Environment Variables**: Add your `GEMINI_API_KEY`, `FLASK_ENV=production`, and `FLASK_DEBUG=0` under the service environment variables tab.

---

## 3. Frontend Deployment (e.g. Vercel)

1. **Import Project**: Connect your GitHub repository to [Vercel](https://vercel.com).
2. **Configure Settings**:
   * **Root Directory**: Select `frontend`.
   * **Framework Preset**: `Vite`.
   * **Build Command**: `npm run build`
   * **Output Directory**: `dist`
3. **Environment Variables**: Add `VITE_API_URL` pointing to your Render backend URL.
4. **Deploy**: Click **Deploy**.

---

## 4. Production Security & CORS

* **CORS Settings**: In [backend/config/settings.py](file:///E:/projects/Capston%20AI%20Summarizer/backend/config/settings.py), update `CORS_ORIGINS` to contain your deployed frontend production URL (e.g. `https://my-notes-summarizer.vercel.app`) to block external unauthorized requests.
* **Max Payload Enforcer**: Ensure your hosting proxy (e.g. Nginx or Cloudflare) aligns with the Flask `MAX_CONTENT_LENGTH` settings (50MB) to protect the server from memory starvation or large payload exploits.

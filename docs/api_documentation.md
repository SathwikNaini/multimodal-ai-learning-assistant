# API Documentation

This document describes the API contract, routes, parameters, and payloads for the backend of the **AI-Based Intelligent Notes Summarizer & Learning Assistant**.

---

## Base URL
All API requests in local development are routed to:
`http://localhost:5000`

---

## Endpoints

### 1. Health Check
Checks the status of the server.

* **Route**: `/health`
* **Method**: `GET`
* **Headers**: `None`
* **Response Code**: `200 OK`

#### Response Body
```json
{
  "success": true,
  "data": {
    "status": "Backend running"
  },
  "error": null
}
```

---

### 2. Summarize Content
Extracts content from a file, image, text, or YouTube video and generates a summary and learning gaps.

* **Route**: `/api/summarize`
* **Method**: `POST`
* **Content-Type**: `multipart/form-data`
* **Request Body**:
  Must provide exactly **one** of the following form fields:

  | Parameter | Type | Required | Description |
  | :--- | :--- | :--- | :--- |
  | `text` | String | No | Raw study notes or article text to summarize (minimum 10 characters). |
  | `youtube_url` | String | No | A valid YouTube video watch link or short link. |
  | `file` | Binary | No | A document (`.pdf`, `.pptx`, `.txt`) or image (`.png`, `.jpg`, `.jpeg`, `.webp`). |

#### Response Codes
* `200 OK`: Request succeeded.
* `400 Bad Request`: Missing inputs, invalid file format, or parsing errors.
* `413 Payload Too Large`: Uploaded file exceeds the 50MB limit.
* `500 Internal Server Error`: Unhandled backend exception.
* `502 Bad Gateway`: Empty or malformed response from the Gemini API.

#### Response Body (200 OK)
```json
{
  "success": true,
  "data": {
    "summary": [
      "Point 1 summarizing the main topic.",
      "Point 2 explaining secondary details.",
      "Point 3 detailing conclusions."
    ],
    "cognitive_gaps": [
      {
        "concept": "Topic Name",
        "reason": "Explanation of why this topic is prerequisite knowledge",
        "youtube_query": "Best query text to search for learning this topic",
        "video": {
          "id": "dQw4w9WgXcQ",
          "title": "Introduction to Topic",
          "link": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
          "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
          "channel": "Educational Channel Name",
          "duration": "10:15"
        }
      }
    ]
  },
  "error": null
}
```

#### Response Body (Error - e.g., 400 Bad Request)
```json
{
  "success": false,
  "data": null,
  "error": "Unsupported file type. Allowed: .jpeg, .jpg, .pdf, .png, .pptx, .txt, .webp"
}
```

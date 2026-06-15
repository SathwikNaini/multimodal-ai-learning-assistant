# AI-Based Intelligent Notes Summarizer & Learning Assistant

An advanced, production-grade web application that leverages generative AI to transform complex academic materials—PDFs, PowerPoint slides, Word documents, images, and YouTube lectures—into structured study summaries, and automatically suggests resources to cover detected learning gaps.

---

## 🚀 Key Features

*   **Multimodal Material Ingestion**:
    *   **PDF Analysis**: Reads academic papers and extracts structured lecture takeaways.
    *   **PPT Analysis**: Parses lecture slides to extract text slide-by-slide.
    *   **Image OCR Analysis**: Leverages Google Gemini to extract text and details directly from whiteboard photos, charts, and diagrams.
    *   **YouTube Video Summarization**: Extracts subtitles and transcripts from YouTube video URLs in multiple regional languages (English, Hindi, Telugu).
*   **AI-Powered Learning Assistance**:
    *   **Detailed Synthesized Summaries**: Translates voluminous content into high-density key takeaways.
    *   **Remediation & Recommendation Engine**: Automatically identifies prerequisite concepts omitted from your source material (cognitive gaps) and performs semantic searches to suggest relevant YouTube tutorial videos.
    *   **Structured PDF Report Export**: Export summaries and recommended video paths into clean, formatted PDF documents.
*   **Modern Design & Theme Systems**: Responsive client dashboard built with React, Tailwind CSS, and a comprehensive dark/light layout.

---

## 🏗️ System Architecture

The application is structured into three primary architectural layers:

1.  **Frontend (React & TypeScript)**: A modern client application built with Vite and Tailwind CSS. Implements a tabbed interface, handles file uploading, manages application states (loading, error, empty), and renders summaries and embedded video recommendation players.
2.  **Backend (Flask)**: A Python microservices layer that validates payloads, manages file uploads (up to 50MB), extracts text from various formats, and orchestrates calls to the AI model.
3.  **AI Layer (Google Gemini API)**: Powered by the `gemini-2.5-flash` model, generating highly structured study breakdowns in JSON formatting.

For a deep dive into data ingestion pipelines, diagrams, and AI prompts, read the [Architecture Documentation](docs/architecture.md).

---

## 🛠️ Installation Guide

### Prerequisites
*   [Node.js](https://nodejs.org/) (v18+)
*   [Python](https://www.python.org/) (v3.9+)
*   [Google Gemini API Key](https://aistudio.google.com/app/apikeys)

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/ai-notes-summarizer.git
cd ai-notes-summarizer
```

### Step 2: Set Up the Backend
1.  Navigate to the `backend` folder:
    ```bash
    cd backend
    ```
2.  Create a virtual environment and activate it:
    ```bash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Configure environment variables (see below).
5.  Start the server:
    ```bash
    python app.py
    ```

### Step 3: Set Up the Frontend
1.  Open a new terminal and navigate to the `frontend` folder:
    ```bash
    cd frontend
    ```
2.  Install packages:
    ```bash
    npm install
    ```
3.  Configure environment variables (see below).
4.  Start the development server:
    ```bash
    npm run dev
    ```
5.  Visit `http://localhost:5173` in your browser.

---

## 🔒 Environment Variables

### Backend Configuration (`backend/.env`)
Create a `.env` file in the `backend/` directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
FLASK_ENV=development
FLASK_DEBUG=1
```

### Frontend Configuration (`.env.local`)
Create a `.env.local` file in the root directory:
```env
VITE_API_URL=http://localhost:5000
```

---

## 📂 Folder Structure

```
project/
├── backend/                  # Flask application
│   ├── config/               # App configuration files
│   ├── routes/               # Modular controller blueprints
│   ├── services/             # Ingestion & AI integrations
│   ├── temp/                 # System temp directories (gitignored)
│   ├── uploads/              # Local uploads directories (gitignored)
│   ├── utils/                # Helper models & exception definitions
│   └── requirements.txt      # Python dependencies
├── docs/                     # Technical specifications & guides
├── frontend/                 # Vite-React client
│   ├── src/
│   │   ├── components/       # UI dashboard elements
│   │   └── api.ts            # Typed backend query client
│   └── package.json          # Node dependencies
├── .gitignore                # Global git exclusion rules
├── LICENSE                   # MIT License file
└── README.md                 # Main overview guide
```

---

## 🔌 API Structure

The system exposes modular endpoints. The primary endpoint for summarization is:

### Post Summarize Content
*   **Path**: `/api/summarize`
*   **Method**: `POST`
*   **Content-Type**: `multipart/form-data`
*   **Fields**:
    *   `text` (Optional): Raw text string
    *   `youtube_url` (Optional): Video link
    *   `file` (Optional): Supported PDF/PPTX/Image document

For example query schemas and response bodies, see the [API Documentation](docs/api_documentation.md).

---

## 🚀 Deployment Guide

We recommend the following deployment platforms:
*   **Frontend**: Host on [Vercel](https://vercel.com) or [Netlify](https://netlify.com) using the build directory `dist`.
*   **Backend**: Host on [Render](https://render.com) or [Heroku](https://heroku.com) utilizing the WSGI server `gunicorn`.

For comprehensive hosting parameters, CORS configurations, and proxy settings, see the [Deployment Guide](docs/deployment.md).

---

## 🔮 Future Enhancements

*   **Vector Database (RAG)**: Introduce ChromaDB/Pinecone to allow users to ask follow-up questions about their documents.
*   **Quiz Engine**: Add a multi-choice quiz generator that validates user understanding of the summaries.
*   **Progress Tracking Dashboard**: User profiles with levels, experience points (XP), and historical learning tracking metrics.
*   **Audio Summaries**: Integrate Text-to-Speech (TTS) to generate read-aloud options for study summaries.

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

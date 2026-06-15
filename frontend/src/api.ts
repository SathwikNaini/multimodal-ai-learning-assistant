export interface VideoMetadata {
    id?: string;
    title: string;
    link: string;
    thumbnail: string;
    channel: string;
    duration: string;
}

export interface LearningGap {
    concept: string;
    reason: string;
    youtube_query: string;
    video?: VideoMetadata;
}

export interface QuizQuestion {
    question: string;
    options: string[];
    correct_answer: string;
    explanation: string;
}

export interface AnalysisResponse {
    main_theme: string;
    important_observations: string[];
    major_topics: string[];
    key_statistics: string[];
    important_entities: string[];
    timeline: string[];
    turning_points: string[];
    strengths: string[];
    weaknesses: string[];
    core_insights: string[];
    learning_gaps: LearningGap[];
    quiz: QuizQuestion[];
    final_verdict: string;
    difficulty_level: string;
    knowledge_score: number;
    estimated_reading_time: string;
    error?: string;
    details?: string;
}

// Get API URL from environment or use default for local development
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000';

export const analyzeContent = async (text: string, file: File | null, youtubeUrl?: string): Promise<AnalysisResponse> => {
    const formData = new FormData();

    if (youtubeUrl) {
        formData.append('youtube_url', youtubeUrl);
    } else if (file) {
        formData.append('file', file);
    } else if (text) {
        formData.append('text', text);
    } else {
        throw new Error("Please provide text, a file, or a YouTube URL.");
    }

    const response = await fetch(`${API_BASE_URL}/api/summarize`, {
        method: 'POST',
        body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || data.details || 'Failed to analyze content');
    }

    return data.data;
};

import React, { useState } from 'react';
import { Send, Loader2, Upload, FileText, Image as ImageIcon, Download, PlayCircle, X } from 'lucide-react';
import { analyzeContent, AnalysisResponse } from '../api';
import jsPDF from 'jspdf';

const AnalysisSection = () => {
    const [textInput, setTextInput] = useState("");
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [result, setResult] = useState<AnalysisResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [activeTab, setActiveTab] = useState<'upload' | 'text' | 'youtube'>('upload');
    const [youtubeUrl, setYoutubeUrl] = useState("");

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setSelectedFile(e.target.files[0]);
            setTextInput("");
            setYoutubeUrl("");
        }
    };

    const [selectedAnswers, setSelectedAnswers] = useState<Record<number, string>>({});

    const handleSelectOption = (qIdx: number, option: string) => {
        if (selectedAnswers[qIdx]) return;
        setSelectedAnswers(prev => ({
            ...prev,
            [qIdx]: option
        }));
    };

    const handleProcess = async () => {
        if (!textInput.trim() && !selectedFile && !youtubeUrl.trim()) return alert("Please Provide Content!");

        setLoading(true);
        setError(null);
        setResult(null);
        setSelectedAnswers({});

        try {
            // Pass the youtubeUrl if the tab is active
            const urlToProcess = activeTab === 'youtube' ? youtubeUrl : undefined;
            const textToProcess = activeTab === 'text' ? textInput : "";
            const fileToProcess = activeTab === 'upload' ? selectedFile : null;

            const data = await analyzeContent(textToProcess, fileToProcess, urlToProcess);
            setResult(data);
        } catch (err) {
            console.error("Analysis Error:", err);
            setError(err instanceof Error ? err.message : "An unexpected error occurred.");
        } finally {
            setLoading(false);
        }
    };

    const exportPDF = () => {
        if (!result) return;
        const doc = new jsPDF();
        let yPos = 20;

        const checkPage = (lineCount: number = 1) => {
            if (yPos + (lineCount * 7) > 280) {
                doc.addPage();
                yPos = 20;
            }
        };

        const addHeader = (text: string) => {
            checkPage(3);
            doc.setFont("helvetica", "bold");
            doc.setFontSize(14);
            doc.setTextColor(0, 51, 102);
            doc.text(text, 10, yPos);
            yPos += 8;
            doc.setFont("helvetica", "normal");
            doc.setFontSize(11);
            doc.setTextColor(0, 0, 0);
        };

        // Title
        doc.setFont("helvetica", "bold");
        doc.setFontSize(22);
        doc.setTextColor(0, 51, 102);
        doc.text("Intelligent Research Report", 10, yPos);
        yPos += 12;

        // Metadata block on first page
        doc.setFontSize(11);
        doc.setFont("helvetica", "bold");
        doc.setTextColor(100, 100, 100);
        doc.text(`Difficulty: ${result.difficulty_level}  |  Knowledge Score: ${result.knowledge_score}/100  |  Reading Time: ${result.estimated_reading_time}`, 10, yPos);
        yPos += 12;

        // 1. Theme and Verdict
        addHeader("🏆 Main Theme");
        const themeSplit = doc.splitTextToSize(result.main_theme || "Not specified.", 180);
        doc.text(themeSplit, 10, yPos);
        yPos += (themeSplit.length * 7) + 5;

        addHeader("📝 Final Verdict");
        const verdictSplit = doc.splitTextToSize(result.final_verdict || "Not specified.", 180);
        doc.text(verdictSplit, 10, yPos);
        yPos += (verdictSplit.length * 7) + 5;

        // 2. Observations
        addHeader("🔎 Important Observations");
        result.important_observations.forEach((line, idx) => {
            const splitLine = doc.splitTextToSize(`${idx + 1}. ${line}`, 180);
            checkPage(splitLine.length);
            doc.text(splitLine, 10, yPos);
            yPos += (splitLine.length * 7);
        });
        yPos += 5;

        // 3. Topics
        if (result.major_topics && result.major_topics.length > 0) {
            addHeader("📑 Major Topics Covered");
            result.major_topics.forEach((topic) => {
                const splitLine = doc.splitTextToSize(`• ${topic}`, 180);
                checkPage(splitLine.length);
                doc.text(splitLine, 10, yPos);
                yPos += (splitLine.length * 7);
            });
            yPos += 5;
        }

        // 4. Statistics
        if (result.key_statistics && result.key_statistics.length > 0) {
            addHeader("📊 Key Facts & Statistics");
            result.key_statistics.forEach((stat) => {
                const splitLine = doc.splitTextToSize(`• ${stat}`, 180);
                checkPage(splitLine.length);
                doc.text(splitLine, 10, yPos);
                yPos += (splitLine.length * 7);
            });
            yPos += 5;
        }

        // 5. Entities
        if (result.important_entities && result.important_entities.length > 0) {
            addHeader("👤 Important Entities");
            const entitiesStr = result.important_entities.join(", ");
            const splitEntities = doc.splitTextToSize(entitiesStr, 180);
            doc.text(splitEntities, 10, yPos);
            yPos += (splitEntities.length * 7) + 5;
        }

        // 6. Timeline
        if (result.timeline && result.timeline.length > 0) {
            addHeader("📅 Timeline of Events");
            result.timeline.forEach((item) => {
                const splitLine = doc.splitTextToSize(`• ${item}`, 180);
                checkPage(splitLine.length);
                doc.text(splitLine, 10, yPos);
                yPos += (splitLine.length * 7);
            });
            yPos += 5;
        }

        // 7. Turning Points
        if (result.turning_points && result.turning_points.length > 0) {
            addHeader("🔄 Turning Points");
            result.turning_points.forEach((item) => {
                const splitLine = doc.splitTextToSize(`• ${item}`, 180);
                checkPage(splitLine.length);
                doc.text(splitLine, 10, yPos);
                yPos += (splitLine.length * 7);
            });
            yPos += 5;
        }

        // 8. Strengths
        if (result.strengths && result.strengths.length > 0) {
            addHeader("⚖️ Strengths");
            result.strengths.forEach((item) => {
                const splitLine = doc.splitTextToSize(`• ${item}`, 180);
                checkPage(splitLine.length);
                doc.text(splitLine, 10, yPos);
                yPos += (splitLine.length * 7);
            });
            yPos += 5;
        }

        // 9. Weaknesses
        if (result.weaknesses && result.weaknesses.length > 0) {
            addHeader("⚖️ Limitations & Weaknesses");
            result.weaknesses.forEach((item) => {
                const splitLine = doc.splitTextToSize(`• ${item}`, 180);
                checkPage(splitLine.length);
                doc.text(splitLine, 10, yPos);
                yPos += (splitLine.length * 7);
            });
            yPos += 5;
        }

        // 10. Core Insights
        if (result.core_insights && result.core_insights.length > 0) {
            addHeader("🧠 Core Insights");
            result.core_insights.forEach((insight) => {
                const splitLine = doc.splitTextToSize(`• ${insight}`, 180);
                checkPage(splitLine.length);
                doc.text(splitLine, 10, yPos);
                yPos += (splitLine.length * 7);
            });
            yPos += 5;
        }

        // 11. Quiz
        if (result.quiz && result.quiz.length > 0) {
            addHeader("❓ Study Quiz Questions");
            result.quiz.forEach((q, idx) => {
                checkPage(4);
                doc.setFont("helvetica", "bold");
                doc.text(`Q${idx + 1}: ${q.question}`, 10, yPos);
                yPos += 7;
                doc.setFont("helvetica", "normal");
                
                q.options.forEach((opt) => {
                    checkPage(1);
                    doc.text(`   ${opt}`, 10, yPos);
                    yPos += 6;
                });
                
                checkPage(2);
                doc.setFont("helvetica", "italic");
                doc.text(`   Correct Answer: ${q.correct_answer}`, 10, yPos);
                yPos += 6;
                const expSplit = doc.splitTextToSize(`   Explanation: ${q.explanation}`, 170);
                checkPage(expSplit.length);
                doc.text(expSplit, 10, yPos);
                yPos += (expSplit.length * 6) + 4;
                doc.setFont("helvetica", "normal");
            });
            yPos += 5;
        }

        // 12. Learning Gaps
        if (result.learning_gaps && result.learning_gaps.length > 0) {
            addHeader("🎯 Learning Gaps & Resources");
            result.learning_gaps.forEach((gap, idx) => {
                checkPage(4);
                doc.setFont("helvetica", "bold");
                doc.text(`Gap ${idx + 1}: ${gap.concept}`, 10, yPos);
                yPos += 7;

                doc.setFont("helvetica", "normal");
                const reasonSplit = doc.splitTextToSize(`Reason: ${gap.reason}`, 180);
                doc.text(reasonSplit, 10, yPos);
                yPos += (reasonSplit.length * 7);

                if (gap.video) {
                    checkPage(1);
                    doc.setTextColor(0, 0, 255);
                    doc.text(`Recommended Resource: ${gap.video.title} (${gap.video.channel})`, 10, yPos);
                    doc.link(10, yPos - 5, 180, 10, { url: gap.video.link });
                    doc.setTextColor(0, 0, 0);
                    yPos += 8;
                }
                yPos += 3;
            });
        }

        doc.save("Analyst_Intelligence_Report.pdf");
    };

    return (
        <section className="py-20 px-6 bg-slate-50 border-y border-slate-200" id="analysis">
            <div className="max-w-5xl mx-auto">

                {/* HEADER */}
                <div className="text-center mb-12">
                    <h2 className="text-4xl font-extrabold text-slate-900 mb-4">Smart Learning Assistant</h2>
                    <p className="text-lg text-slate-600 max-w-2xl mx-auto">
                        Upload your lecture slides (PPT), notes (PDF), images, or <span className="text-blue-600 font-bold">YouTube Videos</span> to get a detailed summary and learning gaps.
                    </p>
                </div>

                {/* INPUT SECTION */}
                <div className="bg-white p-8 rounded-3xl shadow-lg border border-slate-100 mb-12 relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-indigo-500 to-violet-500"></div>

                    {/* TABS */}
                    <div className="flex justify-center mb-8 gap-4">
                        <button
                            onClick={() => setActiveTab('upload')}
                            className={`px-6 py-2 rounded-full font-bold transition-all ${activeTab === 'upload' ? 'bg-indigo-100 text-indigo-600' : 'text-slate-500 hover:bg-slate-50'}`}
                        >
                            Upload File
                        </button>
                        <button
                            onClick={() => setActiveTab('text')}
                            className={`px-6 py-2 rounded-full font-bold transition-all ${activeTab === 'text' ? 'bg-indigo-100 text-indigo-600' : 'text-slate-500 hover:bg-slate-50'}`}
                        >
                            Paste Text
                        </button>
                        <button
                            onClick={() => setActiveTab('youtube')}
                            className={`px-6 py-2 rounded-full font-bold transition-all ${activeTab === 'youtube' ? 'bg-rose-100 text-rose-600' : 'text-slate-500 hover:bg-slate-50'}`}
                        >
                            YouTube Link
                        </button>
                    </div>

                    <div className="min-h-[200px]">
                        {/* UPLOAD TAB */}
                        {activeTab === 'upload' && (
                            <div className={`border-2 border-dashed rounded-2xl p-8 flex flex-col items-center justify-center text-center transition-all ${selectedFile ? 'border-indigo-500 bg-indigo-50' : 'border-slate-300 hover:border-indigo-400'}`}>
                                <input type="file" onChange={handleFileChange} id="fileInput" className="hidden" accept=".pdf,.pptx,.txt,.png,.jpg,.jpeg,.mp4,.mov,.avi" />

                                {selectedFile ? (
                                    <div className="w-full">
                                        <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                            {selectedFile.type.startsWith('image/') ? (
                                                <ImageIcon className="w-8 h-8 text-indigo-600" />
                                            ) : selectedFile.type.startsWith('video/') ? (
                                                <PlayCircle className="w-8 h-8 text-rose-600" />
                                            ) : (
                                                <FileText className="w-8 h-8 text-indigo-600" />
                                            )}
                                        </div>
                                        <p className="font-bold text-slate-800 truncate px-4">{selectedFile.name}</p>
                                        <button onClick={() => setSelectedFile(null)} className="text-sm text-red-500 hover:underline mt-2 flex items-center justify-center gap-1 mx-auto">
                                            <X className="w-4 h-4" /> Remove
                                        </button>
                                    </div>
                                ) : (
                                    <label htmlFor="fileInput" className="cursor-pointer w-full h-full flex flex-col items-center justify-center py-4">
                                        <Upload className="w-10 h-10 text-slate-400 mb-3" />
                                        <p className="font-bold text-slate-700">Click to Upload</p>
                                        <p className="text-sm text-slate-500">PDF, PPT, Images, Videos</p>
                                    </label>
                                )}
                            </div>
                        )}

                        {/* TEXT TAB */}
                        {activeTab === 'text' && (
                            <textarea
                                value={textInput}
                                onChange={(e) => setTextInput(e.target.value)}
                                placeholder="Paste your study notes or article text here..."
                                className="w-full h-full min-h-[200px] p-4 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-indigo-500 outline-none resize-none"
                            />
                        )}

                        {/* YOUTUBE TAB */}
                        {activeTab === 'youtube' && (
                            <div className="flex flex-col items-center justify-center h-full min-h-[200px] text-center">
                                <PlayCircle className="w-12 h-12 text-rose-500 mb-4" />
                                <h3 className="text-xl font-bold text-slate-900 mb-2">Summarize a YouTube Video</h3>
                                <p className="text-slate-500 mb-6">Paste the link below to extract the transcript and find learning gaps.</p>
                                <input
                                    type="text"
                                    value={youtubeUrl}
                                    onChange={(e) => setYoutubeUrl(e.target.value)}
                                    placeholder="https://www.youtube.com/watch?v=..."
                                    className="w-full max-w-lg px-4 py-3 border border-slate-200 rounded-xl focus:ring-2 focus:ring-rose-500 outline-none"
                                />
                            </div>
                        )}
                    </div>

                    <button
                        onClick={handleProcess}
                        disabled={loading}
                        className="w-full mt-8 py-4 bg-gradient-to-r from-indigo-600 to-violet-600 text-white rounded-2xl font-bold hover:shadow-lg hover:shadow-indigo-500/25 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3 transition-all transform active:scale-95"
                    >
                        {loading ? <Loader2 className="animate-spin w-5 h-5" /> : <Send className="w-5 h-5" />}
                        {loading ? "Analyzing Multimodal Content..." : "Analyze Now"}
                    </button>

                    {error && (
                        <div className="mt-6 p-4 bg-red-50 text-red-700 rounded-xl text-center border border-red-100">
                            <p className="font-bold">Analysis Failed</p>
                            <p className="text-sm opacity-90">{error}</p>
                        </div>
                    )}
                </div>

                {/* RESULTS SECTION */}
                {result && (
                    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-8 duration-700">

                        <div className="flex justify-between items-center">
                            <h3 className="text-2xl font-bold text-slate-900">Analysis Results</h3>
                            <button onClick={exportPDF} className="flex items-center gap-2 px-4 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700 transition-all font-medium">
                                <Download className="w-4 h-4" /> Download Report
                            </button>
                        </div>

                        {result.summary.some(point => point.includes("Full transcript unavailable")) && (
                            <div className="p-4 bg-amber-50 border border-amber-200 text-amber-800 rounded-2xl flex items-center gap-3">
                                <span className="text-xl">⚠</span>
                                <div>
                                    <p className="font-bold">Transcript unavailable. Using video metadata analysis.</p>
                                    <p className="text-sm opacity-90">Detailed transcripts could not be extracted. A high-level overview has been compiled from video attributes.</p>
                                </div>
                            </div>
                        )}

                        {/* 1. SUMMARY */}
                        <div className="bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
                            <h4 className="text-lg font-bold text-slate-500 uppercase tracking-wider mb-4">Comprehensive Module Summary</h4>
                            <ul className="space-y-4">
                                {result.summary.slice(0, 15).map((point, idx) => (
                                    <li key={idx} className="flex gap-4 text-slate-700 leading-relaxed text-lg">
                                        <span className="flex-shrink-0 w-8 h-8 bg-green-100 text-green-700 rounded-full flex items-center justify-center font-bold text-sm">
                                            {idx + 1}
                                        </span>
                                        <span className="mt-0.5">{point}</span>
                                    </li>
                                ))}
                            </ul>

                            {result.summary.length > 15 && (
                                <div className="mt-6 p-4 bg-blue-50 text-blue-800 rounded-xl text-center border border-blue-100">
                                    <p className="font-bold">Summary Truncated</p>
                                    <p className="text-sm">Showing the first 15 points. Please fast-track your learning by downloading the full report to see all {result.summary.length} points.</p>
                                    <button onClick={exportPDF} className="mt-2 text-sm font-bold underline hover:text-blue-600">
                                        Download Full Report PDF
                                    </button>
                                </div>
                            )}
                        </div>

                        {/* 2. VIDEO RECOMMENDATIONS */}
                        <div>
                            <h4 className="text-xl font-bold text-slate-900 mb-6 px-2">Recommended Learning Path</h4>

                            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {result.cognitive_gaps.map((gap, idx) => (
                                    <div key={idx} className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full hover:shadow-md transition-shadow">
                                        {/* Video Embed */}
                                        {gap.video && gap.video.id ? (
                                            <div className="aspect-video bg-black">
                                                <iframe
                                                    width="100%"
                                                    height="100%"
                                                    src={`https://www.youtube.com/embed/${gap.video.id}`}
                                                    title={gap.video.title}
                                                    frameBorder="0"
                                                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                                    allowFullScreen
                                                ></iframe>
                                            </div>
                                        ) : gap.video ? (
                                            <a href={gap.video.link} target="_blank" rel="noreferrer" className="block relative group aspect-video bg-slate-100">
                                                <img src={gap.video.thumbnail} alt={gap.video.title} className="w-full h-full object-cover" />
                                                <div className="absolute inset-0 bg-black/20 group-hover:bg-black/40 transition-colors flex items-center justify-center">
                                                    <PlayCircle className="w-12 h-12 text-white opacity-80 group-hover:scale-110 transition-transform" />
                                                </div>
                                                <span className="absolute bottom-2 right-2 bg-black/70 text-white text-xs px-2 py-1 rounded">{gap.video.duration}</span>
                                            </a>
                                        ) : null}

                                        <div className="p-5 flex flex-col flex-grow">
                                            <div className="mb-4">
                                                <span className="inline-block px-3 py-1 bg-amber-100 text-amber-800 text-xs font-bold rounded-full mb-2">
                                                    Topic {idx + 1}
                                                </span>
                                                <h5 className="font-bold text-slate-900 text-lg leading-tight mb-2">{gap.concept}</h5>
                                                <p className="text-sm text-slate-600 line-clamp-3">{gap.reason}</p>
                                            </div>

                                            <div className="mt-auto pt-4 border-t border-slate-100">
                                                <p className="text-xs text-slate-400 font-medium uppercase mb-1">Source Channel</p>
                                                <p className="text-sm font-semibold text-slate-700">{gap.video?.channel || "Recommended Channel"}</p>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                    </div>
                )}

            </div>
        </section>
    );
};

export default AnalysisSection;

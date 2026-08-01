tailwind.config = {
    darkMode: "class",
    theme: {
        extend: {
            colors: {
                "outline": "#7f7660",
                "error-container": "#ffdad6",
                "error": "#ba1a1a",
                "on-secondary-fixed-variant": "#474747",
                "surface-dim": "#dadada",
                "surface-container-highest": "#e2e2e2",
                "on-surface-variant": "#4d4632",
                "on-tertiary-container": "#b2131f",
                "on-tertiary": "#ffffff",
                "on-secondary": "#ffffff",
                "secondary-fixed-dim": "#c6c6c6",
                "surface-container": "#eeeeee",
                "on-tertiary-fixed-variant": "#930013",
                "on-background": "#1b1b1b",
                "surface-container-high": "#e8e8e8",
                "on-surface": "#1b1b1b",
                "tertiary": "#b91a24",
                "on-secondary-container": "#646464",
                "on-tertiary-fixed": "#410004",
                "surface-tint": "#735c00",
                "primary-container": "#facc15",
                "on-primary-fixed": "#231b00",
                "tertiary-fixed": "#ffdad7",
                "surface-container-lowest": "#ffffff",
                "on-error": "#ffffff",
                "surface-container-low": "#f3f3f3",
                "background": "#f9f9f9",
                "on-primary": "#ffffff",
                "primary": "#735c00",
                "surface-bright": "#f9f9f9",
                "tertiary-fixed-dim": "#ffb3ad",
                "on-secondary-fixed": "#1b1b1b",
                "on-primary-container": "#6c5700",
                "secondary-container": "#e2e2e2",
                "secondary": "#5e5e5e",
                "primary-fixed": "#ffe083",
                "outline-variant": "#d1c6ab",
                "tertiary-container": "#ffc2bd",
                "on-error-container": "#93000a",
                "inverse-on-surface": "#f1f1f1",
                "inverse-primary": "#eec200",
                "primary-fixed-dim": "#eec200",
                "on-primary-fixed-variant": "#574500",
                "surface": "#f9f9f9",
                "inverse-surface": "#303030",
                "secondary-fixed": "#e2e2e2",
                "surface-variant": "#e2e2e2"
            },
            fontFamily: {
                "headline": ["Space Grotesk"],
                "body": ["Inter"],
                "label": ["Space Grotesk"]
            },
            borderRadius: { "DEFAULT": "0px", "lg": "0px", "xl": "0px", "full": "9999px" },
        },
    },
}

// --- YouTube Iframe Player API ---
let ytPlayer = null;
let ytPlayerReady = false;
let pendingVideoId = null;

// This function is called by the YouTube Iframe API when it's ready
function onYouTubeIframeAPIReady() {
    console.log('YouTube Iframe API is ready.');
    ytPlayerReady = true;
    if (pendingVideoId) {
        initPlayer(pendingVideoId);
        pendingVideoId = null;
    }
}

function initPlayer(videoId) {
    const container = document.getElementById('player-container');
    const playerDiv = document.getElementById('yt-player');

    if (!container || !playerDiv) return;

    // Destroy existing player if any
    if (ytPlayer && typeof ytPlayer.destroy === 'function') {
        ytPlayer.destroy();
    }

    // Clear the target div (YouTube replaces it with an iframe)
    playerDiv.innerHTML = '';

    container.classList.remove('hidden');

    ytPlayer = new YT.Player('yt-player', {
        videoId: videoId,
        width: '100%',
        height: '100%',
        playerVars: {
            'autoplay': 0,
            'modestbranding': 1,
            'rel': 0,
            'fs': 1,
        },
        events: {
            'onReady': function(event) {
                console.log('YouTube player ready for video:', videoId);
            }
        }
    });
}

function seekToTimestamp(seconds) {
    if (ytPlayer && typeof ytPlayer.seekTo === 'function') {
        ytPlayer.seekTo(seconds, true);
        ytPlayer.playVideo();

        // Smooth scroll to player
        const container = document.getElementById('player-container');
        if (container) {
            container.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
}

function timestampToSeconds(timestamp) {
    // Parse "MM:SS" or "HH:MM:SS" format
    const parts = timestamp.split(':').map(Number);
    if (parts.length === 3) {
        return parts[0] * 3600 + parts[1] * 60 + parts[2];
    } else if (parts.length === 2) {
        return parts[0] * 60 + parts[1];
    }
    return 0;
}

// --- Main Application Logic ---
document.addEventListener('DOMContentLoaded', () => {
    let selectedLanguage = 'English';
    let lastAnalysisData = null; // Store for export

    const langButtons = document.querySelectorAll('.lang-btn');
    const youtubeUrlInput = document.getElementById('youtube-url');
    const summarizeBtn = document.getElementById('summarize-btn');
    const highlightsList = document.getElementById('highlights-list');
    const highlightsHeading = document.getElementById('highlights-heading');
    const highlightsEnglishLabel = document.getElementById('highlights-english-label');
    const keyPointsList = document.getElementById('key-points-list');
    const keyPointsHeading = document.getElementById('key-points-heading');
    const keyPointsEnglishLabel = document.getElementById('key-points-english-label');
    const detailedSummary = document.getElementById('detailed-summary');
    const summaryHeading = document.getElementById('summary-heading');
    const summaryEnglishLabel = document.getElementById('summary-english-label');
    const copyBtn = document.getElementById('copy-btn');
    const exportMdBtn = document.getElementById('export-md-btn');
    const playerContainer = document.getElementById('player-container');
    const videoMetadataContainer = document.getElementById('video-metadata');
    const videoThumbnail = document.getElementById('video-thumbnail');
    const videoTitle = document.getElementById('video-title');
    const videoTitleFallback = document.getElementById('video-title-fallback');
    const brutalistLoader = document.getElementById('brutalist-loader');
    const loaderStatus = document.getElementById('loader-status');
    const quickInsightText = document.getElementById('quick-insight-text');
    const quickInsightHeading = document.getElementById('quick-insight-heading');
    const quickInsightEnglishLabel = document.getElementById('quick-insight-english-label');

    // Language Selection Logic
    langButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            langButtons.forEach(b => {
                b.classList.remove('bg-on-background', 'text-white');
                b.classList.add('bg-surface');
            });
            btn.classList.add('bg-on-background', 'text-white');
            btn.classList.remove('bg-surface');
            selectedLanguage = btn.getAttribute('data-lang');
            updateLocalizedLabels(selectedLanguage);
        });
    });

    function updateLocalizedLabels(language) {
        const labels = {
            English: {
                highlights: 'Key Highlights',
                summary: 'Detailed Summary',
                quickInsight: 'Quick Insight',
                keyPoints: 'Key Points',
            },
            Hindi: {
                highlights: 'मुख्य झलकियाँ',
                summary: 'विस्तृत सारांश',
                quickInsight: 'त्वरित अंतर्दृष्टि',
                keyPoints: 'मुख्य बिंदु',
            },
            Marathi: {
                highlights: 'मुख्य ठळक मुद्दे',
                summary: 'सविस्तर सारांश',
                quickInsight: 'त्वरित अंतर्दृष्टी',
                keyPoints: 'महत्त्वाचे मुद्दे',
            },
        };
        const current = labels[language] || labels.English;
        const showEnglishContext = language !== 'English';

        const setBilingualHeading = (heading, englishLabel, englishText, localizedText) => {
            if (heading) heading.textContent = localizedText;
            if (englishLabel) {
                englishLabel.textContent = englishText;
                englishLabel.classList.toggle('hidden', !showEnglishContext);
            }
        };

        setBilingualHeading(highlightsHeading, highlightsEnglishLabel, 'Key Highlights', current.highlights);
        setBilingualHeading(summaryHeading, summaryEnglishLabel, 'Detailed Summary', current.summary);
        setBilingualHeading(quickInsightHeading, quickInsightEnglishLabel, 'Quick Insight', current.quickInsight);
        setBilingualHeading(keyPointsHeading, keyPointsEnglishLabel, 'Essential Takeaways', current.keyPoints);
    }

    // Summarize Button Logic
    summarizeBtn.addEventListener('click', async () => {
        const url = youtubeUrlInput.value.trim();
        if (!url) {
            alert('Please enter a YouTube URL.');
            return;
        }

        // Start Loading State
        const originalBtnText = summarizeBtn.innerText;
        summarizeBtn.innerText = 'Analyzing...';
        summarizeBtn.disabled = true;
        summarizeBtn.classList.add('opacity-50', 'cursor-not-allowed');
        if (brutalistLoader) brutalistLoader.style.display = 'flex';
        if (loaderStatus) loaderStatus.innerText = 'Downloading media...';
        if (quickInsightText) quickInsightText.innerText = 'Analyzing insight...';

        if (highlightsList) highlightsList.innerHTML = '';
        if (detailedSummary) detailedSummary.innerHTML = '';
        if (playerContainer) playerContainer.classList.add('hidden');
        if (videoMetadataContainer) videoMetadataContainer.classList.add('hidden');

        const resultsSection = document.getElementById('results-section');
        if (resultsSection) {
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            resultsSection.classList.add('min-h-[600px]');
        }

        // Simulate loader progress messages
        const statusMessages = [
            'Downloading media...',
            'Uploading to Gemini...',
            'Running multimodal analysis...',
            'Generating structured summary...',
        ];
        let statusIndex = 0;
        const statusInterval = setInterval(() => {
            statusIndex++;
            if (statusIndex < statusMessages.length && loaderStatus) {
                loaderStatus.innerText = statusMessages[statusIndex];
            }
        }, 4000);

        try {
            const response = await fetch('/summarize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: url,
                    language: selectedLanguage
                })
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                const errorMessage = errorData.detail || errorData.message || 'Failed to analyze video. Please check the URL and try again.';
                throw new Error(errorMessage);
            }

            const data = await response.json();
            lastAnalysisData = data;
            updateResultsUI(data);

        } catch (error) {
            console.error('Summarization Error:', error);
            alert(error.message);
        } finally {
            clearInterval(statusInterval);
            summarizeBtn.innerText = originalBtnText;
            summarizeBtn.disabled = false;
            summarizeBtn.classList.remove('opacity-50', 'cursor-not-allowed');
            if (brutalistLoader) brutalistLoader.style.display = 'none';
            if (resultsSection) resultsSection.classList.remove('min-h-[600px]');
        }
    });

    // --- Copy to Clipboard ---
    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            const textToCopy = buildPlainTextReport();

            if (navigator.clipboard) {
                navigator.clipboard.writeText(textToCopy).then(() => {
                    showBtnFeedback(copyBtn, 'check', 'Copied!');
                }).catch(() => {
                    if (fallbackCopy(textToCopy)) showBtnFeedback(copyBtn, 'check', 'Copied!');
                    else alert('Copy failed. Please copy manually.');
                });
            } else {
                if (fallbackCopy(textToCopy)) showBtnFeedback(copyBtn, 'check', 'Copied!');
                else alert('Copy failed. Please copy manually.');
            }
        });
    }

    // --- Export as Markdown ---
    if (exportMdBtn) {
        exportMdBtn.addEventListener('click', () => {
            if (!lastAnalysisData) {
                alert('No analysis data to export. Run a summary first.');
                return;
            }
            const markdown = buildMarkdownReport(lastAnalysisData);
            const filename = (lastAnalysisData.title || 'VDescribe_Report')
                .replace(/[^a-zA-Z0-9 ]/g, '')
                .replace(/\s+/g, '_')
                .substring(0, 50);

            downloadFile(`${filename}.md`, markdown, 'text/markdown');
            showBtnFeedback(exportMdBtn, 'check', 'Saved!');
        });
    }

    // --- Helper: Build plain text for clipboard ---
    function buildPlainTextReport() {
        let text = '';
        const titleEl = document.getElementById('video-title');
        if (titleEl && titleEl.innerText) {
            text += titleEl.innerText.toUpperCase() + '\n\n';
        }
        if (highlightsList && highlightsList.children.length > 0) {
            text += 'KEY HIGHLIGHTS:\n';
            Array.from(highlightsList.children).forEach((li, index) => {
                const timestampEl = li.querySelector('.timestamp-pill');
                const textSpan = li.querySelector('.highlight-text');
                const ts = timestampEl ? `[${timestampEl.innerText}] ` : '';
                const txt = textSpan ? textSpan.innerText : li.innerText.replace(/^\d+\s*/, '');
                text += `${index + 1}. ${ts}${txt}\n`;
            });
            text += '\n';
        }
        if (keyPointsList && keyPointsList.children.length > 0) {
            text += 'KEY POINTS:\n';
            Array.from(keyPointsList.children).forEach((li, index) => {
                const pointText = li.querySelector('.key-point-text');
                text += `${index + 1}. ${pointText ? pointText.innerText : li.innerText}\n`;
            });
            text += '\n';
        }
        if (detailedSummary) {
            text += 'DETAILED SUMMARY:\n';
            text += detailedSummary.innerText + '\n\n';
        }
        if (quickInsightText) {
            text += 'QUICK INSIGHT:\n';
            text += quickInsightText.innerText + '\n';
        }
        return text;
    }

    // --- Helper: Build Markdown report for export ---
    function buildMarkdownReport(data) {
        let md = '';
        md += `# ${data.title || 'Video Analysis Report'}\n\n`;
        md += `> Generated by [VDescribe](https://vdescribe.onrender.com) — AI-Powered Video Intelligence\n\n`;

        if (data.video_id) {
            md += `**Video:** https://youtube.com/watch?v=${data.video_id}\n\n`;
        }

        if (data.is_multimodal) {
            md += `> 🔬 **Multimodal Analysis** — Both video frames and audio were analyzed.\n\n`;
        }

        md += `---\n\n`;
        md += `## Key Highlights\n\n`;

        if (data.highlights && data.highlights.length > 0) {
            data.highlights.forEach((h, i) => {
                const timestamp = (typeof h === 'object') ? h.timestamp : '00:00';
                const text = (typeof h === 'object') ? h.text : h;
                md += `${i + 1}. **[${timestamp}]** ${text}\n`;
            });
        }

        md += `\n---\n\n`;
        md += `## Key Points\n\n`;

        if (data.key_points && data.key_points.length > 0) {
            data.key_points.forEach((point, i) => {
                md += `${i + 1}. ${point}\n`;
            });
        }

        md += `\n---\n\n`;
        md += `## Detailed Summary\n\n`;

        if (data.summary) {
            // Strip HTML tags for markdown
            const plainSummary = data.summary
                .replace(/<p>/gi, '')
                .replace(/<\/p>/gi, '\n\n')
                .replace(/<[^>]*>/g, '')
                .trim();
            md += plainSummary + '\n\n';
        }

        md += `---\n\n`;
        md += `## Quick Insight\n\n`;
        md += `> ${data.quick_insight || 'N/A'}\n`;

        return md;
    }

    // --- Helper: Download file ---
    function downloadFile(filename, content, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // --- Helper: Fallback copy ---
    function fallbackCopy(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-9999px';
        textArea.style.top = '-9999px';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        let ok = false;
        try { ok = document.execCommand('copy'); } catch(e) { ok = false; }
        document.body.removeChild(textArea);
        return ok;
    }

    // --- Helper: Show button feedback ---
    function showBtnFeedback(btn, icon, label) {
        const original = btn.innerHTML;
        btn.innerHTML = `<span class="material-symbols-outlined">${icon}</span><span class="hidden md:inline font-bold uppercase text-sm tracking-widest">${label}</span>`;
        setTimeout(() => { btn.innerHTML = original; }, 2000);
    }

    /**
     * Updates the highlights, key points, summary, player, and metadata in the DOM.
     */
    function updateResultsUI(data) {
        // 1. Update Highlights (with timestamps)
        if (highlightsList && data.highlights) {
            highlightsList.innerHTML = '';
            data.highlights.forEach((highlight, index) => {
                const isObject = typeof highlight === 'object';
                const timestamp = isObject ? highlight.timestamp : null;
                const text = isObject ? highlight.text : highlight;
                const seconds = timestamp ? timestampToSeconds(timestamp) : 0;

                const li = document.createElement('li');
                li.className = 'flex gap-4 border-b border-surface/20 pb-4 highlight-item';
                if (index === data.highlights.length - 1) {
                    li.classList.remove('border-b', 'pb-4');
                }

                let timestampHtml = '';
                if (timestamp && timestamp !== '00:00') {
                    timestampHtml = `<button class="timestamp-pill bg-primary-container text-on-background px-2 py-1 text-xs font-black tracking-wider whitespace-nowrap hover:bg-[#FACC15]/80 active:scale-95 cursor-pointer" onclick="seekToTimestamp(${seconds})">${timestamp}</button>`;
                }

                li.innerHTML = `
                    <span class="text-primary-container font-black text-lg">${String(index + 1).padStart(2, '0')}</span>
                    <div class="flex flex-col gap-2 flex-1">
                        ${timestampHtml}
                        <span class="highlight-text">${text}</span>
                    </div>
                `;
                highlightsList.appendChild(li);
            });
        }

        // 2. Update Key Points
        if (keyPointsList && data.key_points) {
            keyPointsList.innerHTML = '';
            data.key_points.forEach((point, index) => {
                const li = document.createElement('li');
                li.className = 'key-point-item';

                const number = document.createElement('span');
                number.className = 'key-point-number';
                number.textContent = String(index + 1).padStart(2, '0');

                const text = document.createElement('span');
                text.className = 'key-point-text';
                text.textContent = point;

                li.append(number, text);
                keyPointsList.appendChild(li);
            });
        }

        // 3. Update Detailed Summary
        if (detailedSummary && data.summary) {
            // Insert a decorative separator between paragraphs
            let html = data.summary;
            const separator = `
                <div class="flex gap-8 items-center py-4">
                    <div class="h-[2px] bg-on-background flex-grow"></div>
                    <span class="material-symbols-outlined text-4xl" data-icon="bolt">bolt</span>
                    <div class="h-[2px] bg-on-background flex-grow"></div>
                </div>
            `;
            // Add separator after the first </p> tag (between first and second paragraph)
            const firstClose = html.indexOf('</p>');
            if (firstClose !== -1) {
                html = html.substring(0, firstClose + 4) + separator + html.substring(firstClose + 4);
            }
            detailedSummary.innerHTML = html;
        }

        // 4. Initialize YouTube Player with thumbnail as a loading placeholder
        if (data.video_id) {
            // Always show the player container and title immediately
            if (playerContainer) playerContainer.classList.remove('hidden');
            if (videoMetadataContainer) videoMetadataContainer.classList.add('hidden');
            if (videoTitle) videoTitle.textContent = data.title || "Video Analysis";

            if (ytPlayerReady) {
                initPlayer(data.video_id);
            } else {
                // Store it — onYouTubeIframeAPIReady will pick it up
                pendingVideoId = data.video_id;
                // Show a thumbnail poster inside the player div until the player loads
                const playerDiv = document.getElementById('yt-player');
                if (playerDiv && data.thumbnail_url) {
                    playerDiv.style.backgroundImage = `url('${data.thumbnail_url}')`;
                    playerDiv.style.backgroundSize = 'cover';
                    playerDiv.style.backgroundPosition = 'center';
                }
            }
        } else if (data.title || data.thumbnail_url) {
            // Fallback: show static thumbnail only if no video_id
            if (playerContainer) playerContainer.classList.add('hidden');
            if (videoMetadataContainer) {
                videoMetadataContainer.classList.remove('hidden');
                if (videoTitleFallback) videoTitleFallback.textContent = data.title || "Video Analysis";
                if (videoThumbnail && data.thumbnail_url) {
                    videoThumbnail.src = data.thumbnail_url;
                    videoThumbnail.alt = data.title || "Video Thumbnail";
                    videoThumbnail.classList.remove('hidden');
                }
            }
        }

        // 5. Update Quick Insight and its localized label
        if (quickInsightText && data.quick_insight) {
            quickInsightText.innerText = data.quick_insight;
        }
        updateLocalizedLabels(selectedLanguage);
    }
});

import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import "./InteractiveDemoSection.css";

// Add one real capture to frontend/public/demo/ and set src/type here.
// The four markers are narrative positions, not real match timestamps.
// Sync them to the capture when prepared replay data becomes available.
const demoMedia = {
    src: null, // "/demo/sample-round.mp4", "/demo/sample-radar.mp4", or "/demo/sample-round.webp"
    type: "video", // Set "image" for a .webp capture.
};

const moments = [
    { label: "First contact", description: "You take the fight before support is ready." },
    { label: "Support", description: "No immediate trade is available." },
    { label: "Information", description: "Multiple enemy positions remain possible." },
    { label: "Takeaway", description: "Wait for support or choose a tradeable position." },
];

function DemoMedia({ isPlaying }) {
    const videoRef = useRef(null);
    const [ready, setReady] = useState(false);
    const [failed, setFailed] = useState(false);
    const { src, type } = demoMedia;

    useEffect(() => {
        const video = videoRef.current;
        if (!video) return;
        if (isPlaying) video.play().catch(() => {});
        else video.pause();
    }, [isPlaying]);

    return (
        <div className="demo-media-frame">
            {src && !failed && type === "video" && (
                <video ref={videoRef} src={src} muted playsInline preload="metadata" onLoadedData={() => setReady(true)} onError={() => setFailed(true)} aria-hidden="true" />
            )}
            {src && !failed && type === "image" && (
                <img src={src} alt="" onLoad={() => setReady(true)} onError={() => setFailed(true)} aria-hidden="true" />
            )}
            {(!src || failed || !ready) && (
                <div className="demo-media-placeholder">
                    <span>SAMPLE ROUND</span>
                    <p>Real WatchDemo round review<br />will appear here.</p>
                </div>
            )}
        </div>
    );
}

function DemoTimeline({ activeIndex, onSelect }) {
    return (
        <div className="demo-timeline" aria-label="Prepared analysis moments">
            <div className="demo-timeline-line" aria-hidden="true" />
            {moments.map((moment, index) => (
                <button
                    key={moment.label}
                    type="button"
                    className={`demo-timeline-marker${index === activeIndex ? " is-active" : ""}`}
                    style={{ left: `${index / (moments.length - 1) * 100}%` }}
                    aria-label={`Moment ${index + 1}: ${moment.label}`}
                    aria-current={index === activeIndex ? "step" : undefined}
                    onClick={() => onSelect(index)}
                >
                    <span className="demo-timeline-dot" aria-hidden="true" />
                    <span className="demo-timeline-label">{moment.label}</span>
                </button>
            ))}
        </div>
    );
}

function MiniDemoPlayer() {
    const [activeIndex, setActiveIndex] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);

    useEffect(() => {
        if (!isPlaying) return undefined;
        const timer = window.setTimeout(() => {
            if (activeIndex === moments.length - 2) setIsPlaying(false);
            setActiveIndex(Math.min(activeIndex + 1, moments.length - 1));
        }, 2400);
        return () => window.clearTimeout(timer);
    }, [activeIndex, isPlaying]);

    function selectMoment(index) {
        setIsPlaying(false);
        setActiveIndex(index);
    }

    function togglePlayback() {
        if (!isPlaying && activeIndex === moments.length - 1) setActiveIndex(0);
        setIsPlaying((playing) => !playing);
    }

    return (
        <div className="demo-preview" aria-label="Prepared sample round preview">
            <DemoMedia isPlaying={isPlaying} />
            <div className="demo-controls">
                <button className="demo-play" type="button" onClick={togglePlayback} aria-label={isPlaying ? "Pause preview" : "Play preview"} aria-pressed={isPlaying}>
                    <span aria-hidden="true">{isPlaying ? "Ⅱ" : "▶"}</span>{isPlaying ? "Pause" : "Play"}
                </button>
                <DemoTimeline activeIndex={activeIndex} onSelect={selectMoment} />
                <span className="demo-time" aria-label="Time will be available with real footage">—:— / —:—</span>
            </div>
            <div className="demo-context" aria-live="polite" aria-atomic="true">
                <span>{String(activeIndex + 1).padStart(2, "0")} / {moments[activeIndex].label}</span>
                <p>{moments[activeIndex].description}</p>
            </div>
        </div>
    );
}

function InteractiveDemoSection() {
    return (
        <section className="demo-section" id="product-demo" aria-labelledby="demo-title">
            <div className="demo-section-inner">
                <div className="demo-section-intro">
                    <span className="landing-section-label">INSIDE THE REVIEW</span>
                    <h2 id="demo-title">See how WatchDemo<br /><em>breaks down a round.</em></h2>
                    <p>A prepared review shows how positioning, support and information can change a decision.</p>
                </div>
                <MiniDemoPlayer />
                <div className="mini-demo-after">
                    <span>A closer look changes the next play.</span>
                    <Link to="/upload">Analyze your own demo <span aria-hidden="true">↗</span></Link>
                </div>
            </div>
        </section>
    );
}

export default InteractiveDemoSection;

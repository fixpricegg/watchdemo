import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import BrandMark from "../components/BrandMark";
import WatchDemoIntro from "../components/WatchDemoIntro";
import HowItWorksSection from "../components/landing/HowItWorksSection";
import InteractiveDemoSection from "../components/landing/InteractiveDemoSection";
import ComparisonSection from "../components/landing/ComparisonSection";
import FinalCTA from "../components/landing/FinalCTA";
import LandingFooter from "../components/landing/LandingFooter";
import "./HomePage.css";

const INTRO_DATE_KEY = "watchdemo:intro:last-seen-date";

function localCalendarDate() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

function shouldPlayIntro() {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return false;
    

    try {
        return window.localStorage.getItem(INTRO_DATE_KEY) !== localCalendarDate();
    } catch {
        // The landing remains available if storage is blocked by the browser.
        return false;
    }
}

const features = [
    {
        number: "01",
        title: "Interactive radar",
        description: "Rewatch critical moments and understand positioning, timing and rotations.",
        asset: "/watchdemo-radar-preview.mp4",
        kind: "video",
    },
    {
        number: "02",
        title: "Mistake analysis",
        description: "Find the decisions that actually cost you rounds.",
        asset: "/watchdemo-analysis.webp",
        kind: "image",
    },
    {
        number: "03",
        title: "Actionable insights",
        description: "Turn match data into things you can improve in your next game.",
        asset: "/watchdemo-insights.webp",
        kind: "image",
    },
];

function LandingNav() {
    const [menuOpen, setMenuOpen] = useState(false);

    function closeMenu() {
        setMenuOpen(false);
    }

    return (
        <header className="landing-nav-wrap">
            <nav className="landing-nav" aria-label="Main navigation">
                <Link className="landing-logo" to="/" onClick={closeMenu} aria-label="WatchDemo home">
                    <BrandMark />
                    <span>WatchDemo</span>
                </Link>

                <button
                    className="landing-menu-toggle"
                    type="button"
                    aria-label={menuOpen ? "Close menu" : "Open menu"}
                    aria-expanded={menuOpen}
                    aria-controls="landing-navigation"
                    onClick={() => setMenuOpen((open) => !open)}
                >
                    <span /><span />
                </button>

                <div className={`landing-nav-panel${menuOpen ? " is-open" : ""}`} id="landing-navigation">
                    <div className="landing-nav-links">
                        <a href="#features" onClick={closeMenu}>Features</a>
                        <a href="#how-it-works" onClick={closeMenu}>How it works</a>
                        {/* TODO: Link to the pricing page when pricing is available. */}
                        <span className="landing-nav-unavailable" title="Pricing coming soon">Pricing</span>
                    </div>
                    <div className="landing-nav-actions">
                        {/* TODO: Link to the login route when authentication is available. */}
                        <span className="landing-nav-unavailable" title="Log in coming soon">Log in</span>
                        <Link to="/upload" className="landing-nav-cta" onClick={closeMenu}>
                            Analyze a demo <span aria-hidden="true">↗</span>
                        </Link>
                    </div>
                </div>
            </nav>
        </header>
    );
}

function HeroMedia() {
    const [videoReady, setVideoReady] = useState(false);

    return (
        <div className={`landing-hero-media${videoReady ? " has-video" : ""}`} aria-hidden="true">
            <div className="landing-hero-fallback" />
            {/* Add the finished cinematic film at frontend/public/watchdemo-hero.mp4. */}
            <video
                className="landing-hero-video"
                autoPlay
                muted
                loop
                playsInline
                preload="metadata"
                onCanPlay={() => setVideoReady(true)}
                onError={() => setVideoReady(false)}
            >
                <source src="/watchdemo-hero.mp4" type="video/mp4" />
            </video>
        </div>
    );
}

function FeatureMedia({ asset, kind }) {
    const [loaded, setLoaded] = useState(false);

    return (
        <div className={`landing-feature-media${kind === "video" ? " is-video" : ""}${loaded ? " has-asset" : ""}`} aria-hidden="true">
            {/* Replace these paths with captures from the actual WatchDemo interface. */}
            {kind === "video" ? (
                <video
                    autoPlay
                    muted
                    loop
                    playsInline
                    preload="metadata"
                    onCanPlay={() => setLoaded(true)}
                    onError={() => setLoaded(false)}
                >
                    <source src={asset} type="video/mp4" />
                </video>
            ) : (
                <img
                    src={asset}
                    alt=""
                    loading="lazy"
                    onLoad={() => setLoaded(true)}
                    onError={() => setLoaded(false)}
                />
            )}
            <span className="landing-media-fallback" />
        </div>
    );
}

function FeatureCard({ number, title, description, asset, kind }) {
    return (
        <article className="landing-feature-card">
            <FeatureMedia asset={asset} kind={kind} />
            <div className="landing-feature-copy">
                <span className="landing-feature-number">{number}</span>
                <h3>{title}</h3>
                <p>{description}</p>
            </div>
        </article>
    );
}

function HomePage() {
    const [showIntro, setShowIntro] = useState(shouldPlayIntro);

    useEffect(() => {
        try {
            window.localStorage.setItem(INTRO_DATE_KEY, localCalendarDate());
        } catch {
            // A blocked storage API should never block the landing page.
        }
    }, []);

    return (
        <>
            {showIntro && <WatchDemoIntro onComplete={() => setShowIntro(false)} />}
            <main className={`landing-page${showIntro ? " is-intro-playing" : ""}`} inert={showIntro}>
                <section className="landing-hero" aria-labelledby="landing-title">
                    <HeroMedia />
                    <div className="landing-hero-shade" aria-hidden="true" />
                    <LandingNav />

                    <div className="landing-hero-content">
                        <p className="landing-eyebrow">CS2 DEMO ANALYSIS</p>
                        <h1 id="landing-title">Understand why<br />you lose rounds<span>.</span></h1>
                        <p className="landing-hero-description">
                            WatchDemo turns your CS2 demos into clear, interactive analysis — showing where you made mistakes and why they mattered.
                        </p>
                        <div className="landing-hero-actions">
                            <Link to="/upload" className="landing-button landing-button-primary">Analyze a demo <span aria-hidden="true">↗</span></Link>
                            <a href="#how-it-works" className="landing-button landing-button-secondary">See how it works <span aria-hidden="true">↗</span></a>
                        </div>
                    </div>
                </section>

                <section className="landing-features" id="features" aria-labelledby="features-title">
                    <div className="landing-section-intro">
                        <h2 id="features-title"><span>Every match tells you</span><br />what happened.<br /><em>WatchDemo shows you why.</em></h2>
                        <p className="landing-section-description">Go beyond the scoreboard. Replay the moment, understand the decision, and know what to work on next.</p>
                    </div>
                    <div className="landing-feature-grid">
                        {features.map((feature) => <FeatureCard key={feature.number} {...feature} />)}
                    </div>
                </section>
                <HowItWorksSection />
                <InteractiveDemoSection />
                <ComparisonSection />
                <FinalCTA />
                <LandingFooter />
            </main>
        </>
    );
}

export default HomePage;

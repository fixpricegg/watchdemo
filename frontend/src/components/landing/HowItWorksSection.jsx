import "./HowItWorksSection.css";

const story = [
    "Upload your demo",
    "Reconstruct the match",
    "Review the moments that matter",
    "Understand the decision",
    "Improve the next game",
];

function StoryGroup({ duplicate = false }) {
    return (
        <ol className="story-group" aria-hidden={duplicate ? "true" : undefined}>
            {story.map((title, index) => (
                <li className="story-step" key={title}>
                    <span className="story-step-number">{String(index + 1).padStart(2, "0")}</span>
                    <span className="story-step-title">{title}</span>
                    <span className="story-step-arrow" aria-hidden="true">→</span>
                </li>
            ))}
        </ol>
    );
}

function HowItWorksSection() {
    return (
        <section className="story-section" id="how-it-works" aria-labelledby="story-title">
            <div className="story-heading">
                <span className="landing-section-label">HOW IT WORKS</span>
                <h2 id="story-title">From demo <em>to decision.</em></h2>
                <p>One match can change how you see the next one.</p>
            </div>
            <div className="story-marquee">
                <div className="story-track">
                    <StoryGroup />
                    <StoryGroup duplicate />
                </div>
            </div>
        </section>
    );
}

export default HowItWorksSection;

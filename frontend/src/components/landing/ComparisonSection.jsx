import "./ComparisonSection.css";

const traditional = ["ADR", "K/D", "HS%", "Entries"];
const review = [
    "First contact without support",
    "No immediate trade available",
    "Multiple enemy positions still possible",
    "Better timing available",
];

function ComparisonSection() {
    return (
        <section className="comparison-section" aria-labelledby="comparison-title">
            <div className="comparison-inner">
                <span className="landing-section-label">BEYOND THE SCOREBOARD</span>
                <h2 id="comparison-title"><span>Stats tell you the result.</span><br />WatchDemo explains<br />the decision.</h2>
                <div className="comparison-pair">
                    <div className="comparison-column comparison-stats">
                        <h3>Traditional stats</h3>
                        <p>What happened.</p>
                        <ul>{traditional.map((item) => <li key={item}>{item}</li>)}</ul>
                    </div>
                    <div className="comparison-column comparison-review">
                        <h3>WatchDemo review</h3>
                        <p>Why it happened.</p>
                        <ul>{review.map((item) => <li key={item}>{item}</li>)}</ul>
                    </div>
                </div>
            </div>
        </section>
    );
}

export default ComparisonSection;

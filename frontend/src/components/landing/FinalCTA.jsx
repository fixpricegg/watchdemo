import { Link } from "react-router-dom";

import "./FinalCTA.css";

function FinalCTA() {
    return (
        <section className="final-cta" aria-labelledby="final-cta-title">
            <div className="final-cta-inner">
                <span className="landing-section-label">THE NEXT ROUND STARTS HERE</span>
                <h2 id="final-cta-title">Your next match<br /><em>starts with your last one.</em></h2>
                <p>Review the decisions that mattered and take something useful into the next game.</p>
                <div className="final-cta-actions">
                    <Link to="/upload" className="landing-button landing-button-primary">Analyze a demo <span aria-hidden="true">↗</span></Link>
                    <a href="#how-it-works" className="landing-button landing-button-secondary">See how it works <span aria-hidden="true">↗</span></a>
                </div>
            </div>
        </section>
    );
}

export default FinalCTA;

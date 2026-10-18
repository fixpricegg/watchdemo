import { Link } from "react-router-dom";

import BrandMark from "../BrandMark";
import "./LandingFooter.css";

function LandingFooter() {
    return (
        <footer className="landing-footer">
            <div className="landing-footer-inner">
                <div className="landing-footer-brand">
                    <Link to="/" aria-label="WatchDemo home"><BrandMark /><span>WatchDemo</span></Link>
                    <p>Understand the round. Improve the next one.</p>
                </div>
                <nav className="landing-footer-links" aria-label="Footer navigation">
                    <div><h2>Product</h2><a href="#features">Features</a><a href="#how-it-works">How it works</a><span title="Pricing coming soon">Pricing</span></div>
                    <div><h2>Account</h2><span title="Log in coming soon">Log in</span><span title="Sign up coming soon">Sign up</span></div>
                    <div><h2>Other</h2><span title="Privacy page coming soon">Privacy</span><span title="Terms page coming soon">Terms</span></div>
                </nav>
                <div className="landing-footer-bottom"><span>© {new Date().getFullYear()} WatchDemo</span><a href="#landing-title">Back to top ↑</a></div>
            </div>
        </footer>
    );
}

export default LandingFooter;

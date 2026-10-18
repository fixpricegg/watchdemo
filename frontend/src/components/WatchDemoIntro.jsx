import { useEffect } from "react";

import BrandMark from "./BrandMark";
import "./WatchDemoIntro.css";

const INTRO_DURATION_MS = 2500;

function WatchDemoIntro({ onComplete }) {
    useEffect(() => {
        const timeout = window.setTimeout(onComplete, INTRO_DURATION_MS);
        return () => window.clearTimeout(timeout);
    }, [onComplete]);

    return (
        <div className="watchdemo-intro" role="status" aria-label="WatchDemo is opening">
            <div className="watchdemo-intro-lockup" aria-hidden="true">
                <BrandMark className="watchdemo-intro-mark" />
                <span className="watchdemo-intro-name">WatchDemo</span>
            </div>
        </div>
    );
}

export default WatchDemoIntro;

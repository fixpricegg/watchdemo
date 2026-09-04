import { Link } from "react-router-dom";


function HomePage() {
    return (
        <main className="upload-page">
            <section className="upload-card">
                <p className="upload-eyebrow">
                    WATCHDEMO
                </p>

                <h1>Understand your CS2 matches</h1>

                <p className="upload-description">
                    Upload your demo, review the match
                    and find the mistakes that actually matter.
                </p>

                <Link
                    to="/upload"
                    className="primary-button page-link"
                >
                    Analyze demo
                </Link>
            </section>
        </main>
    );
}


export default HomePage;
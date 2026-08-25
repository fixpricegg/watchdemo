import { Link, NavLink } from "react-router-dom";

import "./Header.css";


function Header() {
    return (
        <header className="site-header">
            <div className="site-header-inner">

                <Link
                    to="/"
                    className="site-logo"
                >
                    WatchDemo
                </Link>

                <nav className="site-nav">

                    <NavLink
                        to="/"
                        className={({ isActive }) =>
                            isActive
                                ? "site-nav-link active"
                                : "site-nav-link"
                        }
                    >
                        Home
                    </NavLink>

                    <NavLink
                        to="/upload"
                        className={({ isActive }) =>
                            isActive
                                ? "site-nav-link active"
                                : "site-nav-link"
                        }
                    >
                        Analyze
                    </NavLink>

                </nav>

            </div>
        </header>
    );
}


export default Header;
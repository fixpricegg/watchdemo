import { Fragment, useEffect, useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { fetchJSON } from "../api";

export default function AccountShell({ children }) {
    const [state, setState] = useState(null);
    const [error, setError] = useState("");
    const location = useLocation();
    const navigate = useNavigate();
    useEffect(() => {
        let active = true;
        fetchJSON("/auth/session").then((data) => { if (active) setState(data); })
            .catch((e) => { if (active) setError(e.message); });
        return () => { active = false; };
    }, []);
    if (!state) return <main><p role="status">{error || "Проверка сессии…"}</p><button onClick={() => window.location.reload()}>Повторить</button></main>;
    const page = location.pathname;
    const accountPage = ["/login", "/register", "/forgot-password", "/reset-password", "/profile"].includes(page);
    async function refresh() { setState(await fetchJSON("/auth/session")); }
    async function logout() {
        try { await fetchJSON("/auth/logout", { method: "POST" }); await refresh(); navigate("/login"); }
        catch (e) { setError(e.message); }
    }
    if (!state.user && !accountPage) return <Navigate to="/login" state={{ from: page }} replace />;
    if (!state.user && page === "/profile") return <Navigate to="/login" replace />;
    return <>
        <nav aria-label="Аккаунт">
            <Link to="/reports">Мои отчёты</Link>{" · "}
            {state.user ? <><Link to="/profile">{state.user.display_name}</Link>{" · "}<button onClick={logout}>Выйти</button></>
                : <><Link to="/login">Вход</Link>{" · "}<Link to="/register">Регистрация</Link></>}
        </nav>
        {error && <p role="alert">{error}</p>}
        {accountPage ? <AccountForm key={page} page={page} user={state.user} refresh={refresh} /> : <Fragment key={state.user?.id}>{children}</Fragment>}
    </>;
}

function AccountForm({ page, user, refresh }) {
    const [message, setMessage] = useState("");
    const [busy, setBusy] = useState(false);
    const navigate = useNavigate();
    const location = useLocation();
    const titles = { "/login": "Вход", "/register": "Регистрация", "/forgot-password": "Восстановление пароля", "/reset-password": "Новый пароль", "/profile": "Профиль" };
    async function submit(event, action) {
        event.preventDefault(); setBusy(true); setMessage("");
        const fields = Object.fromEntries(new FormData(event.currentTarget));
        let endpoint = action || page.slice(1);
        if (page === "/profile" && !action) endpoint = "profile";
        if (page === "/reset-password") fields.token = window.location.hash.slice(1);
        try {
            const data = await fetchJSON(`/auth/${endpoint}`, {
                method: endpoint === "profile" ? "PATCH" : "POST",
                headers: { "Content-Type": "application/json" }, body: JSON.stringify(fields),
            });
            setMessage(data.message || "Сохранено");
            if (endpoint === "login") { await refresh(); navigate(location.state?.from || "/reports", { replace: true }); }
            if (["profile", "password", "reset-password"].includes(endpoint)) await refresh();
            if (endpoint === "reset-password") window.history.replaceState(null, "", "/reset-password");
            event.target.reset();
        } catch (e) { setMessage(e.message); }
        finally { setBusy(false); }
    }
    const emailField = ["/login", "/register", "/forgot-password"].includes(page);
    return <main className="upload-page"><section className="upload-card">
        <h1>{titles[page]}</h1>
        {user && page === "/profile" && <p>Email: {user.email}</p>}
        <form onSubmit={submit}>
            {emailField && <p><label>Email <input name="email" type="email" autoComplete="email" required /></label></p>}
            {["/register", "/profile"].includes(page) && <p><label>Имя <input name="display_name" defaultValue={user?.display_name || ""} maxLength={80} required /></label></p>}
            {["/login", "/register", "/reset-password"].includes(page) && <p><label>Пароль (12–128 символов) <input name="password" type="password" minLength={12} maxLength={128} autoComplete={page === "/login" ? "current-password" : "new-password"} required /></label></p>}
            <button disabled={busy}>Продолжить</button>
        </form>
        {page === "/profile" && user && <form onSubmit={(e) => submit(e, "password")}>
            <h2>Изменить пароль</h2>
            <p><label>Текущий пароль <input name="old_password" type="password" autoComplete="current-password" required /></label></p>
            <p><label>Новый пароль <input name="password" type="password" minLength={12} maxLength={128} autoComplete="new-password" required /></label></p>
            <button disabled={busy}>Изменить пароль</button>
        </form>}
        {message && <p role="status">{message}</p>}
        <p><Link to="/login">Вход</Link>{" · "}<Link to="/register">Регистрация</Link>{" · "}<Link to="/forgot-password">Забыли пароль?</Link></p>
    </section></main>;
}

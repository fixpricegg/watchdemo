CREATE TABLE users (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL UNIQUE CHECK (email = lower(email)),
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE matches ADD COLUMN owner_id UUID REFERENCES users(id);
-- Enforce ownership for new writes without scanning or rewriting legacy rows.
ALTER TABLE matches ADD CONSTRAINT new_matches_require_owner
    CHECK (owner_id IS NOT NULL) NOT VALID;
CREATE INDEX matches_owner_created_idx ON matches(owner_id, created_at DESC);
-- NULL owners preserve legacy data, without granting access to any account.
CREATE TABLE sessions (
    token_hash TEXT PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    csrf_token TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX sessions_user_idx ON sessions(user_id);
CREATE TABLE password_resets (
    token_hash TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ
);
CREATE INDEX password_resets_user_idx ON password_resets(user_id);
CREATE TABLE auth_limits (
    key TEXT PRIMARY KEY,
    attempts INTEGER NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);
-- Provider subjects remain separate from passwords and session identity.
CREATE TABLE external_identities (
    provider TEXT NOT NULL,
    subject TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id),
    PRIMARY KEY(provider, subject),
    UNIQUE(user_id, provider)
);

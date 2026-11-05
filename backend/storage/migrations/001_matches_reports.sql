CREATE TABLE matches (
    id UUID PRIMARY KEY,
    original_filename TEXT NOT NULL,
    players JSONB NOT NULL CHECK (jsonb_typeof(players) = 'array'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE reports (
    id UUID PRIMARY KEY,
    match_id UUID NOT NULL REFERENCES matches(id),
    steamid TEXT NOT NULL,
    player_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('processing', 'completed', 'failed')),
    format_version INTEGER NOT NULL DEFAULT 1 CHECK (format_version = 1),
    map_name TEXT,
    result JSONB,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    CHECK (
        (status = 'processing' AND result IS NULL AND error IS NULL AND finished_at IS NULL)
        OR (status = 'completed' AND jsonb_typeof(result) = 'object'
            AND result IS NOT NULL AND error IS NULL AND finished_at IS NOT NULL)
        OR (status = 'failed' AND result IS NULL AND error IS NOT NULL AND finished_at IS NOT NULL)
    )
);

CREATE INDEX reports_match_created_idx ON reports (match_id, created_at DESC, id DESC);
CREATE INDEX reports_created_idx ON reports (created_at DESC, id DESC);

import "./Timeline.css";

function Timeline({
    radarData,
    tickIndex,
    setTickIndex,
    isPlaying,
    setIsPlaying,
}) {
    
    if (!radarData?.rounds?.length) {
        return null;
    }
    const rounds = radarData.rounds;
    const events = radarData.events || [];

    const masterTicks = (
        radarData.bomb?.states ?? []
    ).map((state) => state.tick);

    const currentTick =
        masterTicks[tickIndex] ??
        masterTicks[0];

    const timelineStartTick = rounds[0].freeze_start_tick;
    const timelineEndTick = rounds[rounds.length - 1].end_tick;
    const timelineLength = timelineEndTick - timelineStartTick;

    const currentRound = rounds.find(
        (round) =>
            currentTick >= round.freeze_start_tick &&
            currentTick < round.end_tick
    );

    let roundTime = "--:--";
    let roundPhase = "";

    if (currentRound) {
        if (currentTick < currentRound.live_start_tick) {
            const ticksLeft = currentRound.live_start_tick - currentTick;
            const secondsLeft = Math.max(0, Math.ceil(ticksLeft / 64));

            roundPhase = "Buy";
            roundTime = `0:${String(secondsLeft).padStart(2, "0")}`;
        } else {
            const ticksPassed = currentTick - currentRound.live_start_tick;
            const secondsPassed = Math.floor(ticksPassed / 64);
            const secondsLeft = Math.max(0, 115 - secondsPassed);

            const minutes = Math.floor(secondsLeft / 60);
            const seconds = String(secondsLeft % 60).padStart(2, "0");

            roundPhase = "Live";
            roundTime = `${minutes}:${seconds}`;
        }
    }

    const timelineProgress = Math.max(
        0,
        Math.min(
            100,
            ((currentTick - timelineStartTick) / timelineLength) * 100
        )
    );

    function getClosestTickIndex(targetTick) {
        if (masterTicks.length === 0) {
            return 0;
        }

        let left = 0;
        let right = masterTicks.length - 1;

        while (left <= right) {
            const middle = Math.floor(
                (left + right) / 2
            );

            const tick = masterTicks[middle];

            if (tick === targetTick) {
                return middle;
            }

            if (tick < targetTick) {
                left = middle + 1;
            } else {
                right = middle - 1;
            }
        }

        if (left >= masterTicks.length) {
            return masterTicks.length - 1;
        }

        if (right < 0) {
            return 0;
        }

        const leftDifference = Math.abs(
            masterTicks[left] - targetTick
        );

        const rightDifference = Math.abs(
            masterTicks[right] - targetTick
        );

        return leftDifference < rightDifference
            ? left
            : right;
    }

    function handleTimelineClick(event) {
        const rect = event.currentTarget.getBoundingClientRect();

        const clickProgress =
            (event.clientX - rect.left) / rect.width;

        const targetTick =
            timelineStartTick + clickProgress * timelineLength;

        setTickIndex(getClosestTickIndex(targetTick));
    }

    return (
        <section className="timeline-section">
            <div className="timeline-header">
                <h2>Timeline</h2>

                <div className="round-info">
                    <span>
                        CT {currentRound ? currentRound.ct_score : "-"}
                    </span>

                    <span className="match-score-separator">:</span>

                    <span>
                        {currentRound ? currentRound.t_score : "-"} T
                    </span>

                    <span>
                        Round {currentRound ? currentRound.round : "-"}
                    </span>

                    <span>{roundPhase}</span>

                    <span>{roundTime}</span>
                </div>
            </div>

            <div
                className="match-timeline"
                onClick={handleTimelineClick}
            >
                <div className="timeline-rounds">
                    {rounds.map((round) => (
                        <div
                            key={round.round}
                            className={`timeline-round ${
                                currentRound?.round === round.round
                                    ? "active-round"
                                    : ""
                            }`}
                            style={{
                                flex: round.end_tick - round.freeze_start_tick,
                            }}
                        >
                            <span>R{round.round}</span>
                        </div>
                    ))}
                </div>

                <div className="timeline-events">
                    {events.map((event, index) => {
                        if (event.tick === null) return null;

                        const left =
                            ((event.tick - timelineStartTick) /
                                timelineLength) * 100;

                        return (
                            <div
                                key={index}
                                className={`timeline-event ${event.category}`}
                                style={{
                                    left: `${left}%`,
                                }}
                                title={event.title}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setTickIndex(getClosestTickIndex(event.tick));
                                }}
                            />
                        );
                    })}
                </div>

                <div
                    className="timeline-progress"
                    style={{ width: `${timelineProgress}%` }}
                ></div>

                <div
                    className="timeline-handle"
                    style={{ left: `${timelineProgress}%` }}
                ></div>
            </div>

            <div className="timeline-controls">
                <button
                    onClick={() =>
                        setTickIndex((prev) => Math.max(0, prev - 8))
                    }
                >
                    ←
                </button>

                <button onClick={() => setIsPlaying(!isPlaying)}>
                    {isPlaying ? "Pause" : "Play"}
                </button>

                <button
                    onClick={() =>
                        setTickIndex((prev) =>
                            Math.min(
                                masterTicks.length - 1,
                                prev + 8
                            )
                        )
                    }
                >
                    →
                </button>
            </div>
        </section>
    );
}

export default Timeline;
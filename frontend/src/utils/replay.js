// Select only frames in the requested round. A nearest frame from another
// round is misleading at freeze/live boundaries.
export function findEpisodeFrame(states, rounds, episode) {
    if (!Number.isFinite(episode?.tick)) return null;
    const round = rounds.find((item) => item.round === episode.round);
    if (!round || episode.tick < round.freeze_start_tick || episode.tick >= round.end_tick) return null;
    let best = null;
    let difference = Infinity;
    states.forEach((state, index) => {
        if (state.tick < round.freeze_start_tick || state.tick >= round.end_tick) return;
        const distance = Math.abs(state.tick - episode.tick);
        if (distance < difference) {
            best = index;
            difference = distance;
        }
    });
    return best;
}

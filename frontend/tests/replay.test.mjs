import assert from 'node:assert/strict';
import test from 'node:test';
import { findEpisodeFrame } from '../src/utils/replay.js';

const rounds = [{round:1,freeze_start_tick:0,end_tick:100},{round:2,freeze_start_tick:100,end_tick:200}];
const states = [{tick:96},{tick:112},{tick:144},{tick:192}];

test('seeking at round boundaries never borrows a frame from another round', () => {
    assert.equal(findEpisodeFrame(states, rounds, {round:1,tick:99}), 0);
    assert.equal(findEpisodeFrame(states, rounds, {round:2,tick:101}), 1);
});
test('the closest frame in the requested round is selected', () => {
    assert.equal(findEpisodeFrame(states, rounds, {round:2,tick:140}), 2);
});
test('missing frames, invalid ticks and out-of-round ticks are unavailable', () => {
    assert.equal(findEpisodeFrame(states, rounds, {round:2,tick:200}), null);
    assert.equal(findEpisodeFrame(states, rounds, {round:3,tick:140}), null);
    assert.equal(findEpisodeFrame([], rounds, {round:1,tick:99}), null);
    assert.equal(findEpisodeFrame(states, rounds, {round:1,tick:NaN}), null);
});

// Pure UI fixtures; no browser, video, network, or real annotation writes.
const fs = require('node:fs');
const vm = require('node:vm');
const test = require('node:test');
const assert = require('node:assert/strict');

function fixture() {
  const calls = [];
  const drawing = {};
  for (const name of ['strokeRect', 'setLineDash', 'beginPath', 'moveTo', 'lineTo', 'closePath', 'stroke', 'fillText']) {
    drawing[name] = (...args) => calls.push([name, ...args]);
  }
  const elements = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, {style: {}, value: '', checked: false, naturalWidth: 1000,
      naturalHeight: 500, videoWidth: 1000, videoHeight: 500, getContext: () => drawing,
      addEventListener() {}, append() {}, replaceChildren() {}});
    return elements.get(id);
  }
  const context = vm.createContext({document: {getElementById: element, createElement: element, addEventListener() {}},
    localStorage: {length: 0, getItem: () => null, setItem() {}}, console, setTimeout() {}});
  const html = fs.readFileSync('counting/review.html', 'utf8');
  const code = html.match(/<script>([\s\S]*?)<\/script>/)[1].replace(/init\(\);\s*$/, '');
  vm.runInContext(code, context);
  return {context, calls};
}

const base = {source_video_sha256: 'SOFTWARE_FIXTURE', video_id: 'fixture', session_id: 'fixture',
  reviewed_interval: {start_frame0: 0, end_frame0: 10},
  review_gate: {axis: 'y', perpendicular_roi: [0, 1], lower: .4, upper: .6}};
const polygon = [[.2, 0], [.4, 0], [.8, 1], [.2, 1]];

test('legacy draft identities retain their original fields', () => {
  const {context} = fixture();
  const expected = ['SOFTWARE_FIXTURE', 'fixture', 0, 10, 'y', [0, 1], .4, .6, 'torso-center-zones-source-pts-v1'];
  assert.equal(context.reviewIdentity(base), JSON.stringify(expected));
});

test('physical polygon changes create different draft identities', () => {
  const {context} = fixture();
  const a = {...base, review_gate: {...base.review_gate, channel_polygon: polygon}};
  const b = {...base, review_gate: {...base.review_gate, channel_polygon: [[.1, 0], [.9, 0], [.9, 1], [.1, 1]]}};
  assert.notEqual(context.reviewIdentity(a), context.reviewIdentity(b));
  assert.notEqual(context.reviewIdentity(a), context.reviewIdentity(base));
});

test('perspective boundary and gate endpoints follow polygon vertices', () => {
  const {context, calls} = fixture();
  context.fixtureMeta = {...base, review_gate: {...base.review_gate, channel_polygon: polygon}};
  vm.runInContext('meta=fixtureMeta; redraw();', context);
  assert.equal(calls.filter(c => c[0] === 'strokeRect').length, 0);
  assert.equal(calls.filter(c => c[0] === 'closePath').length, 1);
  for (const [x, y] of [[560, 200], [640, 300]]) {
    assert.ok(calls.some(c => c[0] === 'lineTo' && Math.abs(c[1] - x) < 1e-7 && Math.abs(c[2] - y) < 1e-7));
  }
});

test('concave polygon gates do not bridge an excluded notch', () => {
  const {context} = fixture();
  const gate = {...base.review_gate, channel_polygon: [[.1, .1], [.9, .1], [.9, .9], [.6, .9], [.6, .4], [.4, .4], [.4, .9], [.1, .9]]};
  const actual = JSON.parse(JSON.stringify(context.channelSegments(gate, .6)));
  assert.deepEqual(actual, [[[.1, .6], [.4, .6]], [[.6, .6], [.9, .6]]]);
});

test('polygon mode cannot import an old unbound-region draft', () => {
  const {context} = fixture();
  const saved = {items: [], uncertain: [], entry: null};
  const meta = {...base, review_gate: {...base.review_gate, channel_polygon: polygon}};
  assert.equal(context.legacyCompatible(saved, meta, true), false);
  assert.equal(context.legacyCompatible(saved, base, true), true);
});

test('collinear outer boundary is not drawn as an interior gate', () => {
  const {context} = fixture();
  const poly = [[.2, .2], [.8, .2], [.8, .8], [.2, .8]];
  for (const axis of ['x', 'y']) {
    const actual = JSON.parse(JSON.stringify(context.channelSegments({...base.review_gate, axis, channel_polygon: poly}, .2)));
    assert.deepEqual(actual, []);
  }
});

test('collinear notch boundary is removed while both real side intervals remain', () => {
  const {context} = fixture();
  const poly = [[.1, .1], [.4, .1], [.4, .6], [.6, .6], [.6, .1], [.9, .1], [.9, .9], [.1, .9]];
  const actual = JSON.parse(JSON.stringify(context.channelSegments({...base.review_gate, channel_polygon: poly}, .6)));
  assert.deepEqual(actual, [[[.1, .6], [.4, .6]], [[.6, .6], [.9, .6]]]);
});

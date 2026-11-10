/*
 * Read-only reproductions of the Standards review findings.
 * Run: node standards_review_repro.js [git-ref]
 * Default: current working tree. Pass a frozen Git ref to reproduce old failures.
 * Optional git-ref allows the same checks against a later committed repair.
 * Uses only Node built-ins, a small DOM fixture, and git show; no real media,
 * browser, board, network, repository edits, or localStorage deletion.
 */
'use strict';

const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const { createHash } = require('node:crypto');
const path = require('node:path');
const vm = require('node:vm');

const repo = path.join(__dirname, '..');
const ref = process.argv[2] || null;
const commit = ref ? execFileSync('git', ['rev-parse', `${ref}^{commit}`], {cwd:repo,encoding:'utf8'}).trim() : 'WORKTREE';
const html = ref ? execFileSync('git', ['show', `${commit}:counting/review.html`], {cwd:repo,encoding:'utf8'}) : require('node:fs').readFileSync(path.join(__dirname,'review.html'),'utf8');
const inlineScript = html.match(/<script>([\s\S]*?)<\/script>/)[1];
// Tests invoke init explicitly when needed, without automatic polling.
assert.match(inlineScript, /init\(\);\s*$/);
const script = inlineScript.replace(/init\(\);\s*$/, '');

function metadata(extra = {}) {
  return {
    source_video_sha256: 'SAME_SOURCE_HASH',
    source_integrity_verified: true,
    video_id: 'fixture-video',
    session_id: 'sessionA',
    source_fps: 25,
    source_frame_times_s: Array.from({ length: 501 }, (_, i) => i / 25),
    reviewed_interval: { start_frame0: 0, end_frame0: 500 },
    review_gate: { axis: 'y', perpendicular_roi: [.34, .75], lower: .4, upper: .6 },
    ...extra,
  };
}

function fixture(meta, storage = new Map()) {
  const nodes = new Map();
  const boundaryPaths = [];
  let currentPath = [];
  const drawing = {
    strokeRect() {}, setLineDash() {}, fillText() {},
    beginPath() { currentPath = []; },
    moveTo(x, y) { currentPath.push([x, y]); },
    lineTo(x, y) { currentPath.push([x, y]); },
    stroke() { boundaryPaths.push(currentPath); },
  };
  function element() {
    let currentTime = 0;
    return {
      value: '', textContent: '', style: {}, checked: false,
      paused: true, seeking: false, readyState: 2,
      videoWidth: 100, videoHeight: 100, naturalWidth: 100, naturalHeight: 100,
      get currentTime() { return currentTime; },
      set currentTime(value) { currentTime = value; this.seeking = true; },
      // Deliberately do not dispatch seeked/onload: the frame is not ready.
      pause() { this.paused = true; },
      append() {}, replaceChildren() {}, listeners: {}, addEventListener(name,fn) { this.listeners[name]=fn; },
      getContext() { return drawing; },
    };
  }
  const sandbox = {
    document: {
      getElementById(id) {
        if (!nodes.has(id)) nodes.set(id, element());
        return nodes.get(id);
      },
      createElement: element,
      addEventListener() {},
    },
    localStorage: {
      getItem(key) { return storage.get(key) ?? null; },
      setItem(key, value) { storage.set(key, value); },
    },
    fetch: async (url) => {
      assert.equal(url, '/metadata.json', 'This fixture never fetches media');
      return { json: async () => meta };
    },
    setTimeout() {},
  };
  const context = vm.createContext(sandbox);
  vm.runInContext(script, context, { filename: `${commit}:counting/review.html` });
  // Supply metadata without invoking asynchronous frame decode.
  context.fixtureMetadata = meta;
  vm.runInContext('meta=fixtureMetadata;', context);
  return {
    boundaryPaths,
    run: (code) => vm.runInContext(code, context),
    snapshot: (expression) => JSON.parse(vm.runInContext(`JSON.stringify(${expression})`, context)),
  };
}

const cases = [
  ['native_video_controls_lock_until_seeked', async () => {
    const f=fixture(metadata());
    f.run('frameMode=false;frameLoading=false;entry=null;v.seeking=true;v.listeners.seeking?.();markEntry();');
    return {actual:f.snapshot('entry'),expected:null};
  }],
  ['annotation_uses_actual_source_pts_not_frame_div_fps', async () => {
    const f=fixture(metadata());
    f.run('frameMode=true;frameLoading=false;cursorFrame=100;sourceTime=7.321;markEntry();cursorFrame=110;sourceTime=7.9;selectedPosition={source_frame0:110,x:50,y:70};complete("A->B");');
    return {actual:f.snapshot('[items[0].entry_time_s,items[0].time_s]'),expected:[7.321,7.9]};
  }],
  ['video_seek_blocks_annotation_before_seeked', async () => {
    const f = fixture(metadata());
    f.run('frameMode=false;frameLoading=false;entry=null;seek(100);markEntry();');
    const evidence = f.snapshot('({frameLoading,entry,reportedFrame:frame(),videoSeeking:v.seeking})');
    return { actual: evidence.entry, expected: null, evidence };
  }],
  ['review_overlay_uses_configured_gate', async () => {
    // Same domain fields as counting config, carried in review template metadata.
    const gate = { axis: 'x', perpendicular_roi: [.2, .8], lower: .25, upper: .75 };
    const f = fixture(metadata({ review_gate: gate }));
    f.run('redraw();');
    const expected = [[[25, 20], [25, 80]], [[75, 20], [75, 80]]];
    return { actual: f.boundaryPaths, expected, evidence: { configuredGate: gate } };
  }],
  ['different_session_and_interval_do_not_auto_load_old_draft', async () => {
    const oldEvent = {
      event_id: 'old-event', video_id: 'fixture-video', session_id: 'sessionA',
      direction: 'A->B', entry_source_frame0: 10, completion_source_frame0: 20,
    };
    const oldKey = 'cow-source-review:SAME_SOURCE_HASH';
    const oldValue = JSON.stringify({ items: [oldEvent], uncertain: [], entry: null, reviewer: 'A' });
    const storage = new Map([[oldKey, oldValue]]);
    const fresh = metadata({
      session_id: 'sessionB', reviewed_interval: { start_frame0: 100, end_frame0: 200 },
      // Skip media loading; draft restoration happens before integrity readiness.
      source_integrity_verified: false, downloaded_bytes: 0,
    });
    const f = fixture(fresh, storage);
    await f.run('init();');
    assert.equal(storage.get(oldKey), oldValue, 'Old draft must remain recoverable');
    const evidence = f.snapshot('({storeKey,currentSession:meta.session_id,currentScope:meta.reviewed_interval,loadedEvents:items})');
    return { actual: evidence.loadedEvents, expected: [], evidence };
  }],
];

(async () => {
  const results = [];
  for (const [name, test] of cases) {
    let detail;
    try {
      detail = await test();
      assert.deepStrictEqual(detail.actual, detail.expected);
      results.push({ name, status: 'PASS', ...detail });
    } catch (error) {
      results.push({ name, status: 'FAIL', ...detail, error: error.message });
    }
  }
  const failed = results.filter((result) => result.status === 'FAIL').length;
  process.stdout.write(JSON.stringify({
    reviewed_commit: commit,
    review_html_sha256: createHash('sha256').update(html).digest('hex'),
    fixture_only: true,
    no_real_video_or_board_access: true,
    tests: results.length, passed: results.length - failed, failed, results,
  }, null, 2) + '\n');
  process.exitCode = failed ? 1 : 0;
})().catch((error) => {
  process.stderr.write(error.stack + '\n');
  process.exitCode = 2;
});

// Exercise release-please's real composite updates, using the repository config.
// https://github.com/googleapis/release-please/blob/v17.3.0/src/strategies/base.ts
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
require('release-please'); // Initialize the package before loading strategy internals.
const {Python} = require('release-please/build/src/strategies/python');
const {Version} = require('release-please/build/src/version');
const root = process.env.JUDGEVET_RELEASE_ROOT || path.resolve(__dirname, '../..');
const config = JSON.parse(fs.readFileSync(path.join(root, 'release-please-config.json'))).packages['.'];

for (const target of ['0.10.0', '1.2.3', '2.0.0-rc.1']) {
  test(`configured updater synchronizes every registry version to ${target}`, async () => {
    const strategy = new Python({
      github: {}, targetBranch: 'main', path: '.', extraFiles: config['extra-files'],
    });
    const updates = await strategy.extraFileUpdates(Version.parse(target), new Map());
    const original = fs.readFileSync(path.join(root, 'server.json'), 'utf8');
    let content = original;
    for (const update of updates.filter(u => u.path === 'server.json')) {
      content = update.updater.updateContent(content);
    }
    const manifest = JSON.parse(content);
    assert.equal(manifest.version, target);
    assert.equal(manifest.packages[0].version, target);
    assert.equal(manifest.packages[0].runtimeArguments[0].variables.version.value, target);
    // Identity, credentials and argv structure must survive version updates.
    const before = JSON.parse(original);
    before.version = target;
    before.packages[0].version = target;
    before.packages[0].runtimeArguments[0].variables.version.value = target;
    assert.deepEqual(manifest, before);
  });
}

for (const target of ['0.10.1', '0.11.0', '1.2.3', '2.0.0-rc.1']) {
  test(`configured updater synchronizes only host recipe pins to ${target}`, async () => {
    const strategy = new Python({
      github: {}, targetBranch: 'main', path: '.', extraFiles: config['extra-files'],
    });
    const updates = await strategy.extraFileUpdates(Version.parse(target), new Map());
    const page = 'docs/how-to/connect-mcp.md';
    const original = fs.readFileSync(path.join(root, page), 'utf8');
    const pin = /\b(judgevet(?:\[mcp\])?==)\d+\.\d+\.\d+(?:-[\w.]+)?/g;
    const pins = [...original.matchAll(pin)];
    assert.ok(pins.length > 0, 'host recipes must retain explicit package pins');
    const expected = original.replace(pin, (_, requirement) => requirement + target);
    let content = original;
    for (const update of updates.filter(u => u.path === page)) {
      content = update.updater.updateContent(content);
    }
    assert.equal(content, expected, 'all pins change; every other byte survives');
  });
}

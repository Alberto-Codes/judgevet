const assert = require('node:assert/strict');
const test = require('node:test');
const {run} = require('./runner.cjs');

function boundary(releases, prs) {
  const calls = [];
  const outputs = {};
  const github = {};
  const api = {
    GitHub: {create: async options => {calls.push(['github', options]); return github;}},
    Manifest: {fromManifest: async (...args) => {
      calls.push(['manifest', ...args]);
      const count = calls.filter(call => call[0] === 'manifest').length;
      return count === 1
        ? {createReleases: async () => {calls.push(['releases']); return releases;}}
        : {createPullRequests: async () => {calls.push(['prs']); return prs;}};
    }},
  };
  const input = {token:'test-token', repository:'Alberto-Codes/judgevet',
    setOutput: (name, value) => {outputs[name] = value;}};
  return {api, input, calls, outputs, github};
}

test('delegate to fresh manifests and preserve consumed release/PR outputs', async () => {
  const pr = {headBranchName:'release-please--branches--main--components--judgevet'};
  const b = boundary([undefined, {path:'.', tagName:'v0.10.0', uploadUrl:'upload'}], [undefined, pr]);
  await run(b.input, b.api);
  assert.deepEqual(b.calls.map(call => call[0]), ['github','manifest','releases','manifest','prs']);
  assert.deepEqual(b.calls[0][1], {owner:'Alberto-Codes', repo:'judgevet', token:'test-token', defaultBranch:'main'});
  for (const call of b.calls.filter(call => call[0] === 'manifest')) {
    assert.deepEqual(call.slice(1), [b.github, 'main', 'release-please-config.json', '.release-please-manifest.json']);
  }
  assert.deepEqual(b.outputs, {releases_created:true, paths_released:['.'],
    release_created:true, tag_name:'v0.10.0', upload_url:'upload', prs_created:true, pr, prs:[pr]});
});

test('empty engine results do not signal a release or lockfile update', async () => {
  const b = boundary([undefined], [undefined]);
  await run(b.input, b.api);
  assert.deepEqual(b.outputs, {releases_created:false, paths_released:[], prs_created:false});
});

for (const input of [{token:'', repository:'Alberto-Codes/judgevet'},
  {token:'test-token', repository:'invalid'}]) {
  test(`invalid ${input.token ? 'repository' : 'credential'} makes no API call`, async () => {
    const b = boundary([], []);
    await assert.rejects(run({...b.input, ...input}, b.api), /required/);
    assert.deepEqual(b.calls, []);
  });
}

test('release failure propagates and prevents PR creation', async () => {
  const b = boundary([], []);
  b.api.Manifest.fromManifest = async () => ({createReleases:async () => {throw new Error('failure');}});
  await assert.rejects(run(b.input, b.api), /failure/);
  assert.deepEqual(b.outputs, {});
});

for (const fails of [false, true]) {
  test(`actual workflow script delegates and sanitizes failure=${fails}`, async () => {
    const fs = require('node:fs');
    const path = require('node:path');
    const yaml = require('yaml');
    const workflow = yaml.parse(fs.readFileSync(path.resolve(__dirname,
      '../../.github/workflows/release-please.yml'), 'utf8'));
    const step = workflow.jobs['release-please'].steps.find(step => step.id === 'release');
    assert.equal(step.env.GH_TOKEN, '${{ secrets.RELEASE_PLEASE_TOKEN }}');
    assert.equal(step.with['github-token'], '${{ secrets.RELEASE_PLEASE_TOKEN }}');
    const outputs = {};
    const errors = [];
    let invoked = false;
    const load = name => {
      assert.equal(name, './scripts/release_config/runner.cjs');
      return {run: async input => {
        invoked = true;
        assert.equal(input.token, 'private-canary');
        assert.equal(input.repository, 'Alberto-Codes/judgevet');
        if (fails) throw new Error('private-canary');
        input.setOutput('prs_created', true);
      }};
    };
    const AsyncFunction = Object.getPrototypeOf(async function() {}).constructor;
    await new AsyncFunction('require', 'process', 'core', step.with.script)(load,
      {env:{GH_TOKEN:'private-canary', GITHUB_REPOSITORY:'Alberto-Codes/judgevet'}},
      {setOutput:(name, value) => {outputs[name] = value;}, setFailed:message => errors.push(message)});
    assert.equal(invoked, true);
    assert.deepEqual(outputs, fails ? {} : {prs_created:true});
    assert.equal(errors.length, fails ? 1 : 0);
    assert.ok(!JSON.stringify(errors).includes('private-canary'));
  });
}

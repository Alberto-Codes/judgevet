const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
test.before(() => require('./runner.cjs').registerReferences());
require('release-please');
const {parseConventionalCommits} = require('release-please/build/src/commit');
const {buildChangelogNotes} = require('release-please/build/src/factories/changelog-notes-factory');
const root = process.env.JUDGEVET_RELEASE_ROOT || path.resolve(__dirname, '../..');
const config = JSON.parse(fs.readFileSync(path.join(root, 'release-please-config.json'))).packages['.'];
const historical = require('./reference-fixtures.json');
const {DefaultChangelogNotes} = require('release-please/build/src/changelog-notes/default');
const cases = [
  {label:'Closes-only', sha:'a'.repeat(40), message:'fix: show closes keyword literally\n\nCloses #123', issues:[123]},
  {label:'Refs-only', sha:'b'.repeat(40), message:'fix: retain a follow-up reference\n\nRefs #124', issues:[124]},
  {label:'mixed CLI regression', ...historical[0], issues:[123,124]},
  {label:'mixed backlog regression', ...historical[1], issues:[34,22,19,3,27,43,67,68,8,124]},
];
for (const fixture of cases) {
  test(`neutral generated references: ${fixture.label}`, async () => {
    const commits = parseConventionalCommits([fixture]);
    const messages = commits.map(c=>c.message);
    const actions = commits.map(c=>c.references.map(r=>r.action));
    const renderer = buildChangelogNotes({type:config['changelog-type'] || 'default', github:{}});
    const options = {
      owner:'Alberto-Codes', repository:'judgevet', version:'0.10.0',
      previousTag:'v0.9.0', currentTag:'v0.10.0', targetBranch:'main',
      changelogSections:config['changelog-sections'],
    };
    const notes = await renderer.buildNotes(commits, options);
    const original = await new DefaultChangelogNotes().buildNotes(
      parseConventionalCommits([fixture]), options);
    assert.equal(notes, original.replaceAll(', closes [', ', references ['));
    assert.match(notes, /, references \[/);
    assert.doesNotMatch(notes, /, closes \[/);
    for (const issue of fixture.issues) {
      assert.ok(notes.includes(`[#${issue}](https://github.com/Alberto-Codes/judgevet/issues/${issue})`));
    }
    assert.ok(notes.includes(`/commit/${fixture.sha}`));
    if (fixture.label === 'Closes-only') assert.ok(notes.includes('show closes keyword literally'));
    assert.deepEqual(commits.map(c=>c.message), messages);
    assert.deepEqual(commits.map(c=>c.references.map(r=>r.action)), actions);
  });
}

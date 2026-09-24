// Keep release state and version decisions in the pinned release-please engine.
const presetFactory = require('conventional-changelog-conventionalcommits');
const engine = require('release-please');
const {DefaultChangelogNotes} = require('release-please/build/src/changelog-notes/default');

async function registerReferences() {
  const {writerOpts} = await presetFactory({});
  const template = writerOpts.commitPartial;
  if (template.split(', closes').length !== 2) {
    throw new Error('Upstream reference template changed');
  }
  const commitPartial = template.replace(', closes', ', references');
  engine.registerChangelogNotes('default', options =>
    new DefaultChangelogNotes({...options, commitPartial}));
}

async function run({token, repository, setOutput}, api = engine) {
  if (!token || !/^[^/]+\/[^/]+$/.test(repository || '')) {
    throw new Error('Release token and owner/repository are required');
  }
  await registerReferences();
  const [owner, repo] = repository.split('/');
  const github = await api.GitHub.create({owner, repo, token, defaultBranch: 'main'});
  const load = () => api.Manifest.fromManifest(github, 'main',
    'release-please-config.json', '.release-please-manifest.json');
  const releases = (await (await load()).createReleases()).filter(Boolean);
  setOutput('releases_created', releases.length > 0);
  setOutput('paths_released', releases.map(release => release.path));
  for (const release of releases) {
    if (release.path !== '.') throw new Error('Unexpected release package path');
    setOutput('release_created', true);
    setOutput('tag_name', release.tagName);
    setOutput('upload_url', release.uploadUrl);
  }
  const prs = (await (await load()).createPullRequests()).filter(Boolean);
  setOutput('prs_created', prs.length > 0);
  if (prs.length) {
    setOutput('pr', prs[0]);
    setOutput('prs', prs);
  }
}

module.exports = {registerReferences, run};

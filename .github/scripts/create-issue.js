async function run(github, context) {
  const fs = require('fs');
  const path = 'inventionguard_report.json';
  if (!fs.existsSync(path)) return;
  const raw = fs.readFileSync(path, 'utf8');
  if (!raw.trim()) return;
  let results;
  try { results = JSON.parse(raw); } catch (e) { return; }
  if (!Array.isArray(results) || results.length === 0) return;
  for (const r of results) {
    const detection = r.detection || {};
    const synthesis = r.synthesis || {};
    const title = `\ud83e\udde0 Potential Invention Detected: ${detection.technical_problem?.substring(0, 80) || 'Unknown'}`;
    const body = `**Disclaimer:** This tool identifies potential technical inventions. It does not provide legal advice. Consult a patent attorney. AI cannot be a co-inventor.

**Commit:** ${r.commit_hash}
**Novelty Score:** ${detection.novelty_score} (${detection.novelty_assessment})
**Risk Assessment:** ${synthesis.risk_assessment}
**Similarity Score:** ${synthesis.overall_similarity_score}%
**Closest Prior Art:** ${synthesis.closest_patent?.patent_number || 'N/A'} — ${synthesis.closest_patent?.title || 'N/A'}

## Draft Independent Claim
> ${synthesis.draft_independent_claim || 'N/A'}

## Recommendation
${synthesis.recommendation || 'N/A'}
`;
    await github.rest.issues.create({
      owner: context.repo.owner,
      repo: context.repo.repo,
      title,
      body,
      labels: ['inventionguard', 'patent-review']
    });
  }
}
module.exports = run;

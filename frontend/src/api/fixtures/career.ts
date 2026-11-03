import type { GapCoach, MatchResult } from '../../types/api'

export const matchFixture: MatchResult = {
  status: 'ok', score: 67, matched_count: 2, assessable_count: 3,
  matched: [
    { name: 'Python', accepted_languages: ['Python', 'Jupyter Notebook'], evidence: [{ repo: 'data-tools', url: 'https://github.com/octocat/data-tools', language: 'Python' }] },
    { name: 'Go', accepted_languages: ['Go'], evidence: [{ repo: 'api-server', url: 'https://github.com/octocat/api-server', language: 'Go' }] },
  ],
  missing: [{ name: 'Java', accepted_languages: ['Java'] }],
  unassessable: ['AWS', 'Kubernetes'],
  explanation: 'Matched 2 of 3 assessable technologies: score = round(100 × 2 / 3) = 67%. AWS and Kubernetes cannot be verified from repository languages and are excluded. Language coverage does not establish proficiency.',
}

export const noKeywordsFixture: MatchResult = {
  status: 'no_assessable_keywords', score: null, matched_count: 0, assessable_count: 0,
  matched: [], missing: [], unassessable: ['AWS', 'Kubernetes'],
  explanation: 'Not enough assessable keywords. AWS and Kubernetes cannot be assessed using public repository languages. No score is available.',
}

export const zeroMatchFixture: MatchResult = {
  status: 'ok', score: 0, matched_count: 0, assessable_count: 1,
  matched: [], missing: [{ name: 'Java', accepted_languages: ['Java'] }], unassessable: [],
  explanation: 'Matched 0 of 1 assessable technologies: score = round(100 × 0 / 1) = 0%. No public Java repository evidence was found.',
}

export const coachFixture: GapCoach = {
  status: 'ok', score: 67,
  strengths: [{ name: 'Python', summary: 'Python appears in 3 of your public repos (largest: data-tools).', evidence: [{ repo: 'data-tools', url: 'https://github.com/octocat/data-tools', language: 'Python' }] }, { name: 'Go', summary: 'Go appears in api-server.', evidence: [{ repo: 'api-server', url: 'https://github.com/octocat/api-server', language: 'Go' }] }],
  missing: ['Java'], unassessable: ['AWS', 'Kubernetes'],
  highlight_repos: [{ name: 'data-tools', url: 'https://github.com/octocat/data-tools', stars: 120, matched_languages: ['Python'], reason: 'Uses Python; 120 stars.' }, { name: 'api-server', url: 'https://github.com/octocat/api-server', stars: 51, matched_languages: ['Go'], reason: 'Uses Go; 51 stars.' }],
  pitch: ['My public GitHub shows work in Python and Go, 2 of the 3 technologies this role lists that can be checked.', 'The clearest examples are data-tools and api-server.', 'I do not have public work in Java yet and would be upfront about that.'],
  disclaimer: 'Language coverage shows that code in a language exists in public repositories; it does not prove proficiency.',
}

export const noKeywordsCoachFixture: GapCoach = {
  status: 'no_assessable_keywords', score: null, strengths: [], missing: [], highlight_repos: [],
  unassessable: ['AWS', 'Kubernetes'],
  pitch: ['There are not enough assessable keywords to compare this role with repository languages.', 'AWS and Kubernetes cannot be verified from language data.', 'I would share direct project examples to discuss those requirements.'],
  disclaimer: coachFixture.disclaimer,
}

export const zeroCoachFixture: GapCoach = {
  status: 'ok', score: 0, strengths: [], missing: ['Java'], highlight_repos: [], unassessable: [],
  pitch: ['My public GitHub does not currently show Java language evidence.', 'I would use other project examples to describe my experience honestly.', 'A public Java project could provide evidence for this requirement.'],
  disclaimer: coachFixture.disclaimer,
}

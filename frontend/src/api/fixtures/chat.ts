import type { ChatResponse } from '../../types/api'

export const chatSuggestions = ['What are my top languages?', 'Which are my best repos?', 'What is my current streak?', 'What is my match score?', 'What are my gaps?', 'How can I improve my portfolio?']

export const chatFixtures: Record<string, ChatResponse> = {
  'How can I improve my portfolio?': { intent: 'portfolio_health', answer: 'Your portfolio presentation score is 100/100. There are no recommended actions in this snapshot. This measures presentation and activity, not code quality or skill.', evidence: [{ label: 'Portfolio presentation', value: '100/100', url: null }], suggestions: chatSuggestions },
  'What are my top languages?': { intent: 'top_languages', answer: 'Your top languages by code size are Python (48%), TypeScript (32%) and Other (20%).', evidence: [{ label: 'Python', value: '48% · 120000 bytes', url: null }, { label: 'TypeScript', value: '32% · 80000 bytes', url: null }, { label: 'Other', value: '20% · 50000 bytes', url: null }], suggestions: chatSuggestions },
  'Which are my best repos?': { intent: 'best_repos', answer: 'Your most starred public repositories are data-tools (120 stars), ui-toolkit (82 stars), and api-server (51 stars).', evidence: [{ label: 'data-tools', value: '120 stars', url: 'https://github.com/octocat/data-tools' }, { label: 'ui-toolkit', value: '82 stars', url: 'https://github.com/octocat/ui-toolkit' }, { label: 'api-server', value: '51 stars', url: 'https://github.com/octocat/api-server' }], suggestions: chatSuggestions },
  'What is my current streak?': { intent: 'streaks', answer: 'Your current streak is 2 days. Your longest streak is 10 days.', evidence: [{ label: 'Current streak', value: '2 days', url: null }, { label: 'Longest streak', value: '10 days', url: null }], suggestions: chatSuggestions },
  'What is my match score?': { intent: 'match_score', answer: 'There is no saved job description yet. Analyze a job description in Career match first.', evidence: [], suggestions: chatSuggestions },
  'What are my gaps?': { intent: 'gaps', answer: 'There is no saved job description yet. Analyze a job description in Career match to see missing language evidence.', evidence: [], suggestions: chatSuggestions },
}

export const unknownChatFixture: ChatResponse = { intent: 'unknown', answer: 'I can help explain top languages, best repositories, contribution streaks, saved match score, and gaps. Choose one of the suggested questions to explore this sample portfolio.', evidence: [], suggestions: chatSuggestions }

export const savedChatFixtures: Record<string, Record<string, ChatResponse>> = {
  '67': {
    'What is my match score?': { intent: 'match_score', answer: 'Your saved job description matches 2 of 3 assessable technologies, for a 67% language coverage score.', evidence: [{ label: 'Language coverage', value: '67% · 2 of 3 assessable technologies', url: null }], suggestions: chatSuggestions },
    'What are my gaps?': { intent: 'gaps', answer: 'Java is missing from your public repository language evidence. AWS and Kubernetes cannot be assessed from repository languages.', evidence: [{ label: 'Missing', value: 'Java', url: null }, { label: 'Unassessable', value: 'AWS, Kubernetes', url: null }], suggestions: chatSuggestions },
  },
  '0': {
    'What is my match score?': { intent: 'match_score', answer: 'Your saved job description matches 0 of 1 assessable technologies, for a 0% language coverage score.', evidence: [{ label: 'Language coverage', value: '0% · 0 of 1 assessable technologies', url: null }], suggestions: chatSuggestions },
    'What are my gaps?': { intent: 'gaps', answer: 'Java is missing from your public repository language evidence.', evidence: [{ label: 'Missing', value: 'Java', url: null }], suggestions: chatSuggestions },
  },
  'null': {
    'What is my match score?': { intent: 'match_score', answer: 'There are not enough assessable keywords in your saved job description. No percentage score is available.', evidence: [{ label: 'Unassessable', value: 'AWS, Kubernetes', url: null }], suggestions: chatSuggestions },
    'What are my gaps?': { intent: 'gaps', answer: 'There are no assessable language requirements in this description. AWS and Kubernetes cannot be verified from repository languages.', evidence: [{ label: 'Unassessable', value: 'AWS, Kubernetes', url: null }], suggestions: chatSuggestions },
  },
}

#!/usr/bin/env node

import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

export const REVIEW_LENSES = [
  {
    id: 'ui-state-reactivity',
    policySection: '## UI State and Reactivity',
    reviewer: 'change-review',
    evidenceRequirements: [
      'trace the real initiating owner and every programmatic writer',
      'follow retained state through the terminal transition event',
      'prove precedence where selectors or declarative rules overlap',
    ],
    patterns: [
      /\b(useEffect|useLayoutEffect|watchEffect|watch|computed|subscribe|observer)\b/i,
      /\b(addEventListener|removeEventListener|onMount|onDestroy|componentDidMount)\b/i,
      /\.(tsx|jsx|vue|svelte)$/i,
    ],
  },
  {
    id: 'mutation-state-ownership',
    policySection: '## Mutation and State Ownership',
    reviewer: 'change-review',
    patterns: [
      /\.(push|pop|splice|sort|reverse|set|delete|append|extend|update)\s*\(/i,
      /\b(mutate|mutation|mutable|in-place|writeFile|rename|unlink)\b/i,
      /\b(INSERT|UPDATE|DELETE)\b/i,
    ],
  },
  {
    id: 'authentication-authorization',
    policySection: '## Authentication and Authorization',
    reviewer: 'security',
    patterns: [
      /\b(auth|oauth|session|permission|authorize|authorization|rbac|role|tenant)\b/i,
      /\b(orgId|org_id|userId|user_id|apiKey|api_key|bearer|jwt)\b/i,
    ],
  },
  {
    id: 'external-input-injection',
    policySection: '## External Input and Injection',
    reviewer: 'security',
    patterns: [
      /\b(request|req\.|params|query|headers|argv|stdin|webhook|process\.env)\b/i,
      /\b(JSON\.parse|yaml\.load|deserialize|template|child_process|exec|spawn)\b/i,
      /\$\{[^}]+\}/,
      /\b(sql|SELECT|INSERT|UPDATE|DELETE|fetch|URL)\b/i,
    ],
  },
  {
    id: 'persistence-migration',
    policySection: '## Persistence and Migration',
    reviewer: 'change-review',
    patterns: [
      /(^|\/)(migrations?|schema|prisma|database|storage|persistence)(\/|\.|$)/i,
      /\.(sql|prisma)$/i,
      /\b(migrate|backfill|index|constraint|transaction|row|table)\b/i,
    ],
  },
  {
    id: 'async-concurrency',
    policySection: '## Async, Concurrency, and Distributed Work',
    reviewer: 'change-review',
    patterns: [
      /\b(async|await|Promise|Future|goroutine|thread|worker|queue|job)\b/i,
      /\b(retry|timeout|cancel|lock|mutex|semaphore|atomic|concurrent|idempotent)\b/i,
      /\b(transaction|event|webhook|scheduler|cron)\b/i,
    ],
  },
  {
    id: 'dependencies-supply-chain',
    policySection: '## Dependencies and Supply Chain',
    reviewer: 'security',
    patterns: [
      /(^|\/)(package(-lock)?\.json|pnpm-lock\.yaml|yarn\.lock|bun\.lockb?)$/i,
      /(^|\/)(pyproject\.toml|requirements.*\.txt|poetry\.lock|uv\.lock)$/i,
      /(^|\/)(Cargo\.(toml|lock)|go\.(mod|sum)|Gemfile(\.lock)?|pom\.xml)$/i,
      /\b(postinstall|dependency|dependencies|npm install|pip install|curl|wget)\b/i,
    ],
  },
  {
    id: 'secrets-privacy-observability',
    policySection: '## Secrets, Privacy, and Observability',
    reviewer: 'security',
    patterns: [
      /\b(secret|password|credential|token|api.?key|private.?key|pii|consent|privacy)\b/i,
      /\b(log|logger|trace|span|metric|analytics|telemetry|audit)\b/i,
      /(^|\/)(\.env|observability|telemetry|analytics)(\/|\.|$)/i,
    ],
  },
  {
    id: 'public-contracts-compatibility',
    policySection: '## Public Contracts and Compatibility',
    reviewer: 'change-review',
    patterns: [
      /(^|\/)(api|auth|session|routes?|controllers?|handlers?|sdk|cli|proto|openapi|shared|types?)(\/|\.|$)/i,
      /\b(export|public API|response|status code|breaking|deprecated|compatib)\b/i,
      /\.(proto|graphql|gql)$/i,
    ],
  },
  {
    id: 'performance-resource-use',
    policySection: '## Performance and Resource Use',
    reviewer: 'change-review',
    patterns: [
      /\b(cache|pagination|batch|stream|pool|buffer|memory|latency|throughput)\b/i,
      /\b(N\+1|hot path|benchmark|performance|unbounded|fan.?out)\b/i,
      /\b(for|while)\s*\([^)]*\)[\s\S]{0,120}\b(await|fetch|query)\b/i,
    ],
  },
  {
    id: 'ci-build-release',
    policySection: '## CI, Build, and Release',
    reviewer: 'security',
    patterns: [
      /(^|\/)(\.github\/workflows|Dockerfile|docker-compose|terraform|helm|deploy|release)(\/|\.|$)/i,
      /\b(CI|workflow|pipeline|deploy|release|artifact|permissions:|runs-on:)\b/i,
      /\b(npm run build|make|gradle|mvn|docker build)\b/i,
    ],
  },
  {
    id: 'agentic-configuration',
    policySection: '## Agentic Configuration',
    reviewer: 'security',
    patterns: [
      /(^|\/)(AGENTS\.md|SKILL\.md|droids?|skills?|hooks?|prompts?|mcp)(\/|\.|$)/i,
      /\b(model|reasoningEffort|tool policy|prompt injection|subagent|completion criterion)\b/i,
    ],
  },
];

function firstSignal(lens, sources) {
  for (const source of sources) {
    for (const pattern of lens.patterns) {
      const match = source.match(pattern);
      if (match) return `${match[0]} matched ${pattern}`;
    }
  }
  return null;
}

export function selectReviewLenses({ paths = [], diff = '' } = {}) {
  const normalizedPaths = paths.filter(Boolean).map(String);
  const sources = [...normalizedPaths, String(diff)];
  const selected = [
    {
      id: 'mandatory',
      signal: 'mandatory for every changed behavior',
      policySection: '## Mandatory',
      reviewer: 'change-review',
    },
  ];

  for (const lens of REVIEW_LENSES) {
    const signal = firstSignal(lens, sources);
    if (signal) selected.push({
      id: lens.id,
      signal,
      policySection: lens.policySection,
      reviewer: lens.reviewer,
      evidenceRequirements: lens.evidenceRequirements ?? [],
    });
  }

  return selected;
}

function parseArgs(argv) {
  const options = { pathsFile: null, diffFile: null, idsOnly: false };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--paths-file') options.pathsFile = argv[++index];
    else if (arg === '--diff-file') options.diffFile = argv[++index];
    else if (arg === '--ids') options.idsOnly = true;
    else throw new Error(`unknown argument: ${arg}`);
  }
  return options;
}

function runCli() {
  const options = parseArgs(process.argv.slice(2));
  let input = { paths: [], diff: '' };

  if (options.pathsFile || options.diffFile) {
    input = {
      paths: options.pathsFile
        ? readFileSync(options.pathsFile, 'utf8').split(/\r?\n/).filter(Boolean)
        : [],
      diff: options.diffFile ? readFileSync(options.diffFile, 'utf8') : '',
    };
  } else {
    const raw = readFileSync(0, 'utf8').trim();
    if (raw) input = JSON.parse(raw);
  }

  const selected = selectReviewLenses(input);
  process.stdout.write(`${JSON.stringify(
    options.idsOnly ? selected.map(({ id }) => id) : selected,
    null,
    2,
  )}\n`);
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  try {
    runCli();
  } catch (error) {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exitCode = 1;
  }
}

import fs from 'fs';
import path from 'path';
import v8toIstanbul from 'v8-to-istanbul';
import coverageLib from 'istanbul-lib-coverage';

const cwd = process.cwd();
const coverageDir = path.join(cwd, 'coverage');
const tmpDir = path.join(coverageDir, '.tmp');
const finalJson = path.join(coverageDir, 'coverage-final.json');
const outputFile = path.join(coverageDir, 'coverage-summary.json');

async function convert() {
  const { createCoverageMap } = coverageLib;
  const map = createCoverageMap({});

  if (!fs.existsSync(tmpDir)) {
    if (fs.existsSync(finalJson)) {
      const finalPayload = JSON.parse(fs.readFileSync(finalJson, 'utf8'));
      map.merge(finalPayload);
    } else {
      console.error('No coverage data found. Run "npm run test:coverage" first.');
      process.exitCode = 1;
      return;
    }
  } else {
    const files = fs
      .readdirSync(tmpDir)
      .filter((file) => file.startsWith('coverage-') && file.endsWith('.json'));

    if (files.length === 0 && !fs.existsSync(finalJson)) {
      console.error('No coverage payloads detected. Ensure Vitest completed successfully.');
      process.exitCode = 1;
      return;
    }

    for (const file of files) {
      const payload = JSON.parse(fs.readFileSync(path.join(tmpDir, file), 'utf8'));
      if (!Array.isArray(payload.result)) continue;

      for (const script of payload.result) {
        if (!script.url?.startsWith('file:///')) continue;
        const rawPath = decodeURIComponent(new URL(script.url).pathname);
        const normalized =
          rawPath.startsWith('/') && rawPath[2] === ':'
            ? rawPath.slice(1)
            : rawPath;

        if (!fs.existsSync(normalized)) continue;

        const source = fs.readFileSync(normalized, 'utf8');
        const converter = v8toIstanbul(normalized, 0, { source });
        await converter.load();
        converter.applyCoverage(script.functions);
        map.merge(converter.toIstanbul());
      }
    }
  }

  const summary = map.getCoverageSummary().data;
  fs.mkdirSync(coverageDir, { recursive: true });
  fs.writeFileSync(outputFile, JSON.stringify(summary, null, 2));

  console.log('Coverage summary written to', path.relative(cwd, outputFile));
  console.table({
    statements: `${summary.statements.pct.toFixed(2)}%`,
    branches: `${summary.branches.pct.toFixed(2)}%`,
    functions: `${summary.functions.pct.toFixed(2)}%`,
    lines: `${summary.lines.pct.toFixed(2)}%`,
  });
}

convert().catch((error) => {
  console.error('Failed to generate coverage summary:', error);
  process.exitCode = 1;
});

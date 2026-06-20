const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const PRESENTATION_ID = 'AkudsICP6luMiSdRc75ceAzpnqf';
const SCRIPTS_DIR = __dirname;

function run(idx) {
  return new Promise((resolve, reject) => {
    const paramsFile = `./scripts/ppt_params.json`;
    const dataFile = `./scripts/ppt_payload_${idx}.json`;

    console.log(`Creating slide ${idx} ...`);
    const proc = spawn('npx', [
      'lark-cli', 'slides', 'xml_presentation.slide', 'create',
      '--as', 'user',
      '--params', `@${paramsFile}`,
      '--data', `@${dataFile}`
    ], {
      stdio: ['pipe', 'pipe', 'pipe'],
      shell: true
    });

    let out = '';
    let err = '';
    proc.stdout.on('data', d => out += d);
    proc.stderr.on('data', d => err += d);
    proc.on('close', code => {
      if (code !== 0) {
        reject(new Error(`Slide ${idx} failed (code ${code}): ${err || out}`));
      } else {
        console.log(`Slide ${idx} OK`);
        resolve(out);
      }
    });
  });
}

async function main() {
  for (let i = 1; i <= 16; i++) {
    try {
      await run(i);
    } catch (e) {
      console.error(e.message);
      process.exit(1);
    }
  }
  console.log('All slides created.');
}

main();

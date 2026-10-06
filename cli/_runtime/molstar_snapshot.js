'use strict';

const path = require('path');
const { pathToFileURL } = require('url');

async function main() {
  const [htmlPath, outputPath, browserPath] = process.argv.slice(2);
  if (!htmlPath || !outputPath || !browserPath || !process.env.PUPPETEER_MODULE) {
    throw new Error('Usage: molstar_snapshot.js HTML OUTPUT BROWSER (with PUPPETEER_MODULE set)');
  }

  const puppeteer = require(process.env.PUPPETEER_MODULE);
  const browser = await puppeteer.launch({
    executablePath: browserPath,
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu-sandbox']
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1600, height: 1000, deviceScaleFactor: 2 });
    await page.goto(pathToFileURL(path.resolve(htmlPath)).href, { waitUntil: 'load' });
    await page.waitForFunction(
      () => window.__MOLSTAR_READY === true || Boolean(window.__MOLSTAR_ERROR),
      { timeout: 90000 }
    );
    const renderError = await page.evaluate(() => window.__MOLSTAR_ERROR || null);
    if (renderError) throw new Error(`Mol* render failed: ${renderError}`);
    await page.screenshot({ path: path.resolve(outputPath), type: 'png' });
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error && error.stack ? error.stack : error);
  process.exit(1);
});

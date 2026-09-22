import puppeteer from 'puppeteer-core';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const OUTPUT_DIR = path.resolve(__dirname, '../../design/screenshots');

if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

async function capture() {
  console.log('Launching browser with Chrome at:', CHROME_PATH);
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 960, deviceScaleFactor: 2 });

  // 1. Lifecycle Ledger Desktop
  console.log('Capturing Ledger Desktop...');
  await page.goto('http://localhost:5173/', { waitUntil: 'networkidle0' });
  await page.evaluateHandle('document.fonts.ready');
  await page.waitForSelector('[class*="footprintCard"]', { timeout: 15000 });
  await new Promise((r) => setTimeout(r, 600));
  await page.screenshot({ path: path.join(OUTPUT_DIR, 'ledger_page_1280px.png'), fullPage: true });

  // 2. Recommender Page
  console.log('Capturing Recommender Page...');
  const recommenderBtn = (await page.$$('button[class*="navLink"]'))[1];
  if (recommenderBtn) {
    await recommenderBtn.click();
    await new Promise((r) => setTimeout(r, 1200));
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'recommender_page_1280px.png'), fullPage: true });
  }

  // 3. Claim Verifier Page
  console.log('Capturing Claim Verifier Page...');
  const claimBtn = (await page.$$('button[class*="navLink"]'))[2];
  if (claimBtn) {
    await claimBtn.click();
    await new Promise((r) => setTimeout(r, 1500));
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'claim_verifier_page_1280px.png'), fullPage: true });
  }

  // 4. Methodology Page
  console.log('Capturing Methodology Page...');
  const methodBtn = (await page.$$('button[class*="navLink"]'))[3];
  if (methodBtn) {
    await methodBtn.click();
    await new Promise((r) => setTimeout(r, 600));
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'methodology_page_1280px.png'), fullPage: true });
  }

  // 5. Not Available Feature State
  console.log('Capturing Not Available Page...');
  const naBtn = (await page.$$('button[class*="navLink"]'))[4];
  if (naBtn) {
    await naBtn.click();
    await new Promise((r) => setTimeout(r, 600));
    await page.screenshot({ path: path.join(OUTPUT_DIR, 'not_available_page_1280px.png'), fullPage: true });
  }

  await browser.close();
  console.log('All screen screenshots captured successfully!');
}

capture().catch((err) => {
  console.error('Error capturing screenshots:', err);
  process.exit(1);
});

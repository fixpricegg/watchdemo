const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const browser = await chromium.launch({
    executablePath: process.env.WATCHDEMO_CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: true,
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const base = process.env.WATCHDEMO_QA_SITE_URL;
    await page.goto(base + '/login');
    await page.getByLabel('Email', {exact:true}).fill('ivr-browser@example.com');
    await page.getByLabel('Пароль (12–128 символов)', {exact:true}).fill('IVR-browser-password-123');
    await page.getByRole('button', {name:'Продолжить'}).click();
    await page.waitForURL('**/reports');
    await page.goto(base + '/reports/' + process.env.WATCHDEMO_QA_REPORT_ID);
    await page.getByRole('heading', {name:'Эпизоды для разбора', exact:true}).waitFor();
    for (const [detector, round] of [['Entry Death',1], ['Missed Trade v2',2], ['Buy Mismatch',3]]) {
      const card = page.locator('.review-card').filter({has: page.getByRole('heading',{name:detector + ' · Раунд ' + round,exact:true})});
      await card.getByRole('button', {name:'Открыть на радаре · раунд ' + round,exact:true}).click();
      await page.getByRole('status').filter({hasText:'Выбран эпизод: ' + detector}).waitFor();
      await page.locator('.round-info').getByText('Round ' + round,{exact:true}).waitFor();
      await card.locator('summary').click();
      await card.locator('details[open]').waitFor();
    }
    await page.getByRole('button', {name:'Play',exact:true}).click();
    await page.locator('.review-card').first().getByRole('button').click();
    await page.getByRole('button', {name:'Play',exact:true}).waitFor();
    await page.getByRole('button', {name:'Buy Mismatch (1)',exact:true}).click();
    if (await page.locator('.review-card').count() !== 1) throw Error('Type filter mismatch');
    await page.getByRole('button', {name:'Все (3)',exact:true}).click();
    const downloading = page.waitForEvent('download');
    await page.getByRole('link',{name:'Скачать отчёт JSON',exact:true}).click();
    const download = await downloading;
    const exported = JSON.parse(fs.readFileSync(await download.path(),'utf8'));
    if (exported.report.top_problems.length !== 3) throw Error('Export missing priorities');
    await page.reload();
    await page.getByRole('heading',{name:'Эпизоды для разбора',exact:true}).waitFor();
    if (await page.locator('.review-card').count() !== 3) throw Error('Reload lost findings');
    await page.setViewportSize({width:390,height:844});
    if (await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)) throw Error('Mobile horizontal overflow');
    await page.screenshot({path:path.join(process.env.WATCHDEMO_QA_OUTPUT,'mobile.png'),fullPage:true});
    await page.setViewportSize({width:1440,height:1000});
    await page.screenshot({path:path.join(process.env.WATCHDEMO_QA_OUTPUT,'desktop.png'),fullPage:true});
    const realId = process.env.WATCHDEMO_QA_REAL_REPORT_ID;
    if (realId) {
      await page.goto(base + '/reports/' + realId);
      await page.getByRole('heading',{name:'Эпизоды для разбора',exact:true}).waitFor();
      const buttons = page.locator('.review-card button');
      for (let i=0; i < await buttons.count(); i++) {
        await buttons.nth(i).click();
        await page.getByRole('status').filter({hasText:'Выбран эпизод:'}).waitFor();
      }
      await page.screenshot({path:path.join(process.env.WATCHDEMO_QA_OUTPUT,'real-replay.png'),fullPage:true});
      console.log('REAL_BROWSER_OK', await buttons.count(), 'episode jumps');
    }
    if (errors.length) throw Error(errors.join('\n'));
    console.log('BROWSER_OK: all 3 detectors, review facts, round/tick jumps, pause on seek, filters, JSON download, reload, mobile width; no JavaScript errors');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });

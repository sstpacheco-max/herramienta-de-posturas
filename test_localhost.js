const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
  page.on('pageerror', error => console.log('BROWSER ERROR:', error.message));
  
  await page.setViewport({width: 1280, height: 800});
  await page.goto('http://localhost:8080/index.html', {waitUntil: 'networkidle2'});
  
  // Click the button
  await page.click('#btn-add-cam-top');
  
  await new Promise(r => setTimeout(r, 1000));
  
  // Check if modal is visible
  const modalVisible = await page.evaluate(() => {
    const modal = document.getElementById('modal-camera');
    return modal && window.getComputedStyle(modal).display !== 'none';
  });
  
  console.log('Is modal visible?', modalVisible);
  
  await browser.close();
})();

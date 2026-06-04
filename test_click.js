const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  
  // Imprimir logs de la consola del navegador
  page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
  page.on('pageerror', error => console.log('BROWSER ERROR:', error.message));
  
  await page.setViewport({width: 1280, height: 800});
  await page.goto('https://sstpacheco-max.github.io/herramienta-de-posturas/', {waitUntil: 'networkidle2'});
  
  await page.screenshot({path: 'before_click.png'});
  console.log('Screenshot before click taken.');
  
  // Click the button
  await page.click('#btn-add-cam-top');
  
  await new Promise(r => setTimeout(r, 1000));
  
  await page.screenshot({path: 'after_click.png'});
  console.log('Screenshot after click taken.');
  
  // Check if modal is visible
  const modalVisible = await page.evaluate(() => {
    const modal = document.getElementById('modal-camera');
    return modal && window.getComputedStyle(modal).display !== 'none';
  });
  
  console.log('Is modal visible?', modalVisible);
  
  await browser.close();
})();

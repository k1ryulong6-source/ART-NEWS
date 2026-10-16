// Render promo/index.html frame by frame into an MP4 (1920×1080, 30 fps).
// Every CSS animation is paused and seeked, so the film is frame-exact and does not
// depend on machine speed.
//
//   NODE_PATH="$(npm root -g)" node promo/record.cjs [out.mp4] [--fps 30] [--from s] [--to s] [--still s]
//
// --still N writes a single PNG of second N instead of a video (for checking frames).
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');

const args = process.argv.slice(2);
const flag = (name, fallback) => { const i = args.indexOf(name); return i > -1 ? Number(args[i + 1]) : fallback; };
const positional = args.filter((a, i) => !a.startsWith('--') && !(i > 0 && args[i - 1].startsWith('--')));
const out = positional[0] || path.join(__dirname, 'intermission-promo.mp4');
const fps = flag('--fps', 30);
const still = flag('--still', null);

(async () => {
  const launch = { args: ['--force-color-profile=srgb', '--font-render-hinting=none'] };
  if (process.env.CHROMIUM_PATH) launch.executablePath = process.env.CHROMIUM_PATH;
  const browser = await chromium.launch(launch);
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'index.html') + '?record');
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => window.promoReady);           // hand inking is drawn once fonts are in
  const duration = await page.evaluate(() => window.promoDuration);

  if (still !== null) {
    await page.evaluate((ms) => window.seekPromo(ms), still * 1000);
    await page.screenshot({ path: out });
    await browser.close();
    return;
  }

  const from = flag('--from', 0), to = flag('--to', duration / 1000);
  const ffmpeg = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '19', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out],
    { stdio: ['pipe', 'inherit', 'inherit'] });
  const frames = Math.round((to - from) * fps);
  for (let i = 0; i < frames; i++) {
    await page.evaluate((ms) => window.seekPromo(ms), (from + i / fps) * 1000);
    const shot = await page.screenshot({ type: 'png' });
    if (!ffmpeg.stdin.write(shot)) await new Promise((r) => ffmpeg.stdin.once('drain', r));
    if (i % 60 === 0) process.stdout.write(`frame ${i}/${frames}\n`);
  }
  ffmpeg.stdin.end();
  await new Promise((r) => ffmpeg.on('close', r));
  await browser.close();
  console.log('wrote ' + out);
})();

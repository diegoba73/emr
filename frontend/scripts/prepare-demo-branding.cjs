// Run only for the demo image, after the React build.
const fs = require('node:fs');
const path = require('node:path');
if (process.env.REACT_APP_DEMO_MODE !== 'true') {
  throw new Error('Demo branding requires REACT_APP_DEMO_MODE=true');
}
const build = path.join(__dirname, '..', 'build');
const index = path.join(build, 'index.html');
const html = fs.readFileSync(index, 'utf8')
  .replace(/<title>[^<]*<\/title>/, '<title>EMR Demo — Entorno de ejemplo</title>')
  .replace(/href="([^"]*)\/favicon.svg"/, 'href="$1/demo-mark.svg"')
  .replace(/<link[^>]*rel="apple-touch-icon"[^>]*>/, '')
  .replace('SYNESIS — Sistema de historia clínica electrónica', 'EMR Demo — Entorno de ejemplo con datos ficticios');
fs.writeFileSync(index, html);
fs.writeFileSync(path.join(build, 'manifest.json'), JSON.stringify({
  short_name: 'EMR Demo',
  name: 'EMR Demo — Entorno de ejemplo',
  icons: [{ src: 'demo-mark.svg', sizes: 'any', type: 'image/svg+xml', purpose: 'any' }],
  start_url: './demo',
  display: 'standalone',
  theme_color: '#173047',
  background_color: '#ffffff',
}, null, 2));

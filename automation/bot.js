/**
 * विज्ञान रंजन Bot
 * Sends scheduled WhatsApp messages and updates the GitHub Pages blog automatically.
 *
 * Usage:
 *   node bot.js           — normal run (connect + start scheduler)
 *   node bot.js --setup   — just connect + list group IDs, then exit
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode  = require('qrcode-terminal');
const cron    = require('node-cron');
const fs      = require('fs');
const path    = require('path');
const { execSync } = require('child_process');

// ── Paths ────────────────────────────────────────────────────────────────
const REPO_ROOT   = path.resolve(__dirname, '..');
const PLAN_FILE   = path.join(__dirname, 'plan.json');
const CONFIG_FILE = path.join(__dirname, 'config.json');
const AUTH_DIR    = path.join(__dirname, '.wwebjs_auth');

// Unique marker placed in each HTML page — bot inserts new cards just before it
const INSERT_MARKER = '<!-- VIDRANJ_INSERT -->';

const PAGE_FILES = {
  'vidnyan-mahiti': 'vidnyan-mahiti.html',
  'prayog-kodi':    'prayog-kodi.html',
};

const CARD_LABELS = {
  mahiti:  '📚 विज्ञान माहिती',
  tathya:  '🌟 रंजक तथ्ये',
  prayog:  '🧪 प्रयोग',
  kodi:    '🧩 कोडे',
  quiz:    '🎯 Quiz',
  upakram: '🌱 उपक्रम',
};

// ── Config ───────────────────────────────────────────────────────────────
let config;
try {
  config = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
} catch {
  console.error('\n❌  config.json सापडला नाही.');
  console.error('   automation/config.json.example ➜ automation/config.json कॉपी करा.\n');
  process.exit(1);
}

const SETUP_MODE = process.argv.includes('--setup');

// ── WhatsApp Client ───────────────────────────────────────────────────────
const client = new Client({
  authStrategy: new LocalAuth({ dataPath: AUTH_DIR }),
  puppeteer: { args: ['--no-sandbox', '--disable-setuid-sandbox'] },
});

client.on('qr', qr => {
  console.log('\n📱  QR Code स्कॅन करा:');
  console.log('    WhatsApp → Settings → Linked Devices → Link a Device\n');
  qrcode.generate(qr, { small: true });
});

client.on('authenticated', () => console.log('🔐  Authenticated!'));

client.on('auth_failure', () => {
  console.error('\n❌  Auth failed. ' + AUTH_DIR + ' डिलीट करा आणि पुन्हा स्कॅन करा.\n');
  process.exit(1);
});

client.on('ready', async () => {
  console.log('✅  WhatsApp connected!\n');

  if (SETUP_MODE || !config.groupId || config.groupId === 'YOUR_GROUP_ID@g.us') {
    await printGroups();
    if (!SETUP_MODE) {
      console.log('⚠️   config.json मध्ये groupId सेट करा आणि bot पुन्हा चालवा.\n');
    }
    process.exit(0);
  }

  console.log(`📌  Group ID: ${config.groupId}`);
  startScheduler();
});

client.initialize();

// ── Group discovery ───────────────────────────────────────────────────────
async function printGroups() {
  console.log('📋  तुमचे WhatsApp groups (config.json मध्ये groupId copy करा):\n');
  const chats = await client.getChats();
  const groups = chats.filter(c => c.isGroup);
  if (groups.length === 0) {
    console.log('   कोणताही group सापडला नाही.');
  } else {
    groups.forEach(g => console.log(`  "${g.name}"\n   → ${g.id._serialized}\n`));
  }
}

// ── Scheduler ─────────────────────────────────────────────────────────────
function startScheduler() {
  showUpcoming();
  // Check every minute
  cron.schedule('* * * * *', checkAndPost);
  console.log('\n⏰  Scheduler चालू आहे! दर मिनिटाला plan.json तपासतो.\n');
}

function showUpcoming() {
  const plan = readPlan();
  const pending = plan.filter(e => !e.posted);
  console.log(`📅  Pending posts: ${pending.length}`);
  if (pending.length > 0) {
    const next = pending[0];
    console.log(`   पुढचा: Day ${next.day} ${next.session} ← ${next.datetime}`);
  }
  console.log();
}

// ── Core: check plan and post ─────────────────────────────────────────────
async function checkAndPost() {
  const now  = formatNow();
  const plan = readPlan();
  let changed = false;

  for (let i = 0; i < plan.length; i++) {
    const entry = plan[i];
    if (entry.posted || entry.datetime !== now) continue;

    console.log(`\n📤  [${now}]  Day ${entry.day} (${entry.dayName}) — ${entry.session}`);

    try {
      // 1 ── Send WhatsApp message
      await client.sendMessage(config.groupId, entry.whatsappMessage);
      console.log('    ✅  WhatsApp sent');

      // 2 ── Update blog HTML files
      const pages = Array.isArray(entry.blogPages) ? entry.blogPages : [];
      for (const page of pages) {
        updatePage(page, entry);
        console.log(`    ✅  ${PAGE_FILES[page]} updated`);
      }

      // 3 ── Git commit + push
      if (pages.length > 0) {
        gitPush(entry);
        console.log('    ✅  GitHub pushed');
      }

      plan[i].posted   = true;
      plan[i].postedAt = now;
      changed = true;
      console.log(`    🎉  Done!\n`);

    } catch (err) {
      console.error(`    ❌  Error: ${err.message}\n`);
    }
  }

  if (changed) writePlan(plan);
}

// ── HTML page update ──────────────────────────────────────────────────────
function updatePage(page, entry) {
  const filePath = path.join(REPO_ROOT, PAGE_FILES[page]);
  let html = fs.readFileSync(filePath, 'utf8');

  if (!html.includes(INSERT_MARKER))
    throw new Error(`INSERT_MARKER not found in ${PAGE_FILES[page]}`);

  // Remove "लवकरच येणार आहे!" empty-state on first post
  html = html.replace(/<div class="empty-state">[\s\S]*?<\/div>(\s*)/, '$1');

  const card = buildCard(page, entry);
  html = html.replace(INSERT_MARKER, card + '\n\n    ' + INSERT_MARKER);

  fs.writeFileSync(filePath, html, 'utf8');
}

// ── Card HTML builder ─────────────────────────────────────────────────────
function buildCard(page, entry) {
  const dateLabel = `दिवस ${entry.day} · ${entry.dayName}`;
  const body      = sanitize(entry.whatsappMessage);
  const type      = entry.cardType || (page === 'vidnyan-mahiti' ? 'mahiti' : 'prayog');
  const label     = CARD_LABELS[type] || type;

  return `    <!-- Day ${entry.day} · ${entry.session.toUpperCase()} — auto-posted ${formatNow()} -->
    <article class="content-card ${type}">
      <div class="card-header">
        <span class="badge badge-${type}">${label}</span>
        <span class="card-tag">${entry.tag}</span>
        <span class="card-date">${dateLabel}</span>
      </div>
      <div class="card-body">${body}</div>
    </article>`;
}

// Strip WhatsApp markdown, escape HTML
function sanitize(text) {
  return text
    .replace(/\*/g, '')
    .replace(/_([^_\n]+)_/g, '$1')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .trim();
}

// ── Git helpers ───────────────────────────────────────────────────────────
function gitPush(entry) {
  const files   = Object.values(PAGE_FILES).join(' ');
  const message = `Auto-post: Day ${entry.day} ${entry.session} — ${entry.tag}`;
  try {
    execSync(`git add ${files}`, { cwd: REPO_ROOT, stdio: 'pipe' });
    execSync(`git commit -m "${message}"`, { cwd: REPO_ROOT, stdio: 'pipe' });
    execSync('git push origin main', { cwd: REPO_ROOT, stdio: 'pipe' });
  } catch (e) {
    const msg = e.stderr ? e.stderr.toString() : e.message;
    if (msg.includes('nothing to commit')) {
      console.log('    ⚠️   No HTML changes to commit (already up to date)');
    } else {
      throw new Error(msg.trim());
    }
  }
}

// ── Utilities ─────────────────────────────────────────────────────────────
function formatNow() {
  const d = new Date();
  return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}
function p(n) { return String(n).padStart(2, '0'); }

function readPlan()       { return JSON.parse(fs.readFileSync(PLAN_FILE, 'utf8')); }
function writePlan(plan)  { fs.writeFileSync(PLAN_FILE, JSON.stringify(plan, null, 2)); }

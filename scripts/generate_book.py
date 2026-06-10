#!/usr/bin/env python3
"""
विज्ञान रंजन — पुस्तक जनरेटर
Generates a print-ready A5 book from weekly plan markdown files.

Run from project root:
    python3 scripts/generate_book.py

Output: book/vidnyan-ranjan-pustak.html
Print in Chrome: File → Print → Save as PDF → Paper: A5 → Margins: None.
To add Week 5+: create .plan/dainik-post-week5.md then rerun.
"""

import re
from pathlib import Path

BASE_DIR       = Path(__file__).resolve().parent.parent
PLAN_DIR       = BASE_DIR / '.plan'
BOOK_DIR       = BASE_DIR / 'book'
SCIENTISTS_REL = '../scientists'
IMAGES_REL     = '..'

# ---------------------------------------------------------------------------
# Scientist images (whole-word regex to avoid "Non-Newtonian" matching Newton)
# ---------------------------------------------------------------------------
SCIENTIST_IMAGES = {
    'टॉरिचेली':        'Torricelli.jpg',
    r'\bTorricelli\b': 'Torricelli.jpg',
    'न्यूटन':           'Sir_Newton.png',
    r'\bNewton\b':      'Sir_Newton.png',
    'फॅरेडे':           'M_Faraday_Th_Phillips_oil_1842.jpg',
    r'\bFaraday\b':     'M_Faraday_Th_Phillips_oil_1842.jpg',
    'मेरी अॅनिंग':     'Mary_Anning_painting.jpg',
    r'\bMary Anning\b': 'Mary_Anning_painting.jpg',
}

# Structured metadata for blog-style rendering (keyed by image filename)
SCIENTIST_METADATA = {
    'Torricelli.jpg': {
        'name':     'इव्हान्जेलिस्टा टॉरिचेली',
        'subtitle': 'Evangelista Torricelli · बॅरोमीटरचे जनक',
        'tag':      'वायुदाब · बॅरोमीटर',
        'meta': [
            ('जन्म',    '१५ ऑक्टोबर १६०८, फेएन्झा, इटली'),
            ('निधन',    '२५ ऑक्टोबर १६४७ (वय ३९)'),
            ('क्षेत्र', 'भौतिकशास्त्र, गणित'),
        ],
        'chips': ['दाबाचे एकक "Torr"', 'हवामानशास्त्राचा पाया', 'आधुनिक बॅरोमीटर', 'शून्यावकाशाचा शोध'],
    },
    'Sir_Newton.png': {
        'name':     'सर आयझॅक न्यूटन',
        'subtitle': 'Sir Isaac Newton · आधुनिक भौतिकशास्त्राचे जनक',
        'tag':      'गुरुत्वाकर्षण · गतीचे नियम',
        'meta': [
            ('जन्म',    '४ जानेवारी १६४३, इंग्लंड'),
            ('निधन',    '३१ मार्च १७२७ (वय ८४)'),
            ('क्षेत्र', 'भौतिकशास्त्र, गणित, खगोलशास्त्र'),
        ],
        'chips': ['बलाचे एकक "Newton (N)"', 'गुरुत्वाकर्षणाचा नियम', 'गतीचे ३ नियम', 'Principia Mathematica'],
    },
    'M_Faraday_Th_Phillips_oil_1842.jpg': {
        'name':     'मायकेल फॅरेडे',
        'subtitle': 'Michael Faraday · आधुनिक विद्युत युगाचे जनक',
        'tag':      'विद्युत-चुंबकीय प्रेरण · जनित्र',
        'meta': [
            ('जन्म',    '२२ सप्टेंबर १७९१, इंग्लंड'),
            ('निधन',    '२५ ऑगस्ट १८६७ (वय ७५)'),
            ('क्षेत्र', 'भौतिकशास्त्र, रसायनशास्त्र'),
        ],
        'chips': ['धारितेचे एकक "Farad (F)"', 'Generator आणि Motor', 'Faraday Cage', 'Electroplating'],
    },
    'Mary_Anning_painting.jpg': {
        'name':     'मेरी अॅनिंग',
        'subtitle': 'Mary Anning · जीवाश्मांची शोधकर्ती',
        'tag':      'जीवाश्मशास्त्र · उत्क्रांती',
        'meta': [
            ('जन्म',    '२१ मे १७९९, लाईम रेजिस, इंग्लंड'),
            ('निधन',    '९ मार्च १८४७ (वय ४७)'),
            ('क्षेत्र', 'जीवाश्मशास्त्र (Palaeontology)'),
        ],
        'chips': ['Ichthyosaurus शोध', 'Plesiosaur शोध', 'उत्क्रांती सिद्धांताचा पाया', 'जीवाश्मशास्त्राची जननी'],
    },
}

# ---------------------------------------------------------------------------
# Topic images — shown on non-scientist pages when topic matches
# keyword → filename relative to project root
# ---------------------------------------------------------------------------
TOPIC_IMAGES = [
    (['हृदय'],                          'Gemini_Generated_whale-heart.png'),
    (['इंद्रधनुष्य', 'रंगांचे'],       'Double-alaskan-rainbow.jpg'),
    (['जैवविविधता', 'मधमाश'],          'licensed-image.jpeg'),
]

def get_topic_image(topic, text):
    combined = topic + ' ' + text[:300]
    for keywords, filename in TOPIC_IMAGES:
        if any(kw in combined for kw in keywords):
            path = BASE_DIR / filename
            if path.exists():
                return f'{IMAGES_REL}/{filename}'
    return None

# ---------------------------------------------------------------------------
# Day icons — shown as a visual element on non-scientist morning pages
# ---------------------------------------------------------------------------
DAY_ICONS = [
    ('क्विझ',              '🏆'),
    ('जीवाश्म',            '🦕'),
    ('डायनोसॉर',           '🦕'),
    ('हाडे',               '🦴'),
    ('हृदय',               '❤️'),
    ('शरीर विज्ञान',       '🫀'),
    ('सूक्ष्मजीव',         '🦠'),
    ('चंद्र',              '🌙'),
    ('दुर्बीण',            '🔭'),
    ('इंद्रधनुष्य',        '🌈'),
    ('रंग',                '🌈'),
    ('गुरुत्वाकर्षण',      '🍎'),
    ('प्रकाशसंश्लेषण',     '🌱'),
    ('वनस्पती',            '🌿'),
    ('पर्यावरण',           '🌍'),
    ('जैवविविधता',         '🌿'),
    ('चुंबक',              '🧲'),
    ('विद्युत',            '⚡'),
    ('ध्वनी',              '🎵'),
    ('आवाज',               '🎵'),
    ('हवामान',             '☁️'),
    ('हवा',                '🌬️'),
    ('वायुदाब',            '🌬️'),
    ('उष्णता',             '🌡️'),
    ('तापमान',             '🌡️'),
    ('यंत्रे',             '⚙️'),
    ('Oobleck',            '🌊'),
    ('पाण्याचे',           '💧'),
    ('पाणी',               '💧'),
    ('केशाकर्षण',          '🔬'),
    ('पृष्ठतान',           '🔬'),
    ('अन्न',               '🍽️'),
    ('दूध',                '🥛'),
    ('जहाज',               '🚢'),
    ('विज्ञान म्हणजे',     '🔬'),
]

# ---------------------------------------------------------------------------
# Skip patterns — lines to exclude entirely
# ---------------------------------------------------------------------------
SKIP_LINE_RE = re.compile('|'.join([
    r'padlet\.com',
    r'गटात (पाठवा|सांगा)',
    r'मराठी विज्ञान परिषद',
    r'विज्ञान परिषद',
    r'^📢\s.*येणार आहे',
    r'^📢\s.*पाठवू',
    r'फोटो.*Padlet',
    r'Padlet.*अपलोड',
    r'व्हिडिओ.*Padlet',
    r'📌.*Padlet',
    r'फोटो अपलोड कसे',
    r'Padlet उघडा',
    r'Pin केलेला मेसेज',
    r'📸.*Padlet',
    r'Padlet.*शेअर',
    r'विज्ञान रंजन\s*[|।]\s*दिवस',
    r'संध्याकाळची पोस्ट दुपारी',
    r'⏰',
    r'आजचा विषय\s*:',
    r'आजच[ाे] शास्त्रज्ञ',
]))

# Chunk-level: skip entire paragraph if it contains these keywords
SKIP_CHUNK_RE = re.compile('|'.join([
    r'विज्ञानवीर',
    r'विज्ञानवीर घोषणा',
    r'या आठवड्याचा विज्ञानवीर',
    r'असाच उत्साह कायम ठेव',
    r'सर्वाधिक बरोबर उत्तरे देणाऱ्याचे नाव',
    r'काल\'?च्या.*उत्तर',
]))


def should_skip_line(line):
    return bool(SKIP_LINE_RE.search(line))

def should_skip_chunk(lines):
    text = ' '.join(lines)
    return bool(SKIP_CHUNK_RE.search(text))


# ---------------------------------------------------------------------------
# Inline markdown → HTML
# ---------------------------------------------------------------------------

def apply_inline(text):
    text = re.sub(r'\*\*([^*\n]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*([^*\n]+)\*',     r'<strong>\1</strong>', text)
    text = re.sub(r'_([^_\n]+)_',       r'<em>\1</em>', text)
    return text


# ---------------------------------------------------------------------------
# Chunk type detection
# ---------------------------------------------------------------------------

def is_numbered(line):
    return bool(re.match(r'^[१२३४५६७८९०\d][).]\s', line.strip()))

def is_bullet(line):
    s = line.strip()
    return s.startswith('- ') or s.startswith('• ') or s.startswith('* ')

def is_table_row(line):
    return line.strip().startswith('|') and line.strip().endswith('|')

def plain(text):
    return re.sub(r'[\*_]', '', text).strip()

def get_chunk_type(lines, in_riddle=False):
    if not lines:
        return 'empty'
    first = lines[0].strip()
    fp    = plain(first)

    if re.match(r'^━+$', first):
        return 'separator'
    if re.search(r'तुम्हाला माहीत आहे का', first) or first.startswith('💡'):
        return 'fact'
    if re.match(r'^साहित्य\s*:?$', fp):
        return 'materials_head'
    if re.match(r'^(?:साहित्य\s*:)', fp):
        return 'materials_head'
    if re.match(r'^(?:कृती|असे करा|कसे करायचे)\s*:?$', fp):
        return 'steps_head'
    if re.match(r'^विज्ञान काय', fp):
        return 'science'
    if re.match(r'^⚠️|^सुरक्षितता', fp):
        return 'warning'
    if is_table_row(first):
        return 'table'
    content_lines = [l for l in lines if l.strip()]
    if content_lines and all(is_bullet(l) for l in content_lines):
        return 'bullets'
    if content_lines and all(is_numbered(l) for l in content_lines):
        return 'numbers'
    # Verse: short non-marked lines, typically a riddle poem
    if (in_riddle and len(content_lines) >= 3
            and all(len(l.strip()) < 65 and not is_bullet(l) and not is_numbered(l)
                    for l in content_lines)
            and not any(re.search(r'[:()]$', l.strip()) for l in content_lines)):
        return 'verse'
    return 'text'


# ---------------------------------------------------------------------------
# Chunk renderers
# ---------------------------------------------------------------------------

def render_bullets(lines):
    items = []
    for l in lines:
        if l.strip():
            txt = re.sub(r'^[•\-\*]\s+', '', l.strip())
            if not should_skip_line(txt):
                items.append(f'<li>{apply_inline(txt)}</li>')
    return '<ul>' + ''.join(items) + '</ul>' if items else ''

def render_numbers(lines):
    items = []
    for l in lines:
        if l.strip():
            txt = re.sub(r'^[१२३४५६७८९०\d][).]\s*', '', l.strip())
            if not should_skip_line(txt):
                items.append(f'<li>{apply_inline(txt)}</li>')
    return '<ol>' + ''.join(items) + '</ol>' if items else ''

def render_table(lines):
    html = ['<table class="content-table">']
    header_done = False
    for row in lines:
        if re.match(r'^\|[\s\-|]+\|$', row.strip()):
            header_done = True
            continue
        cells = [c.strip() for c in row.strip().strip('|').split('|')]
        tag = 'th' if not header_done else 'td'
        html.append('<tr>' + ''.join(f'<{tag}>{apply_inline(c)}</{tag}>' for c in cells) + '</tr>')
        if not header_done:
            header_done = True
    html.append('</table>')
    return '\n'.join(html)

def render_text(lines):
    parts = []
    for l in lines:
        if l.strip():
            parts.append(apply_inline(l.strip()))
    return '<p>' + '<br>'.join(parts) + '</p>' if parts else ''

def render_chunk(ctype, lines):
    if ctype == 'separator':
        return '<hr class="separator">'
    if ctype == 'fact':
        parts = [apply_inline(l.strip()) for l in lines if l.strip()]
        return '<div class="fact-box">' + '<br>'.join(parts) + '</div>'
    if ctype == 'science':
        parts = [apply_inline(l.strip()) for l in lines if l.strip()]
        return '<div class="science-box">' + '<br>'.join(parts) + '</div>'
    if ctype == 'warning':
        parts = [apply_inline(l.strip()) for l in lines if l.strip()]
        return '<div class="warning-box">' + '<br>'.join(parts) + '</div>'
    if ctype == 'verse':
        parts = [apply_inline(l.strip()) for l in lines if l.strip()]
        return '<div class="verse-box">' + '<br>'.join(parts) + '</div>'
    if ctype == 'bullets':
        return render_bullets(lines)
    if ctype == 'numbers':
        return render_numbers(lines)
    if ctype == 'table':
        return render_table(lines)
    return render_text(lines)


# ---------------------------------------------------------------------------
# Main markdown → HTML converter
# ---------------------------------------------------------------------------

SECTION_HEADER_RE = re.compile(
    r'^(?:साहित्य|कृती|असे करा|कसे करायचे|विज्ञान काय)\s*:?$'
)

def insert_section_breaks(text):
    """Ensure each semantic section header is its own blank-line-delimited chunk."""
    lines = text.split('\n')
    out = []
    for line in lines:
        fp = plain(line.strip())
        is_hdr = (SECTION_HEADER_RE.match(fp)
                  or re.search(r'तुम्हाला माहीत आहे का', fp)
                  or line.strip().startswith('💡'))
        if is_hdr:
            if out and out[-1].strip():
                out.append('')
            out.append(line)
            out.append('')
        else:
            out.append(line)
    return '\n'.join(out)


def md_to_html(text, in_riddle=False):
    if not text:
        return ''

    text = insert_section_breaks(text)

    # Split into chunks (blank-line separated)
    raw_chunks = []
    current = []
    for line in text.split('\n'):
        if should_skip_line(line):
            continue
        if line.strip().startswith('#'):
            continue
        if re.match(r'^━+$', line.strip()):
            if current:
                raw_chunks.append(current)
                current = []
            raw_chunks.append([line.strip()])
        elif not line.strip():
            if current:
                raw_chunks.append(current)
                current = []
        else:
            current.append(line)
    if current:
        raw_chunks.append(current)

    # Filter out विज्ञानवीर chunks
    chunks = [c for c in raw_chunks if not should_skip_chunk(c)]

    # Type each chunk
    typed = [(get_chunk_type(c, in_riddle), c) for c in chunks]

    # Group: materials_head + bullets → materials-box
    #        steps_head + numbers → steps-box
    result = []
    i = 0
    while i < len(typed):
        ctype, lines = typed[i]

        if (ctype == 'materials_head'
                and i + 1 < len(typed)
                and typed[i + 1][0] == 'bullets'):
            label = apply_inline(plain(lines[0]).rstrip(':'))
            inner = render_bullets(typed[i + 1][1])
            result.append(
                f'<div class="materials-box">'
                f'<div class="section-label">📦 {label}</div>'
                f'{inner}</div>'
            )
            i += 2
            continue

        if (ctype == 'steps_head'
                and i + 1 < len(typed)
                and typed[i + 1][0] == 'numbers'):
            label = apply_inline(plain(lines[0]).rstrip(':'))
            inner = render_numbers(typed[i + 1][1])
            result.append(
                f'<div class="steps-box">'
                f'<div class="section-label">📋 {label}</div>'
                f'{inner}</div>'
            )
            i += 2
            continue

        result.append(render_chunk(ctype, lines))
        i += 1

    return '\n'.join(r for r in result if r)


# ---------------------------------------------------------------------------
# Plan file parsing
# ---------------------------------------------------------------------------

def get_scientist_image(text):
    for pattern, img in SCIENTIST_IMAGES.items():
        if pattern.startswith(r'\b'):
            if re.search(pattern, text):
                return f'{SCIENTISTS_REL}/{img}'
        elif pattern in text:
            return f'{SCIENTISTS_REL}/{img}'
    return None

def get_day_icon(topic, morning_text):
    for keyword, icon in DAY_ICONS:
        if keyword in topic or keyword in morning_text[:200]:
            return icon
    return '🔬'

def detect_evening_type(text):
    if 'क्विझ उत्तरे' in text:
        return 'quiz_answers'
    if 'साप्ताहिक क्विझ' in text or ('प्र.' in text and 'अ)' in text):
        return 'quiz'
    if 'साहित्य:' in text or 'साहित्य :' in text:
        return 'experiment'
    if 'कोडे' in text or 'मी कोण' in text:
        return 'riddle'
    if 'फोटो शेअर' in text:
        return 'photo_sharing'
    if 'उपक्रम' in text:
        return 'activity'
    return 'general'

def parse_plan_file(filepath):
    content = Path(filepath).read_text(encoding='utf-8')
    days = []
    blocks = re.split(r'(?=^## दिवस )', content, flags=re.MULTILINE)

    for block in blocks:
        if not block.strip() or not block.startswith('## दिवस'):
            continue
        m = re.match(
            r'^## दिवस ([^\s—–]+)\s*[—–]\s*([^,\n]+),\s*([^|\n]+?)(?:\s*\|\s*(.+?))?(?:\n|$)',
            block
        )
        if not m:
            continue

        day_num  = m.group(1).strip()
        day_name = m.group(2).strip()
        date     = m.group(3).strip()
        topic    = (m.group(4) or '').strip()

        morning_m = re.search(
            r'### 🌅 सकाळची पोस्ट[^\n]*\n(.*?)(?=### 🌆|### 🔬[^\n]*दुपार|\Z)',
            block, re.DOTALL
        )
        morning = morning_m.group(1).strip() if morning_m else ''

        midday_m = re.search(
            r'### 🔬[^\n]*दुपारची पोस्ट[^\n]*\n(.*?)(?=### 🌆|\Z)',
            block, re.DOTALL
        )
        if midday_m:
            morning = morning + '\n\n' + midday_m.group(1).strip()

        evening_m = re.search(
            r'### 🌆 संध्याकाळची पोस्ट[^\n]*\n(.*?)(?=^---|\Z)',
            block, re.DOTALL | re.MULTILINE
        )
        evening = evening_m.group(1).strip() if evening_m else ''

        scientist_img = get_scientist_image(morning)
        evening_type  = detect_evening_type(evening)
        day_icon      = None if scientist_img else get_day_icon(topic, morning)

        days.append({
            'number':        day_num,
            'day_name':      day_name,
            'date':          date,
            'topic':         topic,
            'morning':       morning,
            'evening':       evening,
            'evening_type':  evening_type,
            'scientist_img': scientist_img,
            'day_icon':      day_icon,
        })

    return days

def collect_plan_files():
    files = []
    w1 = PLAN_DIR / 'dainik-post.md'
    if w1.exists():
        files.append(w1)
    files.extend(sorted(PLAN_DIR.glob('dainik-post-week*.md')))
    return files


# ---------------------------------------------------------------------------
# Page HTML generators
# ---------------------------------------------------------------------------

def morning_page(day):
    content = md_to_html(day['morning'])

    if day['scientist_img']:
        img_file = Path(day['scientist_img']).name
        meta = SCIENTIST_METADATA.get(img_file, {})

        meta_rows = ''.join(
            f'<tr><td>{k}</td><td>{v}</td></tr>'
            for k, v in meta.get('meta', [])
        )
        chips_html = ''.join(
            f'<span class="sci-chip">{c}</span>'
            for c in meta.get('chips', [])
        )

        profile_html = f'''
<div class="sci-profile">
  <div class="sci-profile-left">
    <img src="{day["scientist_img"]}" alt="{meta.get("name", "")}">
    <table class="sci-meta-table">{meta_rows}</table>
  </div>
  <div class="sci-profile-right">
    <div class="sci-name">{meta.get("name", "")}</div>
    <div class="sci-subtitle">{meta.get("subtitle", "")}</div>
    <span class="sci-tag">{meta.get("tag", "")}</span>
    {content}
  </div>
</div>
<div class="sci-chips">{chips_html}</div>'''

        return f'''
<div class="page scientist-page">
  <div class="page-band scientist-band">
    <div class="band-middle">
      <div class="band-session">🔬 शास्त्रज्ञ</div>
      <div class="band-topic">{day["topic"]}</div>
    </div>
  </div>
  <div class="page-body">
    <div class="page-content">
      {profile_html}
    </div>
  </div>
  <div class="pg-footer"></div>
</div>'''

    else:
        topic_img = get_topic_image(day['topic'], day['morning'])
        if topic_img:
            visual = (
                f'<div class="topic-img-card">'
                f'<img src="{topic_img}" alt="{day["topic"]}">'
                f'</div>'
            )
        else:
            icon = day['day_icon'] or '🔬'
            visual = f'<div class="day-icon-card">{icon}</div>'

        return f'''
<div class="page morning-page">
  <div class="page-band morning-band">
    <div class="band-middle">
      <div class="band-session">🌅</div>
      <div class="band-topic">{day["topic"]}</div>
    </div>
  </div>
  <div class="page-body">
    <div class="page-content">
      {visual}
      {content}
    </div>
  </div>
  <div class="pg-footer"></div>
</div>'''


def observation_box(etype):
    if etype in ('experiment', 'activity'):
        return '''
<div class="observation-box">
  <div class="obs-title">✏️ माझे निरीक्षण</div>
  <div class="obs-line"></div>
  <div class="obs-line"></div>
  <div class="obs-line"></div>
  <div class="obs-draw">✏️ चित्र काढा / फोटो चिकटवा</div>
</div>'''
    if etype == 'riddle':
        return '''
<div class="observation-box riddle-obs">
  <div class="obs-title">💭 माझे उत्तर</div>
  <div class="obs-line wide"></div>
  <div class="obs-line wide"></div>
</div>'''
    return ''


def evening_page(day, appendix_page_num=None):
    is_riddle = day['evening_type'] == 'riddle'
    content   = md_to_html(day['evening'], in_riddle=is_riddle)
    obs       = observation_box(day['evening_type'])

    type_icons = {
        'experiment':   '🧪 प्रयोग',
        'activity':     '🏃 उपक्रम',
        'riddle':       '🧩 कोडे',
        'quiz':         '🏆 क्विझ',
        'quiz_answers': '✅ उत्तरे',
        'photo_sharing':'📸 फोटो',
        'general':      '🌆',
    }
    session_label = type_icons.get(day['evening_type'], '🌆')

    topic_img = get_topic_image(day['topic'], day['evening'])
    visual = ''
    if topic_img and day['evening_type'] not in ('quiz', 'quiz_answers', 'photo_sharing'):
        visual = (
            f'<div class="topic-img-card">'
            f'<img src="{topic_img}" alt="{day["topic"]}">'
            f'</div>'
        )

    xref = ''
    if is_riddle and appendix_page_num:
        xref = f'<div class="ans-xref">उत्तर: पृ. {appendix_page_num}</div>'

    return f'''
<div class="page evening-page">
  <div class="page-band evening-band">
    <div class="band-middle">
      <div class="band-session">{session_label}</div>
      <div class="band-topic">{day["topic"]}</div>
    </div>
  </div>
  <div class="page-body">
    <div class="page-content">
      {visual}
      {content}
      {obs}
      {xref}
    </div>
  </div>
  <div class="pg-footer"></div>
</div>'''


def answers_appendix(all_days, riddle_page_nums=None):
    riddles = []
    quizzes = []
    riddle_page_nums = riddle_page_nums or {}

    for i, day in enumerate(all_days):
        if day['evening_type'] == 'riddle':
            answer = '—'
            if i + 1 < len(all_days):
                m = re.search(r"काल'?च्या कोड्याचे उत्तर[:\s*]*([^\n✅]+)",
                              all_days[i + 1]['morning'])
                if m:
                    answer = re.sub(r'\*+', '', m.group(1)).strip()
            riddles.append({
                'day':      day['number'],
                'day_name': day['day_name'],
                'date':     day['date'],
                'answer':   answer,
                'pg':       riddle_page_nums.get(day['number'], ''),
            })

        if day['evening_type'] == 'quiz_answers':
            quizzes.append({
                'day':     day['number'],
                'date':    day['date'],
                'content': md_to_html(day['evening']),
            })

    riddle_html = ''
    if riddles:
        rows = ''.join(
            f'<tr>'
            f'<td>{r["day_name"]}, {r["date"]}'
            f'{"<br><small style=\'color:#888\'>प्र. पृ. " + str(r["pg"]) + "</small>" if r["pg"] else ""}'
            f'</td>'
            f'<td><strong>{r["answer"]}</strong></td>'
            f'</tr>'
            for r in riddles
        )
        riddle_html = f'''
<h2>🧩 कोड्यांची उत्तरे</h2>
<table class="answer-table">
  <tr><th>दिवस</th><th>उत्तर</th></tr>
  {rows}
</table>'''

    quiz_html = ''
    if quizzes:
        sections = ''.join(
            f'<h3>दिवस {q["day"]} — {q["date"]}</h3>{q["content"]}'
            for q in quizzes
        )
        quiz_html = f'<h2>🏆 क्विझ उत्तरे</h2>{sections}'

    return f'''
<div class="page appendix-page">
  <div class="appendix-band">
    <span class="appendix-band-icon">📚</span>
    <span class="appendix-band-title">उत्तरे</span>
  </div>
  <div class="page-body">
    <div class="page-content">
      {riddle_html}
      {quiz_html}
    </div>
  </div>
  <div class="pg-footer"></div>
</div>'''


def scientists_section_page(scientist_days):
    names = []
    for day in scientist_days:
        m = re.search(r'आजच[ाे] शास्त्रज्ञ[:\s*]+([^\n*\(]+)', day['morning'])
        if m:
            names.append(m.group(1).strip().strip('*').strip())
    name_chips = ''.join(f'<div class="sci-sec-chip">{n}</div>' for n in names)

    return f'''
<div class="page scientists-section-page">
  <div class="sci-sec-top">
    <div class="sci-sec-icon-row">🔬 🧪 🌡️ 📜</div>
    <div class="sci-sec-title">शास्त्रज्ञ</div>
    <div class="sci-sec-subtitle">विज्ञानाचे महान अभ्यासक</div>
  </div>
  <div class="sci-sec-body">
    <div class="sci-sec-label">या विभागात आहे…</div>
    <div class="sci-sec-chips">{name_chips}</div>
    <div class="sci-sec-note">
      प्रत्येक शास्त्रज्ञाची कहाणी, त्यांचे महत्त्वाचे शोध,
      आणि त्यांच्याशी संबंधित प्रयोग.
    </div>
  </div>
  <div class="pg-footer"></div>
</div>'''


def cover_page():
    topics = [
        '💧 पाणी आणि हवा', '🌈 प्रकाश आणि रंग',
        '❤️ शरीर विज्ञान',  '🧲 चुंबकत्व',
        '🌱 वनस्पती',       '🎵 ध्वनी',
        '🍎 गुरुत्वाकर्षण', '🌙 चंद्र',
        '🦠 सूक्ष्मजीव',    '⚡ विद्युत',
        '🔭 दुर्बीण',       '🦕 जीवाश्म',
    ]
    chips = ''.join(f'<div class="cover-chip">{t}</div>' for t in topics)
    return f'''
<div class="page cover-page">
  <div class="cover-top">
    <div class="cover-emoji-row">🔬 🧪 🌡️ 🔭 ⚡ 🌿</div>
    <div class="cover-title">विज्ञानाचा रंजक शोध</div>
    <div class="cover-period">मे – जून २०२६</div>
  </div>
  <div class="cover-bottom">
    <div>
      <div class="cover-section-label">या पुस्तकात आहे…</div>
      <div class="cover-chips">{chips}</div>
    </div>
    <div class="cover-badge">
      <span>📖 २८ दिवस &nbsp;·&nbsp; ५६ प्रयोग & उपक्रम &nbsp;·&nbsp; ४ क्विझ</span>
    </div>
  </div>
</div>'''


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CSS = """\
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;600;700&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --orange:          #C94E0A;
  --orange-mid:      #E8621B;
  --orange-light:    #FFF3E8;
  --blue:            #005F99;
  --blue-mid:        #1882C4;
  --blue-light:      #E0F0FF;
  --amber:           #B87800;
  --amber-light:     #FFFAE0;
  --teal:            #097860;
  --teal-light:      #E0F5EF;
  --purple:          #5E35A8;
  --purple-light:    #F2ECFC;
  --green:           #256B3A;
  --green-light:     #E4F3EA;
  --red:             #B03020;
  --text:            #1C1C2E;
  --muted:           #5A6070;
  --rule:            #E0E4EA;
  --scientist:       #4A1580;
  --scientist-mid:   #7B2FBE;
  --scientist-light: #F3EAFF;
}

body {
  font-family: 'Noto Sans Devanagari', 'Mangal', 'Kokila', sans-serif;
  font-size: 8.5pt;
  line-height: 1.5;
  color: var(--text);
  counter-reset: pg;
}

/* ── Page counter ────────────────────────────────────── */
.page { counter-increment: pg; }

.pg-footer {
  text-align: center;
  font-size: 6pt;
  color: var(--muted);
  padding: 1.5mm 0 1mm;
  border-top: 0.5px solid var(--rule);
  flex-shrink: 0;
}
.pg-footer::after { content: counter(pg); }

.ans-xref {
  font-size: 7pt;
  color: var(--muted);
  text-align: right;
  margin-top: 5px;
  font-style: italic;
}

/* ── Print ─────────────────────────────────────────── */
@page { size: 130mm 198mm; margin: 0; }

@media print {
  body { background: white; }
  .page { page-break-after: always; }
}

/* ── Screen preview ─────────────────────────────────── */
@media screen {
  body { background: #b8bec8; padding: 8mm; }
  .page {
    width: 130mm;
    min-height: 198mm;
    margin: 8mm auto;
    background: white;
    box-shadow: 0 5px 22px rgba(0,0,0,0.35);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
}

/* ── Page shell ──────────────────────────────────────── */
.page { display: flex; flex-direction: column; }

/* ── Colour band (header) ────────────────────────────── */
.page-band {
  display: flex;
  align-items: flex-start;
  gap: 4mm;
  padding: 4.5mm 5mm 4mm;
}

.morning-band {
  background: linear-gradient(120deg, var(--orange) 0%, var(--orange-mid) 55%, #F07830 100%);
  color: white;
}

.evening-band {
  background: linear-gradient(120deg, var(--blue) 0%, var(--blue-mid) 55%, #28A0E0 100%);
  color: white;
}

.scientist-band {
  background: linear-gradient(120deg, var(--scientist) 0%, var(--scientist-mid) 55%, #A855F7 100%);
  color: white;
}

.scientist-box {
  background: var(--scientist-light);
  border-left: 4px solid var(--scientist-mid);
  border-radius: 0 6px 6px 0;
  padding: 6px 9px;
  margin: 5px 0 8px;
  page-break-inside: avoid;
}

.band-divider {
  width: 0.5mm;
  background: rgba(255,255,255,0.35);
  align-self: stretch;
  margin: 1mm 0;
  border-radius: 1mm;
}

.band-middle { flex: 1; }

.band-session {
  font-size: 7pt;
  opacity: 0.85;
  margin-bottom: 1.5mm;
  letter-spacing: 0.2pt;
}

.band-topic {
  font-size: 10.5pt;
  font-weight: 700;
  line-height: 1.25;
}

/* ── Page body ───────────────────────────────────────── */
.page-body {
  flex: 1;
  padding: 4mm 5.5mm 3.5mm;
  display: flex;
  flex-direction: column;
}

.page-content { flex: 1; overflow: hidden; }

/* ── Scientist card ──────────────────────────────────── */
.scientist-card {
  float: right;
  margin: 0 0 5mm 5mm;
  width: 34mm;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 3px 10px rgba(0,0,0,0.22);
  border: 2px solid var(--rule);
}

.scientist-card img { width: 100%; height: auto; display: block; }

/* ── Topic image card ────────────────────────────────── */
.topic-img-card {
  float: right;
  margin: 0 0 5mm 5mm;
  width: 36mm;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 3px 10px rgba(0,0,0,0.22);
  border: 2px solid var(--rule);
}

.topic-img-card img { width: 100%; height: auto; display: block; }

/* ── Day icon (non-scientist pages) ─────────────────── */
.day-icon-card {
  float: right;
  margin: 0 0 5mm 5mm;
  width: 26mm;
  height: 26mm;
  border-radius: 50%;
  background: var(--orange-light);
  border: 2.5px solid var(--orange);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22pt;
  box-shadow: 0 2px 8px rgba(200,78,10,0.18);
}

/* evening pages: icon uses blue palette */
.evening-page .day-icon-card {
  background: var(--blue-light);
  border-color: var(--blue);
  box-shadow: 0 2px 8px rgba(0,95,153,0.18);
}

/* ── Typography ──────────────────────────────────────── */
.page-content p  { margin-bottom: 4px; line-height: 1.5; }
.page-content strong { font-weight: 700; }
.page-content em     { font-style: italic; }
.page-content ul, .page-content ol { margin-left: 14px; margin-bottom: 4px; }
.page-content li { margin-bottom: 2px; }

hr.separator { border: none; border-top: 1.5px solid var(--rule); margin: 4px 0; }

/* ── Content boxes ───────────────────────────────────── */

/* 💡 Fact box */
.fact-box {
  background: var(--amber-light);
  border-left: 4px solid var(--amber);
  border-radius: 0 6px 6px 0;
  padding: 4px 8px 4px 9px;
  margin: 5px 0;
  page-break-inside: avoid;
  font-size: 8pt;
}

/* 📦 Materials box */
.materials-box {
  background: var(--green-light);
  border: 1.5px solid #9ACBA5;
  border-radius: 6px;
  padding: 4px 7px;
  margin: 4px 0;
  page-break-inside: avoid;
}

.section-label {
  font-weight: 700;
  font-size: 7.5pt;
  margin-bottom: 3px;
}

.materials-box .section-label { color: var(--green); }
.materials-box ul { margin-left: 12px; }

/* 📋 Steps box */
.steps-box {
  background: var(--teal-light);
  border: 1.5px solid #7FCFBB;
  border-radius: 6px;
  padding: 4px 7px;
  margin: 4px 0;
  page-break-inside: avoid;
}

.steps-box .section-label { color: var(--teal); }

.steps-box ol {
  list-style: none;
  margin-left: 0;
  counter-reset: step-ctr;
}

.steps-box ol li {
  counter-increment: step-ctr;
  display: flex;
  align-items: flex-start;
  gap: 5px;
  margin-bottom: 3px;
}

.steps-box ol li::before {
  content: counter(step-ctr);
  background: var(--teal);
  color: white;
  font-size: 6.5pt;
  font-weight: 700;
  min-width: 5mm;
  height: 5mm;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 0.5mm;
}

/* 🟢 Science explanation box */
.science-box {
  background: var(--green-light);
  border-left: 4px solid var(--green);
  border-radius: 0 6px 6px 0;
  padding: 4px 8px 4px 9px;
  margin: 5px 0;
  page-break-inside: avoid;
  font-size: 8pt;
}

/* ⚠️ Warning box */
.warning-box {
  background: #FFF8E1;
  border-left: 4px solid #F4B400;
  border-radius: 0 6px 6px 0;
  padding: 3px 8px 3px 9px;
  margin: 4px 0;
  font-size: 7.5pt;
}

/* 📜 Verse / riddle box */
.verse-box {
  background: var(--purple-light);
  border-left: 4px solid var(--purple);
  border-radius: 0 6px 6px 0;
  padding: 6px 10px 6px 12px;
  margin: 5px 0;
  font-style: italic;
  line-height: 1.85;
  page-break-inside: avoid;
}

/* Table */
.content-table {
  border-collapse: collapse;
  width: 100%;
  margin: 4px 0;
  font-size: 7.5pt;
}
.content-table th, .content-table td { border: 1px solid #ccc; padding: 2px 5px; }
.content-table th { background: #F0F0F0; font-weight: 700; }

/* ── Observation box ─────────────────────────────────── */
.observation-box {
  border: 1.5px dashed #8090A0;
  border-radius: 7px;
  padding: 5px 8px;
  margin-top: 7px;
  background: #F5F8FC;
  page-break-inside: avoid;
}

.obs-title {
  font-weight: 700;
  font-size: 8.5pt;
  color: #3A4A5A;
  margin-bottom: 5px;
}

.obs-line {
  border-bottom: 1px solid #C0CBD8;
  height: 6.5mm;
  margin-bottom: 2.5px;
}

.obs-line.wide { height: 9mm; }

.obs-draw {
  border: 1.5px dashed #B0C0CC;
  border-radius: 5px;
  height: 22mm;
  margin-top: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #A0B0BC;
  font-size: 7.5pt;
  font-style: italic;
  background: white;
}

.riddle-obs { border-color: var(--purple); background: var(--purple-light); }
.riddle-obs .obs-title { color: var(--purple); }
.riddle-obs .obs-line  { border-color: #C5B0E0; }

/* ── Cover page ──────────────────────────────────────── */
.cover-page { min-height: 210mm; overflow: hidden; }

.cover-top {
  background: linear-gradient(145deg, var(--orange) 0%, #9B30D0 50%, var(--blue) 100%);
  padding: 14mm 8mm 10mm;
  text-align: center;
  color: white;
}

.cover-emoji-row {
  font-size: 20pt;
  letter-spacing: 3mm;
  margin-bottom: 6mm;
}

.cover-title {
  font-size: 26pt;
  font-weight: 700;
  margin-bottom: 3mm;
  text-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

.cover-subtitle {
  font-size: 10pt;
  opacity: 0.92;
  margin-bottom: 4mm;
}

.cover-period {
  font-size: 8.5pt;
  opacity: 0.8;
  border-top: 1px solid rgba(255,255,255,0.3);
  padding-top: 3mm;
  display: inline-block;
}

.cover-bottom {
  flex: 1;
  background: #F7F8FA;
  padding: 7mm 6mm 5mm;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.cover-section-label {
  font-size: 7.5pt;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.8pt;
  margin-bottom: 4mm;
}

.cover-chips {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2.5mm;
}

.cover-chip {
  background: white;
  border: 1px solid var(--rule);
  border-radius: 20px;
  padding: 2.5px 8px;
  font-size: 7.5pt;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.07);
  color: var(--text);
}

.cover-badge {
  text-align: center;
  margin-top: 5mm;
  font-size: 8pt;
  color: var(--muted);
  border-top: 1px solid var(--rule);
  padding-top: 4mm;
}

/* ── Appendix ────────────────────────────────────────── */
.appendix-band {
  display: flex;
  align-items: center;
  gap: 3mm;
  padding: 5mm 6mm 4mm;
  background: linear-gradient(120deg, var(--green) 0%, var(--teal) 100%);
  color: white;
}

.appendix-band-icon  { font-size: 20pt; }
.appendix-band-title { font-size: 13pt; font-weight: 700; }

.appendix-page .page-body h2 {
  font-size: 9.5pt;
  font-weight: 700;
  color: var(--green);
  margin: 8px 0 4px;
  padding-bottom: 2px;
  border-bottom: 1.5px solid #C0DCC8;
}

.appendix-page .page-body h3 {
  font-size: 8.5pt;
  font-weight: 600;
  color: var(--muted);
  margin: 7px 0 3px;
}

.answer-table {
  border-collapse: collapse;
  width: 100%;
  margin: 4px 0;
  font-size: 8pt;
}
.answer-table th, .answer-table td { border: 1px solid #ccc; padding: 3px 7px; }
.answer-table th { background: var(--green-light); font-weight: 700; }

/* ── Scientists section page ─────────────────────────── */
.scientists-section-page { min-height: 198mm; overflow: hidden; display: flex; flex-direction: column; }

.sci-sec-top {
  background: linear-gradient(145deg, var(--scientist) 0%, var(--scientist-mid) 55%, #A855F7 100%);
  padding: 18mm 8mm 12mm;
  text-align: center;
  color: white;
}

.sci-sec-icon-row {
  font-size: 18pt;
  letter-spacing: 3mm;
  margin-bottom: 6mm;
}

.sci-sec-title {
  font-size: 30pt;
  font-weight: 700;
  margin-bottom: 3mm;
  text-shadow: 0 2px 8px rgba(0,0,0,0.3);
}

.sci-sec-subtitle {
  font-size: 9pt;
  opacity: 0.88;
}

.sci-sec-body {
  flex: 1;
  background: var(--scientist-light);
  padding: 8mm 7mm 6mm;
  display: flex;
  flex-direction: column;
  gap: 5mm;
}

.sci-sec-label {
  font-size: 7.5pt;
  font-weight: 700;
  color: var(--scientist);
  text-transform: uppercase;
  letter-spacing: 0.8pt;
}

.sci-sec-chips {
  display: flex;
  flex-direction: column;
  gap: 2.5mm;
}

.sci-sec-chip {
  background: white;
  border: 1.5px solid var(--scientist-mid);
  border-radius: 8px;
  padding: 3px 10px;
  font-size: 8.5pt;
  font-weight: 600;
  color: var(--scientist);
  box-shadow: 0 1px 4px rgba(74,21,128,0.1);
}

.sci-sec-note {
  font-size: 7.5pt;
  color: var(--muted);
  line-height: 1.6;
  border-top: 1px solid #D8C8F0;
  padding-top: 4mm;
}

/* ── Blog-style scientist profile layout ─────────────── */
.scientist-page .page-content { overflow: visible; }

.sci-profile {
  display: flex;
  gap: 3.5mm;
  margin-bottom: 3mm;
  align-items: stretch;
}

.sci-profile-left {
  width: 30mm;
  flex-shrink: 0;
  background: var(--scientist-light);
  border-radius: 5px;
  padding: 2mm 1.5mm 2mm;
  display: flex;
  flex-direction: column;
  gap: 2mm;
}

.sci-profile-left img {
  width: 100%;
  border-radius: 4px;
  border: 2px solid var(--scientist-mid);
  box-shadow: 0 2px 8px rgba(74,21,128,0.2);
  display: block;
}

.sci-meta-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 5.5pt;
  flex: 1;
}

.sci-meta-table td {
  padding: 1.5px 2px;
  vertical-align: top;
  line-height: 1.45;
  color: var(--muted);
}

.sci-meta-table td:first-child {
  font-weight: 700;
  color: var(--scientist-mid);
  white-space: nowrap;
  padding-right: 3px;
}

.sci-profile-right { flex: 1; min-width: 0; padding-top: 1mm; }

.sci-name {
  font-size: 10.5pt;
  font-weight: 700;
  color: var(--scientist);
  line-height: 1.3;
  margin-bottom: 1.5px;
  overflow: visible;
}

.sci-subtitle {
  font-size: 6.5pt;
  color: var(--scientist-mid);
  font-weight: 600;
  margin-bottom: 2.5mm;
}

.sci-tag {
  display: inline-block;
  background: white;
  border: 1px solid var(--scientist-mid);
  border-radius: 20px;
  font-size: 6pt;
  color: var(--scientist);
  padding: 1px 6px;
  margin-bottom: 2.5mm;
}

.sci-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  margin-top: 3mm;
  padding-top: 2.5mm;
  border-top: 1px solid #D8C8F0;
}

.sci-chip {
  background: var(--scientist-light);
  color: var(--scientist);
  font-size: 6pt;
  font-weight: 600;
  padding: 1.5px 5px;
  border-radius: 20px;
  border: 1px solid var(--scientist-mid);
}
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate():
    BOOK_DIR.mkdir(exist_ok=True)

    all_days = []
    for f in collect_plan_files():
        days = parse_plan_file(f)
        print(f'  {f.name}: {len(days)} days')
        all_days.extend(days)

    print(f'Total: {len(all_days)} days')

    regular_days   = [d for d in all_days if not d['scientist_img']]
    scientist_days = [d for d in all_days if d['scientist_img']]

    # Compute page numbers:
    # 1 cover + 2*regular + 1 sci-section + 2*scientist + 1 appendix
    appendix_page_num = 1 + len(regular_days) * 2 + 1 + len(scientist_days) * 2 + 1

    # Map day_number -> evening page number for riddle days
    riddle_page_nums = {}
    for i, day in enumerate(regular_days):
        if day['evening_type'] == 'riddle':
            riddle_page_nums[day['number']] = 1 + i * 2 + 2  # cover=1, morning=+1, evening=+2

    pages = [cover_page()]
    for day in regular_days:
        pages.append(morning_page(day))
        pages.append(evening_page(day, appendix_page_num))
    pages.append(scientists_section_page(scientist_days))
    for day in scientist_days:
        pages.append(morning_page(day))
        pages.append(evening_page(day))
    pages.append(answers_appendix(all_days, riddle_page_nums))

    html = f"""<!DOCTYPE html>
<html lang="mr">
<head>
  <meta charset="UTF-8">
  <title>विज्ञानाचा रंजक शोध</title>
  <style>
{CSS}
  </style>
</head>
<body>
{''.join(pages)}
</body>
</html>"""

    out = BOOK_DIR / 'vidnyan-ranjan-pustak.html'
    out.write_text(html, encoding='utf-8')
    print(f'\nDone → {out}')
    print('Chrome → Print → Save as PDF → Custom 130×198mm → No margins')


if __name__ == '__main__':
    generate()

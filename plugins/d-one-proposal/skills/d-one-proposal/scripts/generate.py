#!/usr/bin/env python3
"""
Generate an interactive D-One client proposal HTML file.
Embeds images as base64. Outputs a single self-contained index.html.

Usage:
    python generate.py --client "Smith Residence" --project "Constantia" --output /tmp/proposal/
"""

import os
import sys
import base64
import argparse
import json

SKILL_DIR  = os.path.join(os.path.dirname(__file__), '..')
IMAGES_DIR = os.path.join(SKILL_DIR, 'assets', 'images')
LOGO_PATH  = os.path.join(SKILL_DIR, 'assets', 'logo.png')

SYSTEMS = [
    ('cctv',               'CCTV'),
    ('access-control',     'Access Control'),
    ('network',            'Network & Wi-Fi'),
    ('audio',              'Audio'),
    ('home-theatre',       'Home Theatre'),
    ('lighting',           'Lighting Control'),
    ('system-integration', 'System Integration'),
]

CATEGORIES = [
    ('security',           'Security',           ['cctv', 'access-control']),
    ('it',                 'IT',                 ['network']),
    ('audiovisual',        'Audio Visual',       ['audio', 'home-theatre']),
    ('system-integration', 'System Integration', ['lighting', 'system-integration']),
]

TIERS = ['Entry', 'Mid', 'Premium']

NOT_REQUIRED_LABELS = {
    'cctv':               "We don't need CCTV",
    'access-control':     "We don't need Access Control",
    'network':            "We don't need a new Network",
    'audio':              "We don't need Audio",
    'home-theatre':       "We don't need a Home Theatre",
    'lighting':           "We don't need Lighting Control",
    'system-integration': "We don't need System Integration",
}

# Fixed entry points for Access Control facial recognition readers
ACCESS_CONTROL_READERS = [
    ('vehicle-gate',    'Vehicle Gate'),
    ('pedestrian-gate', 'Pedestrian Gate'),
    ('front-door',      'Front Door'),
    ('back-door',       'Back Door'),
    ('server-room',     'Server Room'),
    ('cellar',          'Cellar'),
    ('plant-room',      'Plant Room'),
]

# Default room list for Audio zones (override per proposal via audio_zones param)
DEFAULT_AUDIO_ZONES = [
    # Interior — living spaces
    ('entrance-hall',  'Entrance Hall'),
    ('living-room',    'Living Room'),
    ('lounge',         'Lounge'),
    ('dining-room',    'Dining Room'),
    ('kitchen',        'Kitchen'),
    ('scullery',       'Scullery'),
    ('study',          'Study'),
    ('library',        'Library'),
    ('gym',            'Gym'),
    ('games-room',     'Games Room'),
    ('wine-cellar',    'Wine Cellar'),
    # Bedrooms
    ('master-bed',     'Master Bedroom'),
    ('guest-bed-1',    'Guest Bedroom 1'),
    ('guest-bed-2',    'Guest Bedroom 2'),
    ('guest-bed-3',    'Guest Bedroom 3'),
    ('kids-room',      'Kids Room'),
    # Outdoor & entertaining
    ('covered-patio',  'Covered Patio'),
    ('open-terrace',   'Open Terrace'),
    ('pool-deck',      'Pool Deck'),
    ('braai-area',     'Braai Area'),
    ('garden',         'Garden'),
    ('balcony',        'Balcony'),
    ('rooftop',        'Rooftop Terrace'),
    # Service & utilities
    ('garage',         'Garage'),
    ('staff-quarters', 'Staff Quarters'),
]

# Default per-unit prices for zone selectors (override via zone_prices param)
DEFAULT_ZONE_PRICES = {
    'audio':          55121,  # per room — includes Sonos Amp + speakers + cable + labour
    'access-control': 25000,  # per facial recognition reader
}

def img_b64(path):
    if not path or not os.path.exists(path):
        return None
    ext = path.rsplit('.', 1)[-1].lower()
    mime = {'webp': 'image/webp', 'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg'}.get(ext, 'image/png')
    with open(path, 'rb') as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:{mime};base64,{data}"

def best_image(system_slug, tier_name):
    """Return base64 data URI for the most recently modified image for this system+tier.
    Matches exact filenames (entry.webp) AND prefixed variants (entry_clean.png, entry_trim.png).
    Always picks the newest file by mtime so replacements just need a later timestamp.
    """
    folder = os.path.join(IMAGES_DIR, system_slug)
    tier_lower = tier_name.lower()
    valid_exts = {'webp', 'png', 'jpg', 'jpeg'}
    candidates = []
    if os.path.exists(folder):
        for fname in os.listdir(folder):
            if '.' not in fname:
                continue
            stem, ext = fname.rsplit('.', 1)
            if ext.lower() not in valid_exts:
                continue
            # Match exact tier name OR tier name as a prefix (e.g. entry_clean, entry_trim)
            if stem.lower() == tier_lower or stem.lower().startswith(tier_lower + '_'):
                fpath = os.path.join(folder, fname)
                candidates.append((os.path.getmtime(fpath), fpath))
    if candidates:
        candidates.sort(reverse=True)  # newest first
        return img_b64(candidates[0][1])
    return None

CONTENT = {
    'cctv': {
        'Entry': "Cameras are the UniFi series — a professional-grade system used worldwide for its reliability and picture quality. Entry level covers key viewing points on the outside of the building. All footage is recorded locally on a dedicated NVR and kept for several weeks. You can view any camera live from your phone, anywhere in the world. The system includes intelligent intruder detection — it can tell the difference between a person and a passing car. Off-site monitoring companies act as a live verification to respond in realtime if intruders are detected.",
        'Mid':   "Everything in Entry, plus a set of perimeter cameras positioned around the boundary of the property. These give you early detection — you'll know something is approaching long before it reaches the building. The perimeter cameras are higher resolution with adjustable lenses, so coverage can be fine-tuned to suit your specific property layout. They also carry more advanced AI detection, able to identify and classify movement with greater accuracy and fewer false alerts.",
        'Premium': "Everything in Mid, plus an active deterrent layer. Selected cameras are equipped with integrated spotlights, speakers and sensors. When an intruder crosses a boundary we've set in the camera view, the spotlights activate automatically and your offsite monitoring team can speak directly to the intruder in real time. The system also includes cameras that can automatically track and follow a person once detected, keeping them in frame without any manual control. This is a fully active security system, not just a recording one.",
    },
    'access-control': {
        'Entry': "Your gate has a video intercom station where visitors can ring for entry. You can answer from a screen inside the house, see the visitor clearly on video, speak to them and let them in — all without going to the gate. The same call can be answered from your phone if you're not home, so you always know who's at your gate, wherever you are. Intercom screens are installed in the key areas of the home so there's always one nearby.",
        'Mid':   "Everything in Entry, plus facial recognition at key entry points. Registered residents are recognised automatically and granted access without needing a key, card or code — they simply approach and the gate or door opens. Temporary access can be set up for guests, cleaners or contractors, and expires automatically when no longer needed. All access is managed by the owners through an app.",
        'Premium': "Everything in Mid, plus full integration into a single unified system for the whole home. No separate remotes, keypads, touch panels or apps for different things — one elegant interface controls everything: intercom, gate, lights, music, air conditioning, access and more. It's the simplest possible experience: one system, everything in one place, nothing to figure out.",
    },
    'network': {
        'Entry': "This is the best-value option for most homes. It provides excellent routing, security, VPN and network management, while the access points deliver fast Wi-Fi 7 performance for phones, laptops, TVs and smart home devices. Ideal for typical residential use — streaming, video calls, gaming and smart home systems — offering excellent performance without paying for features most devices can't yet fully utilise.",
        'Mid':   "Designed for larger homes and more demanding networks. The hardware is faster and delivers a stronger Wi-Fi signal, with access points that support higher Wi-Fi capacity and faster uplinks, making them better suited to environments with many simultaneous users, heavy streaming, large file transfers and future expansion.",
        'Premium': "A flagship solution for ultra-premium homes and power users who want the highest possible performance available today. Significantly greater processing power, with access points that support the fastest wireless speeds and highest device densities in the range. Best suited for very large properties, advanced smart home systems, multiple high-speed internet services, media servers, and anyone who wants maximum future-proofing.",
    },
    'audio': {
        'Entry': "In-ceiling speakers installed in the main entertainment areas of the home, providing quality background music wherever you spend most of your time. Simple to use from your phone. Audio is not distributed to every room, keeping the system straightforward and cost-effective.",
        'Mid':   "Everything in Entry, plus higher-quality in-ceiling speakers for a more refined listening experience where it matters most. Subwoofers can be added to specific areas to deliver a fuller, richer sound — ideal for lounges or entertaining spaces where you want audio that goes beyond background music.",
        'Premium': "Everything in Mid, with three premium directions depending on your preference. For spaces where aesthetics are everything, completely invisible speakers plastered directly into the wall or ceiling. For ultimate performance, we work with the world's most prestigious audio brands. And for spaces where the speaker can be part of the design, Bang & Olufsen offers customisable finishes that complement your interiors. Budget for this option depends on the specific choices and preferences selected.",
    },
    'home-theatre': {
        'Entry': "For a TV room that needs a bit of excitement for movies and sport. Surround sound speakers to match the space.",
        'Mid':   "A more dedicated cinema room designed to draw viewers fully into the experience. Carefully chosen speakers, placement and acoustic treatment create a genuinely immersive environment where the audio surrounds you — not just fills the room. A significant step up from a TV room, built for those who take movies and sport seriously.",
        'Premium': "A custom-designed home cinema, built to present content exactly the way the creators intended. Every element — screen size, projector or display, speaker placement, acoustic panels and lighting — is engineered together as a single system. The result is a cinema in the comfort of your own home. Budget for this option depends on the specific design and preferences.",
    },
    'lighting': {
        'Entry': "Lighting control in the main entertainment areas and master bedroom only. When lights come on they go to the right level — no hunting for the correct switch. Easy to adjust from a single point without a bank of switches. Scenes like \"Good Night\" work for the controlled areas. This keeps costs to a minimum.",
        'Mid':   "Everything in Entry, with beautiful architectural light switches that are designed to complement the interior of the home. Switches have engraved labels — so the right button is always obvious, making the system even easier to use.",
        'Premium': "Every light in the home on one system — inside and out. Garden lights come on automatically at sunset. Every room is set to the right level with a single press, easy dimming up or down as needed. One touch turns off the whole house, or sets it perfectly for dinner, entertaining, winding down for the evening. Switch finishes are selected to match the look and feel of each space.",
    },
    'system-integration': {
        'Entry': "Music, lights and access consolidated into one app and one touch panel. One place, everything you use every day.",
        'Mid':   "Everything in Entry, expanded to include air conditioning, gates, doors and TVs. All the systems you interact with daily, controlled from one app and one touch panel.",
        'Premium': "One system that controls everything. Lights, music, TVs, air conditioning, underfloor heating, heated towel rails, gates, doors, blinds, home cinema and AV — all from one touch panel or app. No separate remotes on the coffee table, no separate apps, no wall clutter. The house responds to you, not the other way around. Blinds are quoted separately depending on the number of windows and motor type.",
    },
}

def render_conduit_schedule(conduit_data):
    """Render conduit JSON data as a styled HTML table section."""
    project = conduit_data.get('project_name', 'Conduit Schedule')
    sections_html = ''
    for section in conduit_data.get('sections', []):
        level = section.get('level', '')
        areas_html = ''
        for area in section.get('areas', []):
            area_name = area.get('name', '')
            rows_html = ''
            for i, item in enumerate(area.get('items', [])):
                bg = '#f4f6f9' if i % 2 == 0 else '#ffffff'
                rows_html += f"""
              <tr style="background:{bg};">
                <td style="padding:8px 12px;font-size:12px;color:#1a1a2e;">{item.get('point','')}</td>
                <td style="padding:8px 12px;font-size:12px;color:#1a1a2e;text-align:center;">{item.get('conduit','')}</td>
                <td style="padding:8px 12px;font-size:12px;color:#1a1a2e;">{item.get('destination','')}</td>
                <td style="padding:8px 12px;font-size:12px;color:#1a1a2e;">{item.get('cable','')}</td>
                <td style="padding:8px 12px;font-size:12px;color:#1a1a2e;text-align:center;">{item.get('backbox','')}</td>
                <td style="padding:8px 12px;font-size:12px;color:#1a1a2e;text-align:center;">{item.get('power','')}</td>
              </tr>"""
            areas_html += f"""
            <tr>
              <td colspan="6" style="padding:10px 12px;background:#2a5fa8;color:#fff;font-size:12px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;">{area_name}</td>
            </tr>
            {rows_html}"""
        sections_html += f"""
          <tr>
            <td colspan="6" style="padding:12px 16px;background:#1379C9;color:#fff;font-size:13px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;">{level}</td>
          </tr>
          {areas_html}"""
    return f"""
  <div style="background:#fff;padding:48px 0 64px;">
    <div style="max-width:1320px;margin:0 auto;padding:0 60px;">
      <div style="background:#0a1628;color:#fff;padding:20px 28px;margin-bottom:0;">
        <span style="font-family:sans-serif;font-size:14px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;">Conduit Schedule — For Electrician</span>
        <span style="font-family:sans-serif;font-size:12px;opacity:0.6;margin-left:20px;">{project}</span>
      </div>
      <table style="width:100%;border-collapse:collapse;font-family:sans-serif;">
        <thead>
          <tr style="background:#0a1628;">
            <th style="padding:10px 12px;color:#fff;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;text-align:left;">Point</th>
            <th style="padding:10px 12px;color:#fff;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;text-align:center;">Conduit</th>
            <th style="padding:10px 12px;color:#fff;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;text-align:left;">Destination</th>
            <th style="padding:10px 12px;color:#fff;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;text-align:left;">Cable</th>
            <th style="padding:10px 12px;color:#fff;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;text-align:center;">Backbox</th>
            <th style="padding:10px 12px;color:#fff;font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;text-align:center;">Power</th>
          </tr>
        </thead>
        <tbody>
          {sections_html}
        </tbody>
      </table>
    </div>
  </div>"""


def make_zone_panel(system_slug, zones, per_unit_price, prompt, tiers_that_show):
    """
    Build the HTML for a zone/reader selector panel.
    zones:           list of (zone_id, zone_label)
    tiers_that_show: list of tier names that trigger this panel to show, e.g. ['Mid','Premium']
    """
    price_fmt = f"R {per_unit_price:,.0f}"
    zone_items = ''
    for zone_id, zone_label in zones:
        zone_items += f'''
              <label class="zone-item">
                <input type="checkbox" class="zone-cb"
                       data-system="{system_slug}"
                       data-zone="{zone_id}"
                       data-price="{per_unit_price}"
                       onchange="onZoneChange('{system_slug}')">
                <span class="zone-name">{zone_label}</span>
                <span class="zone-price">+ {price_fmt}</span>
              </label>'''
    return f'''
        <div class="zone-panel" id="zone-panel-{system_slug}"
             data-show-tiers="{json.dumps(tiers_that_show).replace('"', '&quot;')}"
             style="display:none;">
          <div class="zone-panel-header">
            <span class="zone-prompt">{prompt}</span>
            <span class="zone-subtext">Each adds {price_fmt} to your estimate</span>
          </div>
          <div class="zone-grid">
            {zone_items}
          </div>
          <div class="zone-summary">
            <span class="zone-summary-label">Selected</span>
            <span class="zone-summary-items" id="zone-items-{system_slug}">—</span>
            <span class="zone-summary-add" id="zone-add-{system_slug}"></span>
          </div>
        </div>'''


def format_budget(val):
    if val is None or val == 'TBD':
        return 'TBD'
    if isinstance(val, (int, float)):
        return f"R {val:,.0f}"
    return str(val)

def generate_html(client_name, project_name, budgets, logo_b64=None, cover_image_b64=None, plan_images_b64=None,
                  audio_zones=None, zone_prices=None, conduit_html=None):
    """
    budgets:          dict like {'cctv': {'Entry': 45000, 'Mid': 85000, 'Premium': 150000}, ...}
    cover_image_b64:  base64 data URI for the project cover render (optional)
    plan_images_b64:  list of base64 data URIs for marked-up floor plans (optional)
    audio_zones:      list of (zone_id, zone_label) tuples for audio room checkboxes (default: DEFAULT_AUDIO_ZONES)
    zone_prices:      dict with per-unit prices e.g. {'audio': 8000, 'access-control': 25000}
    """
    if audio_zones is None:
        audio_zones = DEFAULT_AUDIO_ZONES
    if zone_prices is None:
        zone_prices = DEFAULT_ZONE_PRICES.copy()

    # Resolve audio zone price — support both a flat int (backwards-compatible)
    # and a per-tier dict {"Entry": N, "Mid": N, "Premium": N} from wequote-budget.
    _audio_price_raw = zone_prices.get('audio', DEFAULT_ZONE_PRICES['audio'])
    if isinstance(_audio_price_raw, dict):
        _audio_price_initial = _audio_price_raw.get('Entry', DEFAULT_ZONE_PRICES['audio'])
        _audio_zone_prices_for_js = {k: int(v) for k, v in _audio_price_raw.items()}
        audio_zone_js_extra = (
            '\n    const AUDIO_ZONE_PRICES = ' + json.dumps(_audio_zone_prices_for_js) + ';'
            '\n    function updateAudioZonePrices(tier) {'
            "\n      const price = AUDIO_ZONE_PRICES[tier] || AUDIO_ZONE_PRICES['Entry'];"
            "\n      document.querySelectorAll('#zone-panel-audio .zone-cb').forEach(cb => { cb.dataset.price = price; });"
            "\n      document.querySelectorAll('#zone-panel-audio .zone-price').forEach(el => {"
            "\n        el.textContent = '+ R ' + price.toLocaleString('en-US');"
            '\n      });'
            "\n      const subtext = document.querySelector('#zone-panel-audio .zone-subtext');"
            "\n      if (subtext) subtext.textContent = 'Each adds R ' + price.toLocaleString('en-US') + ' to your estimate';"
            '\n    }'
        )
        audio_zone_update_call = (
            "\n          if (system === 'audio' && typeof updateAudioZonePrices === 'function')"
            " { updateAudioZonePrices(tier); }"
        )
    else:
        _audio_price_initial = (
            int(_audio_price_raw) if isinstance(_audio_price_raw, (int, float))
            else DEFAULT_ZONE_PRICES['audio']
        )
        audio_zone_js_extra = ''
        audio_zone_update_call = ''

    # Build per-system JS data
    system_data = {}
    for slug, _ in SYSTEMS:
        system_data[slug] = {}
        for tier in TIERS:
            b = budgets.get(slug, {}).get(tier)
            system_data[slug][tier] = 0 if (b is None or b == 'TBD') else int(b)

    system_js = json.dumps(system_data)

    # Category JS mapping
    cat_sys_map = {cat_id: cat_systems for cat_id, _, cat_systems in CATEGORIES}
    cat_js = json.dumps(cat_sys_map)

    # ── COVER IMAGE ──
    if cover_image_b64:
        cover_img_html = f'<img src="{cover_image_b64}" class="cover-img" alt="Project render">'
    else:
        cover_img_html = '''<div class="cover-img-placeholder">
          <div class="placeholder-inner">
            <div class="placeholder-icon">⬜</div>
            <div class="placeholder-label">Project Render</div>
            <div class="placeholder-sub">Replace with your project image</div>
          </div>
        </div>'''

    # ── FLOOR PLANS SECTION ──
    if plan_images_b64 and len(plan_images_b64) > 0:
        # Stack vertically — one per row, full width
        plans_grid_items = ''.join(
            f'<div class="plan-item"><img src="{p}" class="plan-img" alt="Floor plan {i+1}"></div>'
            for i, p in enumerate(plan_images_b64)
        )
        plans_grid = f'<div class="plans-grid" style="grid-template-columns:1fr">{plans_grid_items}</div>'
    else:
        plans_grid = '''<div class="plans-grid plans-placeholder-grid">
          <div class="plan-placeholder">
            <div class="placeholder-inner">
              <div class="placeholder-label">Ground Floor Plan</div>
              <div class="placeholder-sub">Marked-up equipment layout</div>
            </div>
          </div>
          <div class="plan-placeholder">
            <div class="placeholder-inner">
              <div class="placeholder-label">First Floor Plan</div>
              <div class="placeholder-sub">Marked-up equipment layout</div>
            </div>
          </div>
        </div>'''

    design_banner = '''<div style="background:#0a1628;color:#fff;text-align:center;padding:32px 24px;font-size:1.4rem;letter-spacing:0.04em;font-style:italic;">&ldquo;Security, Wi-Fi and AV that disappears into the architecture.&rdquo;</div>'''
    plans_section = f'''
      {design_banner}
      <section class="plans-section">
        <div class="cat-inner">
          <div class="eyebrow">Project Plans</div>
          <div class="rule"></div>
          <p class="plans-note">Equipment layouts prepared for this project. Each system is marked on the drawings below.</p>
          {plans_grid}
        </div>
      </section>'''

    # ── CATEGORY SECTIONS ──
    category_sections = []
    for cat_id, cat_name, cat_systems in CATEGORIES:
        systems_html = []
        for sys_slug in cat_systems:
            sys_label = next(l for s, l in SYSTEMS if s == sys_slug)
            tiers_html = []
            for tier in TIERS:
                img_data = best_image(sys_slug, tier)
                contain_class = ' opt-img-contain' if (
                    sys_slug == 'lighting' or
                    (sys_slug == 'access-control' and tier in ('Entry', 'Mid'))
                ) else ''
                img_html = f'<img src="{img_data}" class="opt-img{contain_class}" alt="{tier}">' if img_data else '<div class="opt-img-placeholder"></div>'
                budget_val = budgets.get(sys_slug, {}).get(tier)
                budget_str = format_budget(budget_val)
                budget_class = 'budget-tbd' if (budget_val is None or budget_val == 'TBD') else 'budget-val'
                content_text = CONTENT.get(sys_slug, {}).get(tier, '')
                tiers_html.append(f'''
            <div class="opt-card" data-system="{sys_slug}" data-tier="{tier}" data-budget="{0 if (budget_val is None or budget_val == 'TBD') else int(budget_val)}" onclick="selectOption(this)">
              <div class="opt-tier">{tier}</div>
              {img_html}
              <div class="opt-body">
                <p class="opt-desc">{content_text}</p>
                <div class="{budget_class}">{budget_str}</div>
              </div>
            </div>''')
            # 4th option — system-specific "not required"
            none_label = NOT_REQUIRED_LABELS.get(sys_slug, f"We don't need {sys_label}")
            tiers_html.append(f'''
            <div class="opt-card opt-none" data-system="{sys_slug}" data-tier="none" data-budget="0" onclick="selectOption(this)">
              <div class="opt-tier" style="color:var(--stone);">Not Required</div>
              <div class="opt-body" style="justify-content:center;">
                <p class="opt-desc opt-none-label">{none_label}</p>
              </div>
            </div>''')

            # Zone / reader panel for audio and access-control
            zone_panel_html = ''
            if sys_slug == 'audio':
                zone_panel_html = make_zone_panel(
                    system_slug='audio',
                    zones=audio_zones,
                    per_unit_price=_audio_price_initial,
                    prompt='Which rooms would you like audio in?',
                    tiers_that_show=['Entry', 'Mid', 'Premium'],
                )
            elif sys_slug == 'access-control':
                zone_panel_html = make_zone_panel(
                    system_slug='access-control',
                    zones=ACCESS_CONTROL_READERS,
                    per_unit_price=zone_prices.get('access-control', 25000),
                    prompt='Which entry points need facial recognition readers?',
                    tiers_that_show=['Mid', 'Premium'],
                )

            systems_html.append(f'''
        <div class="system-section">
          <div class="sys-header">
            <div class="sys-eyebrow">{sys_label}</div>
            <div class="sys-instruction">Select one</div>
          </div>
          <div class="opt-grid">
            {"".join(tiers_html)}
          </div>
          {zone_panel_html}
        </div>''')

        category_sections.append(f'''
      <section class="cat-section" id="cat-{cat_id}">
        <div class="cat-inner">
          <div class="cat-header">
            <div class="eyebrow">{cat_name}</div>
            <div class="rule"></div>
            <p class="cat-header-sub">Click a card below to select your preference for each system. Your estimated budget updates automatically.</p>
          </div>
          {"".join(systems_html)}
          <div class="cat-budget" id="budget-{cat_id}">
            <span class="budget-label">ESTIMATED BUDGET — {cat_name.upper()}</span>
            <span class="budget-amount" id="amount-{cat_id}">Select your preferences above</span>
          </div>
        </div>
      </section>''')

    # ── BUDGET SUMMARY TABLE ──
    summary_rows = ''
    for cat_id, cat_name, cat_systems in CATEGORIES:
        # Build system label list for this category
        sys_labels = ', '.join(next(l for s, l in SYSTEMS if s == slug) for slug in cat_systems)
        summary_rows += f'''
          <tr class="summary-row" data-cat="{cat_id}">
            <td class="sum-cat">{cat_name}</td>
            <td class="sum-sys">{sys_labels}</td>
            <td class="sum-sel" id="sum-sel-{cat_id}">—</td>
            <td class="sum-amt" id="sum-amt-{cat_id}">—</td>
          </tr>'''

    summary_section = f'''
      <section class="summary-section" id="summary">
        <div class="cat-inner">
          <div class="eyebrow">Budget Summary</div>
          <div class="rule"></div>
          <p class="summary-note">Your selections across all categories. Adjust above at any time.</p>
          <table class="summary-table">
            <thead>
              <tr>
                <th>Category</th>
                <th>Systems</th>
                <th>Selection</th>
                <th>Estimate</th>
              </tr>
            </thead>
            <tbody>
              {summary_rows}
            </tbody>
          </table>
          <p class="summary-disclaimer">Estimates are indicative. Final pricing subject to detailed design and scope.</p>
        </div>
      </section>'''

    conduit_section_html = conduit_html if conduit_html else ''

    nav_logo = f'<img src="{logo_b64}" class="nav-logo" alt="D-One">' if logo_b64 else '<span style="color:var(--gold);font-family:var(--f-serif);font-size:18px;">D-One</span>'
    cover_logo = f'<img src="{logo_b64}" class="cover-logo" alt="D-One">' if logo_b64 else ''
    footer_logo = f'<img src="{logo_b64}" class="footer-logo" alt="D-One">' if logo_b64 else ''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{client_name} — Security, Wi-Fi & AV | D-One</title>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --dark:    #17140F;
      --dark2:   #211D16;
      --cream:   #F3EDE2;
      --cream2:  #EAE2D4;
      --gold:    #B8944A;
      --gold-lt: #D4AE6A;
      --stone:   #8C7E6B;
      --white:   #F8F3EB;
      --blue:    #1B72BE;
      --f-serif: 'Cormorant Garamond', Georgia, serif;
      --f-sans:  'DM Sans', Helvetica, sans-serif;
    }}
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ scroll-behavior: smooth; }}
    body {{ background: var(--dark); font-family: var(--f-sans); color: var(--white); }}

    /* ── NAV ── */
    nav {{
      position: sticky; top: 0; z-index: 100;
      background: var(--dark);
      border-bottom: 1px solid rgba(184,148,74,0.25);
      display: flex; align-items: center; justify-content: space-between;
      padding: 0 40px; height: 60px;
    }}
    .nav-logo {{ height: 28px; filter: brightness(0) invert(1); opacity: 0.7; }}
    .nav-links {{ display: flex; gap: 40px; list-style: none; }}
    .nav-links a {{
      font-family: var(--f-sans); font-size: 11px; font-weight: 400;
      letter-spacing: 0.2em; text-transform: uppercase;
      color: var(--stone); text-decoration: none; transition: color 0.2s;
    }}
    .nav-links a:hover, .nav-links a.active {{ color: var(--gold); }}

    /* ── COVER ── */
    .cover {{
      min-height: 100vh; background: var(--dark);
      display: grid; grid-template-columns: 1fr 1fr;
      position: relative; overflow: hidden;
    }}
    .cover-left {{
      display: flex; flex-direction: column; justify-content: center;
      padding: 100px 60px 80px 80px; position: relative;
    }}
    .cover-logo {{
      position: absolute; top: 48px; left: 80px;
      height: 32px; filter: brightness(0) invert(1); opacity: 0.7;
    }}
    .cover-right {{
      position: relative; overflow: hidden;
      background: rgba(184,148,74,0.04);
    }}
    .cover-img {{
      width: 100%; height: auto; object-fit: contain; display: block;
    }}
    .cover-img-placeholder {{
      width: 100%; height: 100%;
      display: flex; align-items: center; justify-content: center;
      border-left: 1px solid rgba(184,148,74,0.15);
    }}
    .placeholder-inner {{
      text-align: center;
      display: flex; flex-direction: column; align-items: center; gap: 12px;
    }}
    .placeholder-icon {{ font-size: 40px; opacity: 0.15; }}
    .placeholder-label {{
      font-family: var(--f-sans); font-size: 11px; font-weight: 400;
      letter-spacing: 0.2em; text-transform: uppercase; color: var(--stone);
    }}
    .placeholder-sub {{
      font-family: var(--f-sans); font-size: 11px; color: rgba(140,126,107,0.5);
      letter-spacing: 0.08em;
    }}
    .eyebrow {{
      font-family: var(--f-sans); font-size: 11px; font-weight: 400;
      letter-spacing: 0.22em; text-transform: uppercase;
      color: var(--gold); margin-bottom: 24px;
    }}
    .cover-title {{
      font-family: var(--f-serif);
      font-size: clamp(40px, 4.5vw, 72px);
      font-weight: 300; line-height: 1.05;
      letter-spacing: -0.01em; color: var(--white);
    }}
    .rule {{
      width: 48px; height: 1px; background: var(--gold); margin: 36px 0;
    }}
    .cover-body {{
      font-family: var(--f-sans); font-size: 15px; font-weight: 300;
      line-height: 1.7; color: var(--stone); max-width: 420px;
    }}
    .cover-contact {{
      margin-top: 48px; font-size: 10px; letter-spacing: 0.15em;
      text-transform: uppercase; color: rgba(184,148,74,0.45);
    }}

    /* ── COVER PHILOSOPHY LINE ── */
    .cover-philosophy {{
      margin-top: 24px; padding-top: 24px;
      border-top: 1px solid rgba(184,148,74,0.15);
      font-family: var(--f-sans); font-size: 12px; font-weight: 300;
      line-height: 1.7; color: rgba(184,148,74,0.55);
      max-width: 420px; letter-spacing: 0.03em;
      font-style: italic;
    }}

    /* ── PHILOSOPHY SECTION ── */
    .philosophy-section {{
      padding: 100px 0; background: var(--cream);
      border-top: 1px solid rgba(184,148,74,0.2);
    }}
    .philosophy-grid {{
      display: grid; grid-template-columns: 1fr 1.6fr; gap: 80px; align-items: start;
    }}
    .philosophy-title {{
      font-family: var(--f-serif); font-size: clamp(32px, 3.5vw, 56px);
      font-weight: 300; line-height: 1.1; letter-spacing: -0.01em;
      color: var(--dark); margin-bottom: 4px;
    }}
    .philosophy-left .eyebrow {{ color: var(--gold); }}
    .philosophy-left .rule {{ background: var(--gold); }}
    .philosophy-body {{
      font-family: var(--f-sans); font-size: 15px; font-weight: 300;
      line-height: 1.75; color: var(--stone); margin-bottom: 20px; max-width: 560px;
    }}
    .philosophy-pillars {{
      display: grid; grid-template-columns: repeat(3, 1fr);
      gap: 24px; margin-top: 40px; padding-top: 36px;
      border-top: 1px solid rgba(184,148,74,0.25);
    }}
    .pillar {{
      display: flex; flex-direction: column; gap: 8px;
    }}
    .pillar-label {{
      font-family: var(--f-serif); font-size: 18px; font-weight: 400;
      color: var(--dark); line-height: 1.2;
    }}
    .pillar-sub {{
      font-family: var(--f-sans); font-size: 12px; font-weight: 300;
      color: var(--stone); line-height: 1.5; letter-spacing: 0.02em;
    }}
    @media (max-width: 960px) {{
      .philosophy-grid {{ grid-template-columns: 1fr; gap: 40px; }}
      .philosophy-pillars {{ grid-template-columns: 1fr; gap: 20px; }}
    }}

    /* ── PLANS SECTION ── */
    .plans-section {{
      padding: 80px 0; background: var(--dark2);
      border-top: 1px solid rgba(184,148,74,0.12);
    }}
    .plans-note {{
      font-family: var(--f-sans); font-size: 13px; font-weight: 300;
      color: var(--stone); line-height: 1.65; margin-bottom: 40px; max-width: 560px;
    }}
    .plans-grid {{
      display: grid; grid-template-columns: 1fr 1fr; gap: 3px;
    }}
    .plan-item {{ overflow: hidden; }}
    .plan-img {{ width: 100%; display: block; object-fit: contain; background: #1a1710; }}
    .plans-placeholder-grid {{ min-height: 360px; }}
    .plan-placeholder {{
      background: rgba(184,148,74,0.04);
      border: 1px dashed rgba(184,148,74,0.2);
      display: flex; align-items: center; justify-content: center;
      min-height: 340px;
    }}

    /* ── CATEGORY SECTIONS ── */
    .cat-section {{
      padding: 80px 0; border-top: 1px solid rgba(184,148,74,0.12);
    }}
    .cat-section:nth-child(odd)  {{ background: var(--dark); }}
    .cat-section:nth-child(even) {{ background: var(--dark2); }}
    .cat-inner {{ max-width: 1320px; margin: 0 auto; padding: 0 60px; }}
    .cat-header {{ margin-bottom: 48px; }}
    .cat-header-sub {{
      margin-top: 16px;
      font-family: var(--f-sans); font-size: 12px; font-weight: 300;
      color: var(--stone); letter-spacing: 0.05em; opacity: 0.7;
    }}

    /* ── SYSTEM SUBSECTION ── */
    .system-section {{ margin-bottom: 72px; }}
    .sys-header {{
      display: flex; align-items: baseline; justify-content: space-between;
      margin-bottom: 20px; padding-bottom: 16px;
      border-bottom: 1px solid rgba(184,148,74,0.15);
    }}
    .sys-eyebrow {{
      font-family: var(--f-sans); font-size: 22px; font-weight: 300;
      letter-spacing: 0.08em; color: var(--white);
    }}
    .sys-instruction {{
      font-family: var(--f-sans); font-size: 11px; letter-spacing: 0.12em;
      text-transform: uppercase; color: var(--stone); opacity: 0.6;
    }}
    .sys-instruction::before {{
      content: '↓ '; font-size: 10px;
    }}

    /* ── OPTION CARDS — 4 options (Entry / Mid / Premium / Not Required) ── */
    .opt-grid {{
      display: grid; grid-template-columns: 1fr 1fr 1fr 0.35fr; gap: 2px;
    }}
    .opt-card {{
      background: var(--dark2);
      border: 1px dashed rgba(184,148,74,0.22);
      cursor: pointer;
      transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
      display: flex; flex-direction: column; position: relative;
    }}
    .cat-section:nth-child(odd)  .opt-card {{ background: #1A1710; }}
    .cat-section:nth-child(even) .opt-card {{ background: var(--dark); }}
    .opt-card:hover {{
      border: 3px solid var(--gold);
      box-shadow: 0 0 18px rgba(184,148,74,0.25), inset 0 0 0 1px rgba(184,148,74,0.1);
      background: rgba(184,148,74,0.06);
    }}
    .opt-card.selected {{
      border: 3px solid var(--gold);
      background: rgba(184,148,74,0.1);
      box-shadow: 0 0 24px rgba(184,148,74,0.3), inset 0 0 0 1px rgba(184,148,74,0.15);
    }}
    /* Selection indicator dot */
    .opt-card::after {{
      content: '';
      position: absolute; top: 16px; right: 16px;
      width: 14px; height: 14px; border-radius: 50%;
      border: 1.5px solid rgba(184,148,74,0.35);
      background: transparent;
      transition: background 0.15s, border-color 0.15s, box-shadow 0.15s;
    }}
    .opt-card:hover::after {{
      border-color: var(--gold); border-width: 2px;
      box-shadow: 0 0 6px rgba(184,148,74,0.4);
    }}
    .opt-card.selected::after {{
      background: var(--gold); border-color: var(--gold);
      box-shadow: 0 0 8px rgba(184,148,74,0.5);
    }}
    .opt-card.opt-none {{ opacity: 0.5; }}
    .opt-card.opt-none::after {{ border-color: rgba(140,126,107,0.3); }}
    .opt-card.opt-none:hover {{
      opacity: 0.8; border: 2px solid var(--stone);
      box-shadow: none; background: rgba(140,126,107,0.05);
    }}
    .opt-card.opt-none:hover::after {{ border-color: var(--stone); }}
    .opt-card.opt-none.selected {{
      opacity: 1; border: 2px solid var(--stone); box-shadow: none;
    }}
    .opt-card.opt-none.selected::after {{
      background: var(--stone); border-color: var(--stone); box-shadow: none;
    }}
    .opt-none-label {{
      font-family: var(--f-serif); font-size: 20px; font-weight: 300;
      color: var(--stone); text-align: center; font-style: italic; line-height: 1.4;
    }}
    .opt-tier {{
      font-family: var(--f-sans); font-size: 10px; font-weight: 500;
      letter-spacing: 0.22em; text-transform: uppercase;
      color: var(--gold); padding: 20px 20px 0; margin-bottom: 12px;
    }}
    .opt-img {{ width: 100%; height: 220px; object-fit: cover; display: block; }}
    .opt-img-contain {{ object-fit: contain; background: #111; }}
    .opt-img-placeholder {{
      width: 100%; height: 220px; background: rgba(184,148,74,0.05);
    }}
    .opt-body {{
      padding: 20px; flex: 1; display: flex; flex-direction: column; gap: 16px;
    }}
    .opt-desc {{
      font-family: var(--f-sans); font-size: 13px; font-weight: 300;
      line-height: 1.65; color: var(--stone); flex: 1;
    }}
    .budget-val {{
      font-family: var(--f-serif); font-size: 22px; font-weight: 400;
      color: var(--gold-lt); margin-top: 8px;
    }}
    .budget-tbd {{
      font-family: var(--f-sans); font-size: 11px; letter-spacing: 0.15em;
      text-transform: uppercase; color: rgba(184,148,74,0.4); margin-top: 8px;
    }}

    /* ── CATEGORY BUDGET TOTAL ── */
    .cat-budget {{
      display: flex; align-items: baseline; gap: 24px;
      margin-top: 48px; padding-top: 28px;
      border-top: 1px solid rgba(184,148,74,0.2);
    }}
    .budget-label {{
      font-family: var(--f-sans); font-size: 10px; font-weight: 400;
      letter-spacing: 0.22em; text-transform: uppercase; color: var(--stone);
    }}
    .budget-amount {{
      font-family: var(--f-serif); font-size: 36px; font-weight: 300; color: var(--gold);
    }}

    /* ── BUDGET SUMMARY TABLE ── */
    .summary-section {{
      padding: 80px 0; background: var(--cream);
      border-top: 1px solid rgba(184,148,74,0.2);
    }}
    .summary-section .eyebrow {{ color: var(--gold); }}
    .summary-section .rule {{ background: var(--gold); }}
    .summary-note {{
      font-family: var(--f-sans); font-size: 13px; font-weight: 300;
      color: var(--stone); line-height: 1.65; margin-bottom: 36px; max-width: 520px;
    }}
    .summary-table {{
      width: 100%; border-collapse: collapse;
      font-family: var(--f-sans);
    }}
    .summary-table thead tr {{
      border-bottom: 1px solid rgba(184,148,74,0.4);
    }}
    .summary-table th {{
      font-size: 10px; font-weight: 400; letter-spacing: 0.2em;
      text-transform: uppercase; color: var(--stone);
      padding: 0 20px 16px 0; text-align: left;
    }}
    .summary-table th:last-child {{ text-align: right; padding-right: 0; }}
    .summary-table .summary-row {{
      border-bottom: 1px solid rgba(184,148,74,0.12);
      transition: background 0.15s;
    }}
    .summary-table .summary-row td {{
      padding: 20px 20px 20px 0; vertical-align: middle;
    }}
    .summary-table .summary-row td:last-child {{ padding-right: 0; }}
    .sum-cat {{
      font-family: var(--f-serif); font-size: 22px; font-weight: 400; color: #17140F;
      white-space: nowrap;
    }}
    .sum-sys {{
      font-size: 12px; font-weight: 300; color: var(--stone);
      line-height: 1.5;
    }}
    .sum-sel {{
      font-size: 11px; font-weight: 400; letter-spacing: 0.12em;
      text-transform: uppercase; color: var(--gold);
    }}
    .sum-amt {{
      font-family: var(--f-serif); font-size: 26px; font-weight: 300;
      color: #17140F; text-align: right; white-space: nowrap;
    }}
    .sum-amt.tbd {{
      font-family: var(--f-sans); font-size: 12px; letter-spacing: 0.15em;
      text-transform: uppercase; color: var(--stone);
    }}
    .summary-disclaimer {{
      margin-top: 28px; font-size: 11px; font-weight: 300;
      color: var(--stone); letter-spacing: 0.05em;
      font-style: italic;
    }}

    /* ── FOOTER ── */
    footer {{
      background: #0F0C08; border-top: 1px solid rgba(184,148,74,0.15);
      padding: 60px 80px;
      display: flex; justify-content: space-between; align-items: flex-start; gap: 40px;
    }}
    .footer-left {{ max-width: 520px; }}
    .footer-disclaimer {{
      font-size: 12px; font-weight: 300; line-height: 1.7; color: var(--stone);
    }}
    .footer-contact {{
      font-size: 11px; letter-spacing: 0.15em; text-transform: uppercase;
      color: rgba(184,148,74,0.5); margin-top: 16px;
    }}
    .footer-logo {{ height: 24px; filter: brightness(0) invert(1); opacity: 0.3; }}

    /* ── ZONE PANELS ── */
    .zone-panel {{
      margin-top: 3px;
      padding: 28px 32px 24px;
      background: rgba(184,148,74,0.05);
      border: 1px solid rgba(184,148,74,0.2);
      animation: zoneIn 0.2s ease;
    }}
    @keyframes zoneIn {{
      from {{ opacity: 0; transform: translateY(-6px); }}
      to   {{ opacity: 1; transform: translateY(0); }}
    }}
    .zone-panel-header {{
      display: flex; align-items: baseline; gap: 20px;
      margin-bottom: 20px; padding-bottom: 14px;
      border-bottom: 1px solid rgba(184,148,74,0.15);
    }}
    .zone-prompt {{
      font-family: var(--f-sans); font-size: 13px; font-weight: 400;
      letter-spacing: 0.06em; color: var(--white);
    }}
    .zone-subtext {{
      font-family: var(--f-sans); font-size: 11px; font-weight: 300;
      color: var(--stone); letter-spacing: 0.04em;
    }}
    .zone-grid {{
      display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px;
      margin-bottom: 20px;
    }}
    .zone-item {{
      display: flex; flex-direction: column; gap: 5px;
      cursor: pointer; padding: 14px 38px 14px 14px;
      background: rgba(184,148,74,0.03);
      border: 1px solid rgba(184,148,74,0.1);
      position: relative;
      transition: border-color 0.15s, background 0.15s;
      user-select: none;
    }}
    .zone-item:hover {{
      border-color: rgba(184,148,74,0.3);
      background: rgba(184,148,74,0.08);
    }}
    .zone-item:has(.zone-cb:checked) {{
      border-color: var(--gold);
      background: rgba(184,148,74,0.12);
    }}
    .zone-cb {{
      position: absolute; top: 12px; right: 12px;
      appearance: none; -webkit-appearance: none;
      width: 16px; height: 16px;
      border: 1.5px solid rgba(184,148,74,0.35);
      border-radius: 3px;
      background: transparent;
      cursor: pointer;
      transition: background 0.15s, border-color 0.15s;
      flex-shrink: 0;
    }}
    .zone-cb:checked {{
      background: var(--gold); border-color: var(--gold);
    }}
    .zone-cb:checked::after {{
      content: '✓'; font-size: 10px; color: #17140F; font-weight: 700;
      position: absolute; top: -1px; left: 2px;
    }}
    .zone-name {{
      font-family: var(--f-sans); font-size: 13px; font-weight: 300;
      color: var(--white); line-height: 1.3;
    }}
    .zone-price {{
      font-family: var(--f-sans); font-size: 11px; font-weight: 300;
      color: rgba(184,148,74,0.45); letter-spacing: 0.04em;
    }}
    .zone-summary {{
      display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
      padding-top: 14px;
      border-top: 1px solid rgba(184,148,74,0.12);
    }}
    .zone-summary-label {{
      font-family: var(--f-sans); font-size: 10px; font-weight: 400;
      letter-spacing: 0.2em; text-transform: uppercase; color: var(--stone);
    }}
    .zone-summary-items {{
      font-family: var(--f-sans); font-size: 12px; font-weight: 300;
      color: var(--white); flex: 1; min-width: 0;
    }}
    .zone-summary-add {{
      font-family: var(--f-serif); font-size: 22px; font-weight: 300;
      color: var(--gold-lt); white-space: nowrap;
    }}

    /* ── RESPONSIVE ── */
    @media (max-width: 1100px) {{
      .opt-grid {{ grid-template-columns: 1fr 1fr 1fr 0.35fr; }}
    }}
    @media (max-width: 960px) {{
      .cover {{ grid-template-columns: 1fr; }}
      .cover-right {{ min-height: 50vw; }}
      .opt-grid {{ grid-template-columns: 1fr 1fr; }}
      .cat-inner {{ padding: 0 24px; }}
      .cover-left {{ padding: 80px 24px 60px; }}
      nav {{ padding: 0 20px; }}
      .nav-links {{ gap: 20px; }}
      footer {{ flex-direction: column; padding: 40px 24px; }}
      .cat-budget {{ flex-direction: column; gap: 8px; }}
      .plans-grid {{ grid-template-columns: 1fr; }}
      .zone-grid {{ grid-template-columns: repeat(2, 1fr); }}
      .zone-panel {{ padding: 20px; }}
    }}
    @media (max-width: 560px) {{
      .opt-grid {{ grid-template-columns: 1fr; }}
      .nav-links {{ gap: 12px; }}
      .nav-links a {{ font-size: 9px; letter-spacing: 0.12em; }}
      .sum-cat {{ font-size: 17px; }}
      .sum-amt {{ font-size: 20px; }}
      .zone-grid {{ grid-template-columns: 1fr 1fr; }}
    }}
  </style>
</head>
<body>

  <nav>
    {nav_logo}
    <ul class="nav-links">
      <li><a href="#cat-security">Security</a></li>
      <li><a href="#cat-it">IT</a></li>
      <li><a href="#cat-audiovisual">Audio Visual</a></li>
      <li><a href="#cat-system-integration">System Integration</a></li>
      <li><a href="#summary">Summary</a></li>
    </ul>
  </nav>

  <div class="cover">
    <div class="cover-left">
      {cover_logo}
      <div class="eyebrow">Security, Wi-Fi &amp; AV</div>
      <div class="cover-title">{client_name}</div>
      <div class="rule"></div>
      <p class="cover-body">This document outlines the security, Wi-Fi and AV options for your home. For each system, choose the level that suits you — your selections give us what we need to prepare a detailed proposal.</p>
      <p class="cover-philosophy">Every option has been chosen for simplicity above all else — the fewest components, zero learning curve, and the most intuitive experience possible.</p>
      <div class="cover-contact">Prepared by D-One &nbsp;·&nbsp; darren@d-one.co.za &nbsp;·&nbsp; www.d-one.co.za</div>
    </div>
    <div class="cover-right">
      {cover_img_html}
    </div>
  </div>

  <section class="philosophy-section">
    <div class="cat-inner">
      <div class="philosophy-grid">
        <div class="philosophy-left">
          <div class="eyebrow">Our Design Principle</div>
          <div class="philosophy-title">Designed for simplicity</div>
          <div class="rule"></div>
        </div>
        <div class="philosophy-right">
          <p class="philosophy-body">Every option in this document has been chosen with one priority above all others: simplicity. The goal is to give you the most capable system possible using the fewest components, with zero learning curve.</p>
          <p class="philosophy-body">Nothing to configure. Nothing to figure out. The system should work exactly when you need it, without getting in your way. These options are specifically designed for clients who want to enjoy the benefits of being in control without any of the complexity that often comes with a large home and its systems.</p>
          <div class="philosophy-pillars">
            <div class="pillar">
              <div class="pillar-label">Fewest components</div>
              <div class="pillar-sub">Only what you need, nothing superfluous</div>
            </div>
            <div class="pillar">
              <div class="pillar-label">Zero learning curve</div>
              <div class="pillar-sub">Intuitive from day one, no manual required</div>
            </div>
            <div class="pillar">
              <div class="pillar-label">Built for people, not technologists</div>
              <div class="pillar-sub">Every choice made with the end-user in mind</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  {plans_section}

  {"".join(category_sections)}

  {summary_section}

  <footer>
    <div class="footer-left">
      <p class="footer-disclaimer">Prices are estimates and subject to detailed design and final scope. Some items marked TBD will be confirmed once design is complete.</p>
      <p class="footer-contact">darren@d-one.co.za &nbsp;·&nbsp; www.d-one.co.za</p>
    </div>
    {footer_logo}
  </footer>

  {conduit_section_html}

  <script>
    const SYSTEM_BUDGETS = {system_js};
    const CAT_SYSTEMS    = {cat_js};
    const CAT_NAMES      = {json.dumps({cat_id: cat_name for cat_id, cat_name, _ in CATEGORIES})};
{audio_zone_js_extra}

    // Track tier selections per system: system -> {{ tier, budget }}
    const selections = {{}};
    // Track zone/reader additions per system: system -> total added cost
    const zoneAdditions = {{}};

    function selectOption(el) {{
      const system = el.dataset.system;
      const tier   = el.dataset.tier;
      const budget = parseInt(el.dataset.budget) || 0;

      // Deselect all cards for this system
      document.querySelectorAll(`.opt-card[data-system="${{system}}"]`).forEach(c => c.classList.remove('selected'));
      el.classList.add('selected');

      // Store tier selection
      selections[system] = {{ tier, budget }};

      // Handle zone panel visibility
      const panel = document.getElementById(`zone-panel-${{system}}`);
      if (panel) {{
        const showTiers = JSON.parse(panel.dataset.showTiers || '[]');
        if (tier === 'none' || !showTiers.includes(tier)) {{
          // Hide panel and clear all checkboxes + zone costs
          panel.style.display = 'none';
          panel.querySelectorAll('.zone-cb').forEach(cb => cb.checked = false);
          zoneAdditions[system] = 0;
          const itemsEl = document.getElementById(`zone-items-${{system}}`);
          const addEl   = document.getElementById(`zone-add-${{system}}`);
          if (itemsEl) itemsEl.textContent = '—';
          if (addEl)   addEl.textContent = '';
        }} else {{
          panel.style.display = 'block';{audio_zone_update_call}
          // Recalculate in case it was previously populated
          onZoneChange(system);
          return; // onZoneChange will call updateCategoryBudget
        }}
      }}

      // Update budgets for the category this system belongs to
      refreshCategoryForSystem(system);
    }}

    function onZoneChange(system) {{
      const panel = document.getElementById(`zone-panel-${{system}}`);
      if (!panel || panel.style.display === 'none') {{
        zoneAdditions[system] = 0;
        refreshCategoryForSystem(system);
        return;
      }}

      const checkedBoxes = panel.querySelectorAll('.zone-cb:checked');
      let total = 0;
      const labels = [];
      checkedBoxes.forEach(cb => {{
        total += parseInt(cb.dataset.price) || 0;
        labels.push(cb.closest('.zone-item').querySelector('.zone-name').textContent);
      }});

      zoneAdditions[system] = total;

      // Update zone summary line
      const itemsEl = document.getElementById(`zone-items-${{system}}`);
      const addEl   = document.getElementById(`zone-add-${{system}}`);
      if (itemsEl) {{
        itemsEl.textContent = labels.length > 0 ? labels.join(', ') : '—';
      }}
      if (addEl) {{
        if (total > 0) {{
          const fmt = new Intl.NumberFormat('en-ZA', {{style:'currency',currency:'ZAR',maximumFractionDigits:0}}).format(total);
          addEl.textContent = `+ ${{fmt}}`;
        }} else {{
          addEl.textContent = '';
        }}
      }}

      refreshCategoryForSystem(system);
    }}

    function refreshCategoryForSystem(system) {{
      for (const [catId, systems] of Object.entries(CAT_SYSTEMS)) {{
        if (systems.includes(system)) {{
          updateCategoryBudget(catId);
          updateSummaryRow(catId);
          break;
        }}
      }}
    }}

    function getCategoryTotals(catId) {{
      const systems = CAT_SYSTEMS[catId];
      let total = 0, hasTbd = false, anySelected = false;
      const tierNames = [];
      for (const sys of systems) {{
        const sel = selections[sys];
        if (sel) {{
          anySelected = true;
          if (sel.tier === 'none') {{
            tierNames.push('Not Required');
            continue;
          }}
          total += sel.budget;
          total += zoneAdditions[sys] || 0;
          if (sel.budget === 0) hasTbd = true;
          tierNames.push(sel.tier);
        }}
      }}
      return {{ total, hasTbd, anySelected, tierNames }};
    }}

    function updateCategoryBudget(catId) {{
      const {{ total, hasTbd, anySelected }} = getCategoryTotals(catId);
      const amountEl = document.getElementById(`amount-${{catId}}`);
      if (!anySelected) {{
        amountEl.textContent = 'Select your preferences above';
        amountEl.style.cssText = 'color:var(--stone);font-size:14px;font-family:var(--f-sans);letter-spacing:0';
      }} else {{
        amountEl.style.cssText = 'color:var(--gold);font-size:36px;font-family:var(--f-serif)';
        if (total === 0 && hasTbd) {{
          amountEl.textContent = 'TBD';
        }} else {{
          const fmt = new Intl.NumberFormat('en-ZA', {{style:'currency',currency:'ZAR',maximumFractionDigits:0}}).format(total);
          amountEl.textContent = fmt + (hasTbd ? ' + TBD' : '');
        }}
      }}
    }}

    function updateSummaryRow(catId) {{
      const {{ total, hasTbd, anySelected, tierNames }} = getCategoryTotals(catId);
      const selEl = document.getElementById(`sum-sel-${{catId}}`);
      const amtEl = document.getElementById(`sum-amt-${{catId}}`);
      if (!anySelected) {{
        selEl.textContent = '—';
        amtEl.textContent = '—';
        amtEl.className = 'sum-amt';
      }} else {{
        const unique = [...new Set(tierNames)];
        selEl.textContent = unique.join(' / ');
        if (total === 0 && hasTbd) {{
          amtEl.textContent = 'TBD';
          amtEl.className = 'sum-amt tbd';
        }} else {{
          const fmt = new Intl.NumberFormat('en-ZA', {{style:'currency',currency:'ZAR',maximumFractionDigits:0}}).format(total);
          amtEl.textContent = fmt + (hasTbd ? ' + TBD' : '');
          amtEl.className = 'sum-amt';
        }}
      }}
    }}

    // Highlight active nav link on scroll
    const allSections = document.querySelectorAll('.cat-section[id], #summary');
    const navLinks    = document.querySelectorAll('.nav-links a');
    const observer = new IntersectionObserver((entries) => {{
      entries.forEach(e => {{
        if (e.isIntersecting) {{
          navLinks.forEach(l => l.classList.remove('active'));
          const link = document.querySelector(`.nav-links a[href="#${{e.target.id}}"]`);
          if (link) link.classList.add('active');
        }}
      }});
    }}, {{ rootMargin: '-40% 0px -55% 0px' }});
    allSections.forEach(s => observer.observe(s));
  </script>
</body>
</html>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--client',      default='Demo Residence')
    parser.add_argument('--project',     default='')
    parser.add_argument('--output',      default='/tmp/proposal-demo/')
    parser.add_argument('--budgets',      default=None,
                        help='JSON dict of budgets per system/tier')
    parser.add_argument('--budgets-file', default=None,
                        help='Path to proposal_budgets.json from the budget-analyzer skill. '
                             'Provides both tier card prices and per-unit zone prices. '
                             'Takes priority over --budgets and --zone-prices if all three are given.')
    parser.add_argument('--audio-zones', default=None,
                        help='JSON array of [zone_id, zone_label] pairs extracted from drawings. '
                             'If omitted, DEFAULT_AUDIO_ZONES is used.')
    parser.add_argument('--zone-prices', default=None,
                        help='JSON dict of per-unit prices e.g. {"audio":8000,"access-control":25000}')
    parser.add_argument('--plans', default=None,
                        help='Comma-separated list of floor plan image paths to embed as project plans')
    parser.add_argument('--cover', default=None, help='Path to cover image')
    parser.add_argument('--conduit', default=None, help='Path to conduit JSON file')
    args = parser.parse_args()

    # ── Load from proposal_budgets.json if provided (output of budget-analyzer) ──
    budgets_file_data = None
    if args.budgets_file and os.path.exists(args.budgets_file):
        with open(args.budgets_file, 'r', encoding='utf-8') as f:
            budgets_file_data = json.load(f)
        print(f"Loaded budgets from: {args.budgets_file}")

    # Tier budgets — budgets-file > --budgets > demo defaults
    if budgets_file_data and budgets_file_data.get('tier_budgets'):
        budgets = budgets_file_data['tier_budgets']
    elif args.budgets:
        budgets = json.loads(args.budgets)
    else:
        budgets = {
            'cctv':               {'Entry': 45000,  'Mid': 85000,  'Premium': 150000},
            'access-control':     {'Entry': 30000,  'Mid': 65000,  'Premium': 'TBD'},
            'network':            {'Entry': 55000,  'Mid': 90000,  'Premium': 160000},
            'audio':              {'Entry': 40000,  'Mid': 75000,  'Premium': 'TBD'},
            'home-theatre':       {'Entry': 80000,  'Mid': 180000, 'Premium': 'TBD'},
            'lighting':           {'Entry': 60000,  'Mid': 110000, 'Premium': 220000},
            'system-integration': {'Entry': 35000,  'Mid': 70000,  'Premium': 140000},
        }

    # Audio zones — use drawing-extracted list if provided, else default
    audio_zones = None
    if args.audio_zones:
        raw = json.loads(args.audio_zones)
        # Accept either [[id, label], ...] or ["Room Name", ...] (auto-slugify the latter)
        if raw and isinstance(raw[0], str):
            audio_zones = [(r.lower().replace(' ', '-'), r) for r in raw]
        else:
            audio_zones = [tuple(pair) for pair in raw]

    # Zone prices — budgets-file > --zone-prices > built-in defaults
    if budgets_file_data and budgets_file_data.get('zone_prices'):
        zone_prices = budgets_file_data['zone_prices']
        if args.zone_prices:
            # Merge: explicit --zone-prices overrides individual keys
            zone_prices.update(json.loads(args.zone_prices))
    else:
        zone_prices = json.loads(args.zone_prices) if args.zone_prices else None

    # Floor plans — load each image from the comma-separated paths
    plan_images_b64 = None
    if args.plans:
        paths = [p.strip() for p in args.plans.split(',') if p.strip()]
        loaded = [img_b64(p) for p in paths if os.path.exists(p)]
        if loaded:
            plan_images_b64 = loaded
            print(f"Loaded {len(loaded)} floor plan(s)")
        missing = [p for p in paths if not os.path.exists(p)]
        if missing:
            print(f"Warning: plan files not found: {missing}")

    # Cover image — explicit path, or auto-detect from output folder
    cover_path = None
    if args.cover:
        cover_path = args.cover
    else:
        output_dir = os.path.abspath(args.output)
        cover_exts = {'png', 'jpg', 'jpeg', 'webp'}
        if os.path.isdir(output_dir):
            for fname in sorted(os.listdir(output_dir)):
                stem, _, ext = fname.rpartition('.')
                if ext.lower() not in cover_exts:
                    continue
                if stem.lower() == 'cover' or 'cover' in fname.lower():
                    cover_path = os.path.join(output_dir, fname)
                    break
    cover_image_b64 = img_b64(cover_path) if cover_path and os.path.exists(cover_path) else None
    if cover_image_b64:
        print(f"Loaded cover image: {cover_path}")

    logo_b64 = img_b64(LOGO_PATH)

    # Load conduit schedule if provided
    conduit_html = None
    if args.conduit and os.path.exists(args.conduit):
        with open(args.conduit, 'r', encoding='utf-8') as f:
            conduit_data = json.load(f)
        conduit_html = render_conduit_schedule(conduit_data)
        print(f"Loaded conduit schedule: {args.conduit}")
    elif args.conduit:
        print(f"Warning: conduit file not found: {args.conduit}")

    html = generate_html(args.client, args.project, budgets, logo_b64=logo_b64, cover_image_b64=cover_image_b64,
                         plan_images_b64=plan_images_b64,
                         audio_zones=audio_zones, zone_prices=zone_prices, conduit_html=conduit_html)

    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(args.output, 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Generated: {out_path} ({os.path.getsize(out_path) // 1024} KB)")
    return out_path


if __name__ == '__main__':
    main()

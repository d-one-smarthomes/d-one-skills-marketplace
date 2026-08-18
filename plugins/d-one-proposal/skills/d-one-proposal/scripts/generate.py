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
from html import escape

SKILL_DIR  = os.path.join(os.path.dirname(__file__), '..')
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

# Client testimonials — one pull-quote is placed after each major section.
QUOTES = [
    "The best contractor on our whole project.",
    "I'm not technical — it must just work.",
    "Nice to deal with guys that just get it.",
    "D-One gets it done.",
    "Nice that it's so obvious, so I don't have to remember anything.",
    "We don't need to be shown how it works — it's obvious, anyone can use it.",
]


def pull_quote(text):
    """A centred gold pull-quote block, used between sections."""
    return f'''
      <section class="quote-section">
        <div class="quote-inner">
          <div class="quote-mark">&ldquo;</div>
          <p class="quote-text">{escape(text)}</p>
        </div>
      </section>'''

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

# ── IMAGE SOURCE ─────────────────────────────────────────────────────────
#
# Images are BAKED INTO this skill at assets/images/<system>/<tier>.<ext> —
# that's what makes the skill self-contained: anyone who installs it gets
# working proposals immediately, with zero path configuration.
#
# Darren also gets an optional live convenience on top of that: if
# config/image_source.json points at a folder that actually exists on THIS
# machine (his Google Drive sync), that folder is used instead — so he can
# preview a new photo before running scripts/sync_images_from_drive.py to
# bake it in for everyone else. On any other machine that path won't exist,
# so this silently and correctly falls through to the bundled images —
# no per-teammate configuration needed.
#
# Resolution order:
#   1. DONE_PROPOSAL_IMAGES_ROOT env var, if set — must resolve, or error
#      (explicit override always wins; mainly for testing)
#   2. "images_root" in config/image_source.json, IF that path exists on
#      this machine — Darren's live-preview convenience
#   3. assets/images/ bundled in this skill — the reliable default
#
# Folder structure when using the EXTERNAL source (#1 or #2), matching
# Darren's Drive folder:
#   <root>/<Category>/<System>/<Tier>/<one image file>
# Folder structure for the BUNDLED source (#3):
#   assets/images/<system-slug>/<tier>.<ext>   e.g. assets/images/lighting/premium.jpeg
#
# See SKILL.md > "Where proposal images come from" and
# scripts/sync_images_from_drive.py to update the bundled images later.
IMAGE_SOURCE_CONFIG_PATH = os.path.join(SKILL_DIR, 'config', 'image_source.json')
BUNDLED_IMAGES_DIR = os.path.join(SKILL_DIR, 'assets', 'images')

# ── LIVE IMAGE HOST (hot-linked) ──────────────────────────────────────────────
# Preferred source for the per-tier option photos: a hosted image site whose
# URLs are stable, so the proposal HTML just points at them. To change a photo
# you replace it in the Drive source folder and re-publish the host — this skill
# is never edited. URL scheme: <base_url>/<system-slug>/<tier-lowercase>.jpg
# Configured in config/image_host.json ("base_url"); env DONE_PROPOSAL_IMAGE_BASE_URL
# overrides it; empty/unset falls back to the bundled base64 images below.
IMAGE_HOST_CONFIG_PATH = os.path.join(SKILL_DIR, 'config', 'image_host.json')

_image_base_url_cache = None  # None = not yet resolved; '' = explicitly none

def _image_base_url():
    global _image_base_url_cache
    if _image_base_url_cache is not None:
        return _image_base_url_cache
    base = os.environ.get('DONE_PROPOSAL_IMAGE_BASE_URL')
    if base is None and os.path.exists(IMAGE_HOST_CONFIG_PATH):
        try:
            with open(IMAGE_HOST_CONFIG_PATH, 'r', encoding='utf-8') as f:
                base = (json.load(f) or {}).get('base_url')
        except (json.JSONDecodeError, OSError):
            base = None
    _image_base_url_cache = (base or '').rstrip('/')
    return _image_base_url_cache


def image_src(system_slug, tier_name):
    """Return the value for an option <img src>. Hot-links the live host when a
    base_url is configured (the default); otherwise falls back to a baked-in
    base64 data URI from the external Drive folder or bundled assets."""
    base = _image_base_url()
    if base:
        return f"{base}/{system_slug}/{tier_name.lower()}.jpg"
    return best_image(system_slug, tier_name)

# system_slug -> (Category folder name, System folder name) as they exist
# inside an EXTERNAL images root. These must match the shared Drive folder's
# names exactly. Not used for the bundled source, which is flat per system.
SYSTEM_FOLDER_MAP = {
    'cctv':               ('Security',           'CCTV'),
    'access-control':     ('Security',           'Access Control'),
    'network':            ('IT',                 'Network & Wi-Fi'),
    'audio':              ('Audio Visual',       'Audio'),
    'home-theatre':       ('Audio Visual',       'Home Theatre'),
    'lighting':           ('System Integration', 'Lighting Control'),
    'system-integration': ('System Integration', 'System Integration'),
}

VALID_IMAGE_EXTS = {'webp', 'png', 'jpg', 'jpeg'}
IGNORE_FILENAMES = {'.ds_store', 'thumbs.db', 'desktop.ini'}


class ImageSlotError(RuntimeError):
    """Raised when a Category/System/Tier image slot can't be resolved unambiguously.
    This is intentionally fatal — guessing which image is meant is exactly the bug
    this replaced, so any ambiguity or missing file stops generation with a clear,
    actionable message instead of silently picking something.
    """
    pass


_images_source_cache = None  # (root_path, mode) where mode is 'external' or 'bundled'

def _resolve_images_source():
    """Lazily decide whether to read from Darren's live external folder or the
    bundled assets — not at import time, so any ImageSlotError raised here is
    caught by the try/except around main() instead of crashing on import.
    """
    global _images_source_cache
    if _images_source_cache is not None:
        return _images_source_cache

    env_override = os.environ.get('DONE_PROPOSAL_IMAGES_ROOT')
    if env_override:
        if not os.path.isdir(env_override):
            raise ImageSlotError(
                f"DONE_PROPOSAL_IMAGES_ROOT is set but not reachable:\n  {env_override}\n"
                "Fix the path, or unset the variable to use the bundled images instead."
            )
        _images_source_cache = (env_override, 'external')
        return _images_source_cache

    if os.path.exists(IMAGE_SOURCE_CONFIG_PATH):
        try:
            with open(IMAGE_SOURCE_CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            configured_root = cfg.get('images_root')
        except (json.JSONDecodeError, OSError):
            configured_root = None
        if configured_root and os.path.isdir(configured_root):
            _images_source_cache = (configured_root, 'external')
            return _images_source_cache

    # No env override, and no reachable configured folder on this machine —
    # this is the expected path for anyone who isn't Darren.
    _images_source_cache = (BUNDLED_IMAGES_DIR, 'bundled')
    return _images_source_cache


def _valid_image_files(folder):
    return sorted(
        fname for fname in os.listdir(folder)
        if not fname.startswith('.')
        and fname.lower() not in IGNORE_FILENAMES
        and '.' in fname
        and fname.rsplit('.', 1)[-1].lower() in VALID_IMAGE_EXTS
    )


def best_image(system_slug, tier_name):
    """Resolve the image for a system+tier — see the IMAGE SOURCE comment above
    for the bundled-vs-external resolution order.

    Whichever source is used, exactly one image file must be found for the
    slot. Raises ImageSlotError on anything else (missing folder, empty slot,
    or more than one candidate) rather than guessing.
    """
    images_root, mode = _resolve_images_source()

    if mode == 'external':
        cat_label, sys_label = SYSTEM_FOLDER_MAP[system_slug]
        folder = os.path.join(images_root, cat_label, sys_label, tier_name)
        slot_desc = f"{system_slug} / {tier_name} (external source)"
        fix_hint = (
            "Expected structure: <Category>/<System>/<Tier>/<one image file>. "
            "Create this folder and add one image, or fix the ambiguity below."
        )
    else:
        folder = os.path.join(images_root, system_slug)
        slot_desc = f"{system_slug} / {tier_name} (bundled source)"
        fix_hint = (
            "Expected exactly one file named like "
            f"'{tier_name.lower()}.<ext>' in this folder. Run "
            "scripts/sync_images_from_drive.py to re-bake images from the Drive folder, "
            "or fix this folder directly."
        )

    if not os.path.isdir(folder):
        raise ImageSlotError(f"No folder found for {slot_desc}:\n  {folder}\n{fix_hint}")

    if mode == 'bundled':
        tier_lower = tier_name.lower()
        candidates = [
            f for f in _valid_image_files(folder)
            if f.rsplit('.', 1)[0].lower() == tier_lower
        ]
    else:
        candidates = _valid_image_files(folder)

    if len(candidates) == 0:
        raise ImageSlotError(f"No image found for {slot_desc} in:\n  {folder}\n{fix_hint}")
    if len(candidates) > 1:
        raise ImageSlotError(
            f"Ambiguous image slot for {slot_desc} — found {len(candidates)} files in:\n"
            f"  {folder}\n  -> {', '.join(candidates)}\n{fix_hint}"
        )

    return img_b64(os.path.join(folder, candidates[0]))

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

def make_zone_panel(system_slug, zones, unit_by_tier, prompt, tiers_that_show):
    """
    Build the HTML for a zone selector panel.
    zones:           list of (zone_id, zone_label)
    unit_by_tier:    dict {tier: price} — the per-zone price is TIER-SPECIFIC and is
                     NOT shown to the client. Only the category subtotal moves.
    tiers_that_show: list of tier names that trigger this panel to show.
    """
    units_json = json.dumps({t: int(round(p or 0)) for t, p in (unit_by_tier or {}).items()}).replace('"', '&quot;')
    zone_items = ''
    for zone_id, zone_label in zones:
        zone_items += f'''
              <label class="zone-item">
                <input type="checkbox" class="zone-cb"
                       data-system="{system_slug}"
                       data-zone="{zone_id}"
                       data-units="{units_json}"
                       onchange="onZoneChange('{system_slug}')">
                <span class="zone-name">{zone_label}</span>
              </label>'''
    return f'''
        <div class="zone-panel" id="zone-panel-{system_slug}"
             data-show-tiers="{json.dumps(tiers_that_show).replace('"', '&quot;')}"
             style="display:none;">
          <div class="zone-panel-header">
            <span class="zone-prompt">{prompt}</span>
          </div>
          <div class="zone-grid">
            {zone_items}
          </div>
          <div class="zone-summary">
            <span class="zone-summary-label">Selected</span>
            <span class="zone-summary-items" id="zone-items-{system_slug}">—</span>
          </div>
        </div>'''


def make_option_panel(system_slug, controls, prompt, tiers_that_show, panel_suffix=''):
    """
    Build the HTML for a client-selectable OPTION panel (dropdowns + checkboxes).
    Per-unit prices are TIER-SPECIFIC and are NOT shown to the client — selecting
    quantities only moves the category subtotal.

    controls:        list of dicts, each either:
        {'type': 'dropdown', 'label': str, 'units': {tier: price}, 'max': int, 'default': int}
        {'type': 'checkbox', 'label': str, 'units': {tier: price}, 'checked': bool}
      ('unit' is still accepted as a flat fallback and expanded to all tiers.)
    tiers_that_show: list of tier names that trigger this panel to show.
    panel_suffix:    optional suffix so a system can have more than one option panel
                     (e.g. access-control's Entry/Mid panel vs its Premium panel).
    """
    pid = f"{system_slug}{panel_suffix}"

    def units_of(c):
        u = c.get('units')
        if u is None:
            flat = int(round(c.get('unit') or 0))
            u = {t: flat for t in TIERS}
        return json.dumps({t: int(round(p or 0)) for t, p in u.items()}).replace('"', '&quot;')

    rows = ''
    for c in controls:
        units_json = units_of(c)
        if c.get('type') == 'dropdown':
            maxn    = int(c.get('max', 10))
            default = int(c.get('default', 0))
            opts = ''.join(
                f'<option value="{i}"{" selected" if i == default else ""}>{i}</option>'
                for i in range(0, maxn + 1)
            )
            rows += f'''
              <label class="option-item">
                <span class="option-name">{c['label']}</span>
                <span class="option-controls">
                  <select class="opt-select" data-system="{system_slug}" data-units="{units_json}"
                          data-default="{default}" onchange="onOptionChange('{system_slug}')">
                    {opts}
                  </select>
                </span>
              </label>'''
        else:  # checkbox
            checked = ' checked' if c.get('checked') else ''
            rows += f'''
              <label class="option-item option-item-cb">
                <input type="checkbox" class="opt-cb" data-system="{system_slug}"
                       data-units="{units_json}"{checked} onchange="onOptionChange('{system_slug}')">
                <span class="option-name">{c['label']}</span>
              </label>'''
    return f'''
        <div class="zone-panel option-panel" id="option-panel-{pid}"
             data-system="{system_slug}"
             data-show-tiers="{json.dumps(tiers_that_show).replace('"', '&quot;')}"
             style="display:none;">
          <div class="zone-panel-header">
            <span class="zone-prompt">{prompt}</span>
          </div>
          <div class="option-grid">
            {rows}
          </div>
        </div>'''


def format_budget(val):
    if val is None or val == 'TBD':
        return 'TBD'
    if isinstance(val, (int, float)):
        return f"R {val:,.0f}"
    return str(val)

def generate_html(client_name, project_name, budgets, logo_b64=None, cover_image_b64=None, plan_images_b64=None,
                  audio_zones=None, zone_prices=None, options=None, per_unit=None, takeoff=None):
    """
    budgets:          dict like {'cctv': {'Entry': 45000, 'Mid': 85000, 'Premium': 150000}, ...}
    cover_image_b64:  base64 data URI for the project cover render (optional)
    plan_images_b64:  list of base64 data URIs for marked-up floor plans (optional)
    audio_zones:      list of (zone_id, zone_label) tuples for audio room checkboxes (default: DEFAULT_AUDIO_ZONES)
    zone_prices:      dict with per-unit prices e.g. {'audio': 8000, 'access-control': 25000}
    options:          flat dict of per-unit OPTION prices (net ex-VAT), e.g. from
                      proposal_budgets.json's "options" block:
                      cctv_enhancer_each, network_5g_backup, audio_outdoor_zone,
                      si_hvac_integration, si_door_integration, si_lighting_integration.
    """
    if audio_zones is None:
        audio_zones = DEFAULT_AUDIO_ZONES
    if zone_prices is None:
        zone_prices = DEFAULT_ZONE_PRICES.copy()
    if options is None:
        options = {}
    # per_unit: tier-specific per-add-on prices, e.g.
    #   {'audio_zone': {'Entry':x,'Mid':y,'Premium':z},
    #    'access_viewer': {'Entry':..,'Mid':..}, 'access_reader': {...}, 'access_intercom': {'Premium':..}}
    if per_unit is None:
        per_unit = {}
    # takeoff: drawing-derived add-on locations/limits, e.g.
    #   {'access_viewer_locations': [[id,label],...], 'access_intercom_locations': [[id,label],...],
    #    'access_reader_max': 8}
    if takeoff is None:
        takeoff = {}

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
        n = len(plan_images_b64)
        # Adaptive column count: 1→1col, 2→2col, 3→3col, 4+→2col wrapping
        if n == 1:
            cols = '1fr'
        elif n == 3:
            cols = '1fr 1fr 1fr'
        else:
            cols = '1fr 1fr'
        plans_grid_items = ''.join(
            f'<div class="plan-item"><img src="{p}" class="plan-img" alt="Floor plan {i+1}"></div>'
            for i, p in enumerate(plan_images_b64)
        )
        plans_grid = f'<div class="plans-grid" style="grid-template-columns:{cols}">{plans_grid_items}</div>'
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

    plans_section = f'''
      <section class="plans-section">
        <div class="cat-inner">
          <div class="eyebrow">Project Plans</div>
          <div class="rule"></div>
          <p class="plans-note">Equipment layouts prepared for this project. Each system is marked on the drawings below.</p>
          {plans_grid}
        </div>
      </section>''' + pull_quote(QUOTES[0])

    # ── CATEGORY SECTIONS ──
    category_sections = []
    for cat_idx, (cat_id, cat_name, cat_systems) in enumerate(CATEGORIES):
        systems_html = []
        for sys_slug in cat_systems:
            sys_label = next(l for s, l in SYSTEMS if s == sys_slug)
            tiers_html = []
            for tier in TIERS:
                img_data = image_src(sys_slug, tier)
                contain_class = ' opt-img-contain' if (
                    sys_slug == 'lighting' or
                    (sys_slug == 'access-control' and tier in ('Entry', 'Mid'))
                ) else ''
                img_html = f'<img src="{img_data}" class="opt-img{contain_class}" alt="{tier}">' if img_data else '<div class="opt-img-placeholder"></div>'
                budget_val = budgets.get(sys_slug, {}).get(tier)
                # Audio has no baseline — it is priced entirely per selected zone,
                # so the card shows "Priced per zone" instead of a rand figure (B8).
                if sys_slug == 'audio':
                    budget_str = 'Priced per zone'
                    budget_class = 'budget-perzone'
                    budget_val = 0
                else:
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

            # ── Audio zone panel. Audio has NO baseline — every zone (indoor AND
            #    outdoor) the client picks adds a TIER-SPECIFIC per-zone price to the
            #    subtotal; the unit price is never shown (C3/B8). ──
            zone_panel_html = ''
            if sys_slug == 'audio':
                au_zone_units = per_unit.get('audio_zone') or {t: zone_prices.get('audio', 8000) for t in TIERS}
                zone_panel_html = make_zone_panel(
                    system_slug='audio',
                    zones=audio_zones,
                    unit_by_tier=au_zone_units,
                    prompt='Which areas would you like audio in? Each area you select is added to your Audio estimate.',
                    tiers_that_show=['Entry', 'Mid', 'Premium'],
                )

            # ── Client-selectable OPTION panels (dropdowns + checkboxes) ──
            option_panel_html = ''
            if sys_slug == 'cctv':
                option_panel_html = make_option_panel(
                    system_slug='cctv',
                    controls=[
                        {'type': 'dropdown',
                         'label': 'Camera enhancers (auto spotlight + radar + live speaker)',
                         'unit': options.get('cctv_enhancer_each', 0),
                         'max': 20, 'default': 0},
                    ],
                    prompt='Add active-deterrent camera enhancers',
                    tiers_that_show=['Premium'],
                )
            elif sys_slug == 'network':
                option_panel_html = make_option_panel(
                    system_slug='network',
                    controls=[
                        {'type': 'checkbox',
                         'label': '5G failover backup (keeps the home online if the main line drops)',
                         'unit': options.get('network_5g_backup', 0),
                         'checked': True},
                    ],
                    prompt='Connectivity resilience',
                    tiers_that_show=['Entry', 'Mid', 'Premium'],
                )
            elif sys_slug == 'access-control':
                # Access Control is a baseline + per-additional-unit model, and the
                # add-on options differ by tier (C2):
                #   Entry / Mid : baseline = 1 reader + 1 viewer at the gate.
                #                 Add more VIEWERS at the marked-up locations, and
                #                 more READERS via a dropdown.
                #   Premium     : baseline = 1 Savant gate intercom.
                #                 Add more Savant INTERCOMS, plus optional TAG READERS
                #                 at the marked-up locations. No interior viewers —
                #                 those are Savant touch panels under System Integration.
                # Per-unit prices are tier-specific and hidden — only the subtotal moves.
                ac_viewer   = per_unit.get('access_viewer',   {})
                ac_reader    = per_unit.get('access_reader',   {})
                ac_intercom = per_unit.get('access_intercom', {})
                viewer_locs   = takeoff.get('access_viewer_locations', [])   # [[id,label],...]
                intercom_locs = takeoff.get('access_intercom_locations', []) # [[id,label],...]
                reader_max    = int(takeoff.get('access_reader_max', 8) or 8)

                # Entry/Mid panel: additional viewers (at marked-up spots) + readers dropdown
                em_controls = []
                for loc_id, loc_label in viewer_locs:
                    em_controls.append({'type': 'checkbox',
                                        'label': f'Add a viewer — {loc_label}',
                                        'units': {t: ac_viewer.get(t, 0) for t in ('Entry', 'Mid')}})
                em_controls.append({'type': 'dropdown', 'label': 'Additional tag readers',
                                    'units': {t: ac_reader.get(t, 0) for t in ('Entry', 'Mid')},
                                    'max': reader_max, 'default': 0})
                em_panel = make_option_panel(
                    system_slug='access-control', controls=em_controls,
                    prompt='Additional doors — extra viewers and tag readers',
                    tiers_that_show=['Entry', 'Mid'], panel_suffix='-em')

                # Premium panel: additional Savant intercoms + optional tag readers
                prem_controls = [{'type': 'dropdown', 'label': 'Additional Savant intercom stations',
                                  'units': {'Premium': ac_intercom.get('Premium', 0)},
                                  'max': max(1, len(intercom_locs) or 8), 'default': 0}]
                for loc_id, loc_label in intercom_locs:
                    prem_controls.append({'type': 'checkbox',
                                          'label': f'Tag reader — {loc_label}',
                                          'units': {'Premium': ac_reader.get('Premium', 0)}})
                if not intercom_locs:
                    prem_controls.append({'type': 'dropdown', 'label': 'Optional tag readers',
                                          'units': {'Premium': ac_reader.get('Premium', 0)},
                                          'max': reader_max, 'default': 0})
                prem_panel = make_option_panel(
                    system_slug='access-control', controls=prem_controls,
                    prompt='Additional doors — extra Savant intercoms and tag readers',
                    tiers_that_show=['Premium'], panel_suffix='-prem')

                option_panel_html = em_panel + prem_panel
            elif sys_slug == 'system-integration':
                option_panel_html = make_option_panel(
                    system_slug='system-integration',
                    controls=[
                        {'type': 'checkbox', 'label': 'HVAC Integration',
                         'unit': options.get('si_hvac_integration', 0)},
                        {'type': 'checkbox', 'label': 'Door Integration',
                         'unit': options.get('si_door_integration', 0)},
                        {'type': 'checkbox', 'label': 'Lighting Integration',
                         'unit': options.get('si_lighting_integration', 0)},
                        {'type': 'dropdown', 'label': 'Number of touch panels',
                         'unit': options.get('si_touch_panel_each', 0), 'max': 10, 'default': 0},
                        {'type': 'dropdown', 'label': 'Number of SmartControl processors',
                         'unit': options.get('si_smartcontrol_each', 0), 'max': 10, 'default': 0},
                    ],
                    prompt='System integration options',
                    tiers_that_show=['Entry', 'Mid', 'Premium'],
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
          {option_panel_html}
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
        # A client pull-quote after each category section (quotes[1..4]).
        category_sections.append(pull_quote(QUOTES[(cat_idx + 1) % len(QUOTES)]))

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

          <div class="save-block">
            <div class="save-eyebrow">Next step</div>
            <p class="save-note">Happy with your selections? Save them and we'll get a copy so we can prepare your detailed proposal. You'll also download a copy for your records.</p>
            <div class="save-fields">
              <input type="text"  id="client-name"  class="save-input" placeholder="Your name" autocomplete="name">
              <input type="email" id="client-email" class="save-input" placeholder="Your email" autocomplete="email">
            </div>
            <button type="button" class="save-btn" id="save-btn" onclick="saveSelections()">Save my selections</button>
            <p class="save-status" id="save-status"></p>
          </div>
        </div>
      </section>''' + pull_quote(QUOTES[5]) + f'''
      <!-- Selections are posted cross-site to the permanent D-One inbox on Netlify
           (d1-proposal-inbox), whose form notifications email systems@ and operations@.
           Posting into a hidden iframe avoids CORS and works from any hosted proposal. -->
      <iframe name="d1-inbox-frame" style="display:none" title="submit"></iframe>
      <form id="d1-selections-form" name="proposal-selections"
            action="https://d1-proposal-inbox.netlify.app/" method="POST"
            target="d1-inbox-frame" style="display:none">
        <input type="hidden" name="form-name" value="proposal-selections">
        <input type="hidden" name="bot-field">
        <input type="hidden" name="client">
        <input type="hidden" name="project">
        <input type="hidden" name="name">
        <input type="hidden" name="email">
        <textarea name="summary" hidden></textarea>
      </form>'''

    nav_logo = f'<img src="{logo_b64}" class="nav-logo" alt="D-One">' if logo_b64 else '<span style="color:var(--gold);font-family:var(--f-serif);font-size:18px;">D-One</span>'
    cover_logo = f'<img src="{logo_b64}" class="cover-logo" alt="D-One">' if logo_b64 else ''
    footer_logo = f'<img src="{logo_b64}" class="footer-logo" alt="D-One">' if logo_b64 else ''

    # Project name / address subtitle on the cover (rendered only when supplied)
    project_line = f'<div class="cover-project">{escape(project_name)}</div>' if project_name else ''

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
      width: 100%; height: 100%; object-fit: cover; display: block;
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
    .cover-project {{
      font-family: var(--f-sans); font-size: 15px; font-weight: 400;
      letter-spacing: 0.12em; text-transform: uppercase;
      color: var(--gold-lt); margin-top: 12px;
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
    .budget-perzone {{
      font-family: var(--f-sans); font-size: 11px; letter-spacing: 0.15em;
      text-transform: uppercase; color: var(--gold-lt); margin-top: 8px;
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

    /* ── PULL QUOTES ── */
    .quote-section {{
      background: var(--dark); padding: 64px 80px; text-align: center;
      border-top: 1px solid rgba(184,148,74,0.12);
      border-bottom: 1px solid rgba(184,148,74,0.12);
    }}
    .quote-inner {{ max-width: 760px; margin: 0 auto; }}
    .quote-mark {{
      font-family: var(--f-serif); font-size: 64px; line-height: 0.5;
      color: var(--gold); opacity: 0.6; margin-bottom: 18px;
    }}
    .quote-text {{
      font-family: var(--f-serif); font-weight: 300; font-style: italic;
      font-size: clamp(22px, 2.6vw, 32px); line-height: 1.35; color: var(--white);
    }}

    /* ── SAVE / NEXT STEP ── */
    .save-block {{
      margin-top: 48px; padding-top: 36px;
      border-top: 1px solid rgba(184,148,74,0.25); text-align: center;
    }}
    .save-eyebrow {{
      font-family: var(--f-sans); font-size: 12px; letter-spacing: 0.2em;
      text-transform: uppercase; color: var(--gold); margin-bottom: 12px;
    }}
    .save-note {{
      font-size: 14px; font-weight: 300; line-height: 1.7; color: #4A4437;
      max-width: 560px; margin: 0 auto 24px;
    }}
    .save-fields {{ display: flex; gap: 12px; justify-content: center; flex-wrap: wrap; margin-bottom: 18px; }}
    .save-input {{
      font-family: var(--f-sans); font-size: 14px; padding: 12px 16px;
      border: 1px solid rgba(23,20,15,0.25); background: #fff; color: #17140F;
      border-radius: 2px; min-width: 220px;
    }}
    .save-input:focus {{ outline: none; border-color: var(--gold); }}
    .save-btn {{
      font-family: var(--f-sans); font-size: 13px; letter-spacing: 0.15em;
      text-transform: uppercase; color: var(--white); background: var(--gold);
      border: none; padding: 16px 44px; border-radius: 2px; cursor: pointer;
      transition: background 0.2s ease;
    }}
    .save-btn:hover {{ background: var(--gold-lt); }}
    .save-btn:disabled {{ opacity: 0.6; cursor: default; }}
    .save-status {{
      margin-top: 16px; font-size: 13px; font-weight: 300; min-height: 18px;
      color: #2E7D32;
    }}
    .save-status.error {{ color: #B00020; }}

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

    /* ── OPTION PANELS (dropdowns + checkboxes) ── */
    .option-grid {{
      display: flex; flex-direction: column; gap: 8px; margin-bottom: 20px;
    }}
    .option-item {{
      display: flex; align-items: center; justify-content: space-between; gap: 16px;
      padding: 14px 16px;
      background: rgba(184,148,74,0.03);
      border: 1px solid rgba(184,148,74,0.1);
      cursor: pointer;
      transition: border-color 0.15s, background 0.15s;
      user-select: none;
    }}
    .option-item:hover {{
      border-color: rgba(184,148,74,0.3);
      background: rgba(184,148,74,0.08);
    }}
    .option-item:has(.opt-cb:checked) {{
      border-color: var(--gold);
      background: rgba(184,148,74,0.12);
    }}
    .option-name {{
      font-family: var(--f-sans); font-size: 13px; font-weight: 300;
      color: var(--white); line-height: 1.3; flex: 1;
    }}
    .option-controls {{
      display: flex; align-items: center; gap: 12px;
    }}
    .option-price {{
      font-family: var(--f-sans); font-size: 11px; font-weight: 300;
      color: rgba(184,148,74,0.55); letter-spacing: 0.04em; white-space: nowrap;
    }}
    .opt-select {{
      font-family: var(--f-sans); font-size: 13px; color: var(--white);
      background: var(--dark); border: 1px solid rgba(184,148,74,0.35);
      border-radius: 3px; padding: 6px 10px; cursor: pointer; min-width: 64px;
    }}
    .opt-select:focus {{ outline: none; border-color: var(--gold); }}
    .option-item-cb .opt-cb {{
      appearance: none; -webkit-appearance: none;
      width: 16px; height: 16px;
      border: 1.5px solid rgba(184,148,74,0.35);
      border-radius: 3px; background: transparent; cursor: pointer;
      position: relative; flex-shrink: 0;
      transition: background 0.15s, border-color 0.15s;
    }}
    .option-item-cb .opt-cb:checked {{
      background: var(--gold); border-color: var(--gold);
    }}
    .option-item-cb .opt-cb:checked::after {{
      content: '✓'; font-size: 10px; color: #17140F; font-weight: 700;
      position: absolute; top: -1px; left: 2px;
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
      {project_line}
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

  <script>
    const SYSTEM_BUDGETS = {system_js};
    const CAT_SYSTEMS    = {cat_js};
    const CAT_NAMES      = {json.dumps({cat_id: cat_name for cat_id, cat_name, _ in CATEGORIES})};
    const CLIENT_NAME    = {json.dumps(client_name)};
    const PROJECT_NAME   = {json.dumps(project_name or '')};

    // Track tier selections per system: system -> {{ tier, budget }}
    const selections = {{}};
    // Track zone/reader additions per system: system -> total added cost
    const zoneAdditions = {{}};
    // Track option-control additions per system (dropdowns + checkboxes): system -> total added cost
    const optionAdditions = {{}};

    // Per-tier unit price for an element carrying a data-units JSON map,
    // resolved against the tier currently selected for `system`. Missing -> 0.
    function unitFor(el, system) {{
      const sel = selections[system];
      if (!sel || sel.tier === 'none') return 0;
      let map = {{}};
      try {{ map = JSON.parse(el.dataset.units || '{{}}'); }} catch (e) {{ map = {{}}; }}
      return parseInt(map[sel.tier]) || 0;
    }}

    function selectOption(el) {{
      const system = el.dataset.system;
      const tier   = el.dataset.tier;
      const budget = parseInt(el.dataset.budget) || 0;

      // Deselect all cards for this system
      document.querySelectorAll(`.opt-card[data-system="${{system}}"]`).forEach(c => c.classList.remove('selected'));
      el.classList.add('selected');

      // Store tier selection
      selections[system] = {{ tier, budget }};

      // A system can have MORE THAN ONE option panel (e.g. access-control's
      // Entry/Mid panel vs its Premium panel). Show those whose show-tiers include
      // the selected tier; hide + reset the others.
      document.querySelectorAll(`.option-panel[data-system="${{system}}"]`).forEach(op => {{
        const showTiers = JSON.parse(op.dataset.showTiers || '[]');
        if (tier === 'none' || !showTiers.includes(tier)) {{
          op.style.display = 'none';
          op.querySelectorAll('.opt-select').forEach(s => {{ s.value = s.dataset.default || '0'; }});
          op.querySelectorAll('.opt-cb').forEach(cb => {{ cb.checked = cb.defaultChecked; }});
        }} else {{
          op.style.display = 'block';
        }}
      }});
      onOptionChange(system);

      // Handle zone panel visibility (audio)
      const panel = document.getElementById(`zone-panel-${{system}}`);
      if (panel) {{
        const showTiers = JSON.parse(panel.dataset.showTiers || '[]');
        if (tier === 'none' || !showTiers.includes(tier)) {{
          panel.style.display = 'none';
          panel.querySelectorAll('.zone-cb').forEach(cb => cb.checked = false);
          zoneAdditions[system] = 0;
          const itemsEl = document.getElementById(`zone-items-${{system}}`);
          if (itemsEl) itemsEl.textContent = '—';
        }} else {{
          panel.style.display = 'block';
          onZoneChange(system);   // recompute at the newly-selected tier's per-zone price
          return; // onZoneChange calls refreshCategoryForSystem
        }}
      }}

      refreshCategoryForSystem(system);
    }}

    function onZoneChange(system) {{
      const panel = document.getElementById(`zone-panel-${{system}}`);
      if (!panel || panel.style.display === 'none') {{
        zoneAdditions[system] = 0;
        refreshCategoryForSystem(system);
        return;
      }}
      let total = 0;
      const labels = [];
      panel.querySelectorAll('.zone-cb:checked').forEach(cb => {{
        total += unitFor(cb, system);   // TIER-SPECIFIC per-zone price
        labels.push(cb.closest('.zone-item').querySelector('.zone-name').textContent);
      }});
      zoneAdditions[system] = total;
      const itemsEl = document.getElementById(`zone-items-${{system}}`);
      if (itemsEl) itemsEl.textContent = labels.length > 0 ? labels.join(', ') : '—';
      refreshCategoryForSystem(system);
    }}

    function onOptionChange(system) {{
      // Sum across ALL visible option panels for this system, priced at the
      // selected tier. Per-unit prices are never displayed — only the subtotal moves.
      let total = 0;
      document.querySelectorAll(`.option-panel[data-system="${{system}}"]`).forEach(panel => {{
        if (panel.style.display === 'none') return;
        panel.querySelectorAll('.opt-select').forEach(sel => {{
          const qty = parseInt(sel.value) || 0;
          total += qty * unitFor(sel, system);
        }});
        panel.querySelectorAll('.opt-cb').forEach(cb => {{
          if (cb.checked) total += unitFor(cb, system);
        }});
      }});
      optionAdditions[system] = total;
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
          const adds = (zoneAdditions[sys] || 0) + (optionAdditions[sys] || 0);
          total += sel.budget + adds;
          // A zero baseline is only "TBD" when nothing has been added yet. Audio is
          // priced entirely per zone, so once zones are picked it is NOT unknown.
          if (sel.budget === 0 && adds === 0) hasTbd = true;
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

    // ── Save my selections: build a summary, download a copy, notify D-One ──
    const ZAR = new Intl.NumberFormat('en-ZA', {{style:'currency',currency:'ZAR',maximumFractionDigits:0}});

    function collectSummary() {{
      const cats = [];
      for (const [catId, systems] of Object.entries(CAT_SYSTEMS)) {{
        const {{ total, hasTbd, anySelected }} = getCategoryTotals(catId);
        const lines = [];
        for (const sys of systems) {{
          const sel = selections[sys];
          if (!sel) continue;
          let line = `${{sys}}: ${{sel.tier === 'none' ? 'Not Required' : sel.tier}}`;
          // audio zones chosen
          const zpanel = document.getElementById(`zone-panel-${{sys}}`);
          if (zpanel && zpanel.style.display !== 'none') {{
            const zones = [...zpanel.querySelectorAll('.zone-cb:checked')].map(cb => cb.closest('.zone-item').querySelector('.zone-name').textContent);
            if (zones.length) line += ` — zones: ${{zones.join(', ')}}`;
          }}
          // access-control / other add-ons chosen
          const adds = [];
          document.querySelectorAll(`.option-panel[data-system="${{sys}}"]`).forEach(op => {{
            if (op.style.display === 'none') return;
            op.querySelectorAll('.opt-select').forEach(s => {{ if ((parseInt(s.value)||0) > 0) adds.push(`${{s.value}}× ${{s.closest('.option-item').querySelector('.option-name').textContent}}`); }});
            op.querySelectorAll('.opt-cb:checked').forEach(cb => adds.push(cb.closest('.option-item').querySelector('.option-name').textContent));
          }});
          if (adds.length) line += ` — add-ons: ${{adds.join(', ')}}`;
          lines.push(line);
        }}
        if (anySelected) {{
          const amt = (total === 0 && hasTbd) ? 'TBD' : (ZAR.format(total) + (hasTbd ? ' + TBD' : ''));
          cats.push({{ category: CAT_NAMES[catId], estimate: amt, lines }});
        }}
      }}
      return cats;
    }}

    function summaryText(name, email) {{
      const cats = collectSummary();
      let out = `D-One — Proposal selections\n`;
      out += `Client: ${{CLIENT_NAME}}\n`;
      if (PROJECT_NAME) out += `Project: ${{PROJECT_NAME}}\n`;
      if (name)  out += `Submitted by: ${{name}}\n`;
      if (email) out += `Email: ${{email}}\n`;
      out += `\n`;
      if (!cats.length) {{ out += `(No selections made yet.)\n`; return out; }}
      cats.forEach(c => {{
        out += `${{c.category}} — ${{c.estimate}}\n`;
        c.lines.forEach(l => out += `   • ${{l}}\n`);
        out += `\n`;
      }});
      out += `Note: estimates are indicative, subject to detailed design and scope.\n`;
      return out;
    }}

    function downloadSummary(text) {{
      const blob = new Blob([text], {{ type: 'text/plain;charset=utf-8' }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      const slug = (CLIENT_NAME || 'proposal').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
      a.href = url; a.download = `d-one-selections-${{slug}}.txt`;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }}

    function encodeForm(data) {{
      return Object.keys(data).map(k => encodeURIComponent(k) + '=' + encodeURIComponent(data[k])).join('&');
    }}

    function saveSelections() {{
      const btn = document.getElementById('save-btn');
      const statusEl = document.getElementById('save-status');
      const name  = (document.getElementById('client-name')  || {{}}).value || '';
      const email = (document.getElementById('client-email') || {{}}).value || '';
      const cats = collectSummary();
      statusEl.className = 'save-status';
      if (!cats.length) {{
        statusEl.className = 'save-status error';
        statusEl.textContent = 'Please make at least one selection above first.';
        return;
      }}
      const text = summaryText(name, email);
      // 1) Always give the client a downloaded copy.
      downloadSummary(text);
      // 2) Notify D-One: post to the permanent inbox form (emails systems@ & operations@).
      btn.disabled = true;
      statusEl.textContent = 'Saving…';
      try {{
        const form = document.getElementById('d1-selections-form');
        form.client.value  = CLIENT_NAME;
        form.project.value = PROJECT_NAME;
        form.name.value    = name;
        form.email.value   = email;
        form.summary.value = text;
        form.submit();  // posts cross-site into the hidden iframe (no CORS)
        statusEl.textContent = 'Saved — a copy downloaded to your device and sent to D-One. We\\'ll be in touch.';
      }} catch (e) {{
        statusEl.textContent = 'Downloaded a copy to your device. If you were reviewing offline, please email it to systems@d-one.co.za.';
      }}
      btn.disabled = false;
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

    # Options — per-unit OPTION prices from proposal_budgets.json's "options" block
    options = {}
    if budgets_file_data and budgets_file_data.get('options'):
        options = budgets_file_data['options']

    # per_unit — TIER-SPECIFIC per-add-on prices (audio_zone, access_viewer/reader/intercom)
    per_unit = {}
    if budgets_file_data and budgets_file_data.get('per_unit'):
        per_unit = budgets_file_data['per_unit']

    # takeoff — drawing-derived add-on locations/limits for the option selectors.
    # Zone/location lists arrive as [[id,label], ...]; normalise inner lists to tuples.
    takeoff = {}
    if budgets_file_data and budgets_file_data.get('takeoff'):
        raw_takeoff = budgets_file_data['takeoff']
        for k, v in raw_takeoff.items():
            if isinstance(v, list) and v and isinstance(v[0], (list, tuple)):
                takeoff[k] = [tuple(pair) for pair in v]
            else:
                takeoff[k] = v

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

    # Cover image
    cover_image_b64 = img_b64(args.cover) if args.cover and os.path.exists(args.cover) else None
    if cover_image_b64:
        print(f"Loaded cover image: {args.cover}")

    logo_b64 = img_b64(LOGO_PATH)

    html = generate_html(args.client, args.project, budgets, logo_b64=logo_b64, cover_image_b64=cover_image_b64,
                         plan_images_b64=plan_images_b64,
                         audio_zones=audio_zones, zone_prices=zone_prices, options=options,
                         per_unit=per_unit, takeoff=takeoff)

    os.makedirs(args.output, exist_ok=True)
    out_path = os.path.join(args.output, 'index.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Generated: {out_path} ({os.path.getsize(out_path) // 1024} KB)")
    return out_path


if __name__ == '__main__':
    try:
        main()
    except ImageSlotError as e:
        print(f"\nImage lookup failed — generation stopped:\n\n{e}\n", file=sys.stderr)
        sys.exit(1)

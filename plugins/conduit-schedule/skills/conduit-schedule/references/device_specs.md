# D-One Device Conduit Specifications

Two lookup tables are provided:
1. **Device Lookup** — used when reading from a quote (Input Mode A)
2. **Icon → Device Lookup** — used when reading from a D-One floorplan PDF (Input Mode B)

---

## Conduit Size Rules

| Rule | Size |
|------|------|
| Standard minimum (all devices) | **25mm** |
| TV Point (multiple cables in one chase) | **2×25mm** |
| Never use | ~~20mm~~ |

---

## 1. Device Lookup (Quote Input)

| Device / Point | Conduit | Destination | Cable | Backbox | Power |
|---|---|---|---|---|---|
| IP Camera (interior turret/dome) | 25 | Head-End | CAT6 | Deep round | POE |
| IP Camera (exterior, pole/wall) | 25 | Head-End | CAT6 | Deep round | POE |
| Door Intercom (UA-Intercom-Viewer / UA-G3-Intercom) | 25 | Head-End | CAT6 | Flush round outdoor | No |
| G6 Entry Door Camera | 25 | Head-End | CAT6 | Flush round outdoor | POE |
| UniFi G6 Turret Camera | 25 | Head-End | CAT6 | Deep round | POE |
| Door Hub Mini / UniFi Access Door Hub | 25 | Head-End | CAT6 | Flush round outdoor | No |
| G6 Doorbell | 25 | Head-End | CAT6 | Flush round outdoor | POE |
| WiFi AP (indoor, any U6/U7 model) | 25 | Head-End | CAT6 | 4×4 | POE |
| WiFi AP (outdoor, U7-Pro-Outdoor / U6-Mesh) | 25 | Head-End | CAT6 | 4×4 | POE |
| In-Ceiling Speaker (any model) | 25 | AV Receiver | Speaker Cable 2-core | (ceiling void) | No |
| In-Wall Speaker (any model) | 25 | AV Receiver | Speaker Cable 2-core | (wall void) | No |
| Outdoor Speaker (B+W AM1, JBL bracket-mount) | 25 | AV Receiver | Speaker Cable 2-core | In-wall cavity | No |
| Subwoofer (in-wall/in-ceiling) | 25 | AV Receiver | Speaker Cable 2-core | (wall void) | No |
| Bookshelf Speaker (passive, on bracket) | 25 | AV Receiver | Speaker Cable 2-core | (wall void) | No |
| AV Receiver / AV Amplifier | 25 | Head-End | CAT6 | 4×4 deep | Yes |
| TV Point (wall plate) | 2×25 | Head-End | 3× CAT6 | 4×4 | Yes |
| Picture Slider / Motorised Screen (any size) | 25 | Head-End | 2-core flex | — | Yes |
| Lutron Keypad (any model) | 25 | Lighting DB | 4-core Mylar | 2×4 | No |
| Lutron HQP Processor (rack) | — | (rack item — no field conduit) | — | — | — |
| Motion Sensor 360 / Lutron Occupancy Sensor | 25 | Lighting DB | 4-core Mylar | Surface round | No |
| Motorised Blind | 25 | Lighting DB | 4-core Mylar | — | No |
| Motorised Curtain | 25 | Lighting DB | 4-core Mylar | — | No |
| Touch Panel | 25 | Head-End | CAT6 | 4×4 | Yes |
| Exit Button | 25 | Head-End | 2-core | Flush round | No |
| Audible Sounder | 25 | Head-End | CAT6 | Surface round | No |
| Network / Control Trunk (DB-to-DB or DB-to-Head-End) | 2×25 | Head-End | 4× CAT6 | — | Yes |
| Patch Panel / Switch / Rack equipment | — | (rack item) | — | — | — |

---

## 2. Icon → Device Lookup (Floorplan Input)

Map each icon key from the floorplan-icons skill to its conduit schedule entry.

| Icon Key | Point Name | Conduit | Destination | Cable | Backbox | Power |
|---|---|---|---|---|---|---|
| `wireless_access_point` | WiFi AP | 25 | Head-End | CAT6 | 4×4 | POE |
| `tv` | TV Point | 2×25 | Head-End | 3× CAT6 | 4×4 | Yes |
| `ceiling_speaker` | In-Ceiling Speaker | 25 | AV Receiver | Speaker Cable 2-core | (ceiling void) | No |
| `wall_speaker` | Outdoor / Wall Speaker | 25 | AV Receiver | Speaker Cable 2-core | In-wall cavity | No |
| `network_point` | Network Point | 25 | Head-End | CAT6 | 4×4 | No |
| `intercom_door_station` | Door Intercom (Door Station) | 25 | Head-End | CAT6 | Flush round outdoor | No |
| `facial_recognition_reader` | Facial Recognition Reader | 25 | Head-End | CAT6 | Flush round outdoor | POE |
| `intercom_receiver_panel` | Intercom Receiver Panel | 25 | Head-End | CAT6 | Flush round | No |
| `amplifier` | AV Receiver / Amplifier | 25 | Head-End | CAT6 | 4×4 deep | Yes |
| `server_cabinet` | *(Head-End — skip, rack item)* | — | — | — | — | — |
| `motion_sensor` | Motion Sensor 360 | 25 | Lighting DB | 4-core Mylar | Surface round | No |
| `light_switch_keypad` | Lutron Keypad | 25 | Lighting DB | 4-core Mylar | 2×4 | No |
| `cctv_bullet` | IP Camera (Exterior) | 25 | Head-End | CAT6 | Deep round | POE |
| `cctv_dome` | IP Camera (Interior) | 25 | Head-End | CAT6 | Deep round | POE |
| `motorised_blind` | Motorised Blind | 25 | Lighting DB | 4-core Mylar | — | No |
| `motorised_curtain` | Motorised Curtain | 25 | Lighting DB | 4-core Mylar | — | No |
| `touch_panel` | Touch Panel | 25 | Head-End | CAT6 | 4×4 | Yes |
| `exit_button` | Exit Button | 25 | Head-End | 2-core | Flush round | No |
| `audible_sounder` | Audible Sounder | 25 | Head-End | CAT6 | Surface round | No |
| `spotlight` | *(Lighting circuit — skip)* | — | — | — | — | — |

### Combining tv + network_point

When `tv` and `network_point` both appear in the same room, they represent the same
TV-point location. Merge them into a single row:

| Point | Conduit | Destination | Cable | Backbox | Power |
|---|---|---|---|---|---|
| TV Point | 2×25 | Head-End | 3× CAT6 | 4×4 | Yes |

Do not create two separate rows.

---

## Destination Notes

- **Head-End** = main rack / services room
- **Guest DB** = secondary DB in guest wing (use when clearly separate wing)
- **Lighting DB** = Lutron lighting panel (may appear as "Spanel", "L-DB")
- **AV Receiver** = local amplifier in same zone (speaker cables only)

## Power Column

| Condition | Value |
|---|---|
| Powered over POE | POE |
| Needs dedicated socket | Yes |
| Passive (no power) | No |

## Level Labels (D-One convention)

- **PERIMETER** — exterior gates, boundary cameras, entry doors
- **L1 BASEMENT** — lower ground or basement level
- **L2 GROUND** — ground floor / main entry level
- **L3 FIRST** — first floor / upper bedrooms

Match whatever floor labels the source document uses.

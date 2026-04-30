"""
Blanks Generator — Dear PyGui
Requirements: pip install dearpygui typst pillow
Portable: works as-is or compiled with PyInstaller (see bottom of file).
"""

import io
import os
import sys
import threading

# ── DPI awareness (must run before ANY GUI call) ──────────────────────────
def _init_dpi() -> float:
    """Declare per-monitor DPI awareness and return scale factor (1.0 = 96 dpi)."""
    if sys.platform == "win32":
        try:
            import ctypes
            # PROCESS_PER_MONITOR_DPI_AWARE = 2
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            dpi = ctypes.windll.user32.GetDpiForSystem()
            return dpi / 96.0
        except Exception:
            return 1.0
    # Linux / WSL / macOS: honour env vars set by the compositor
    for var in ("GDK_SCALE", "QT_SCALE_FACTOR", "XCURSOR_SIZE"):
        val = os.environ.get(var)
        if val:
            try:
                s = float(val)
                if 0.5 <= s <= 4.0:
                    return s
            except ValueError:
                pass
    return 1.0

SCALE: float = 1.75


import typst
from PIL import Image
import dearpygui.dearpygui as dpg

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PDF  = os.path.join(SCRIPT_DIR, "blanks_output.pdf")
PREVIEW_PDF = os.path.join(SCRIPT_DIR, "preview_one_team.pdf")

# ── Preview texture ─────────────────────────────────────────────────────────────
# Texture is rendered at 2× the display widget size for sharpness.
# PPI is also scaled so typst renders at the true physical resolution.
_BASE_PPI   = 110                        # base render PPI at scale=1
PREV_PPI    = _BASE_PPI * max(1, SCALE)  # e.g. 220 on 4K
_BASE_W, _BASE_H = 380, 537              # display widget at scale=1
PREV_W = int(_BASE_W * SCALE)
PREV_H = int(_BASE_H * SCALE)
TEX_W  = PREV_W * 2                     # texture always 2× display widget
TEX_H  = PREV_H * 2

# ── Typst shared definitions ───────────────────────────────────────────────────
# __LANG__ → "true" or "false" (flipped/landscape)
_DEFS = r"""
#let blank_cell(team_label, event, question_num, pic) = [
  #box(width: 90%, height: 80%, [
    #place(left  + top,    text(size: 10pt, team_label))
    #if pic != none [
      #place(right + top,  move(dx: 10%, dy: -15%, box(height: 70%, pic)))
    ]
    #place(center + horizon, text(
      size: 50pt,
      fill: color.black.transparentize(80%),
      [#question_num],
    ))
    #place(right + bottom, event)
  ])
]

#let blank_page(label, event, pic, c, r, q0) = {
  set page(margin: 0cm, flipped: __LAND__)
  let cells = range(q0, c * r + q0).map(n =>
    align(center + horizon, blank_cell(label, event, n, pic))
  )
  grid(
    columns: (100% / c,) * c,
    rows:    (100% / r,) * r,
    gutter:  0cm,
    stroke:  1pt + black,
    ..cells,
  )
}
"""

# Full multi-team document — 1 page per team
FULL_TMPL = "__FONT__\n" + _DEFS + """
#for i in range(__START__, __FINISH__ + 1) {
  let lbl = "__PFX__" + str(i)
  blank_page(lbl, "__LOC__", __PIC__, __W__, __H__, 1)
}
"""

# Single-page preview — shows team __PREV_TEAM__
PREV_TMPL = "__FONT__\n" + _DEFS + """
#blank_page("__PFX____PREV_TEAM__", "__LOC__", __PIC__, __W__, __H__, 1)
"""


def _pic_expr(pic: str) -> str:
    return f'image("{pic.strip()}")' if pic.strip() else "none"


def _font_line(font: str) -> str:
    return f'#set text(font: "{font.strip()}")' if font.strip() else ""


def _build(tmpl: str, start, finish, w, h, loc, pfx, pic, font, landscape,
           prev_team: int = 1) -> bytes:
    return (tmpl
        .replace("__FONT__",      _font_line(font))
        .replace("__LAND__",      "true" if landscape else "false")
        .replace("__START__",     str(start))
        .replace("__FINISH__",    str(finish))
        .replace("__W__",         str(w))
        .replace("__H__",         str(h))
        .replace("__LOC__",       loc)
        .replace("__PFX__",       pfx)
        .replace("__PIC__",       _pic_expr(pic))
        .replace("__PREV_TEAM__", str(prev_team))
    ).encode("utf-8")


# ── Live preview (debounced, background thread) ───────────────────────────────
_ptimer: threading.Timer | None = None
_plock  = threading.Lock()


def _vals() -> dict:
    return {
        "w":         dpg.get_value("sl_w"),
        "h":         dpg.get_value("sl_h"),
        "s":         dpg.get_value("sl_start"),
        "f":         dpg.get_value("sl_finish"),
        "loc":       dpg.get_value("in_loc"),
        "pfx":       dpg.get_value("in_pfx"),
        "pic":       dpg.get_value("in_pic"),
        "font":      dpg.get_value("in_font"),
        "land":      dpg.get_value("chk_land"),
        "prev_team": dpg.get_value("in_prev_team"),
    }


def schedule_preview(*_):
    global _ptimer
    if _ptimer:
        _ptimer.cancel()
    _ptimer = threading.Timer(0.7, _do_preview)
    _ptimer.daemon = True
    _ptimer.start()
    _update_stats()


def _do_preview():
    with _plock:
        v   = _vals()
        src = _build(PREV_TMPL, v["s"], v["s"], v["w"], v["h"],
                     v["loc"], v["pfx"], v["pic"], v["font"], v["land"],
                     v["prev_team"])
        try:
            if dpg.does_item_exist("prev_status"):
                dpg.set_value("prev_status", "Rendering preview…")
            png = typst.compile(src, format="png", ppi=PREV_PPI, root=SCRIPT_DIR)
            _show_png(png)
            if dpg.does_item_exist("prev_status"):
                dpg.set_value("prev_status", "")
        except Exception as exc:
            if dpg.does_item_exist("prev_status"):
                dpg.set_value("prev_status", f"Preview error: {str(exc)[:150]}")


def _show_png(png_bytes: bytes):
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    img.thumbnail((TEX_W, TEX_H), Image.LANCZOS)
    bg  = Image.new("RGBA", (TEX_W, TEX_H), (210, 210, 210, 255))
    bg.paste(img, ((TEX_W - img.width) // 2, (TEX_H - img.height) // 2))
    data = [c / 255.0 for px in bg.getdata() for c in px]
    dpg.set_value("preview_tex", data)


# ── PDF compilation ───────────────────────────────────────────────────────────
def _compile_pdf(start, finish, out_path, btn_tag):
    v   = _vals()
    src = _build(FULL_TMPL, start, finish, v["w"], v["h"],
                 v["loc"], v["pfx"], v["pic"], v["font"], v["land"])

    def _set_status(text: str, color: tuple[int, int, int] | None = None):
        if dpg.does_item_exist("status"):
            if color is not None:
                dpg.configure_item("status", color=color)
            dpg.set_value("status", text)

    dpg.configure_item(btn_tag, enabled=False)
    _set_status("Compiling…", (220, 200, 80))

    def _run():
        try:
            pdf = typst.compile(src, format="pdf", root=SCRIPT_DIR)
            with open(out_path, "wb") as fh:
                fh.write(pdf)
            _set_status(f"Done  →  {out_path}", (120, 255, 120))
            _open_file(out_path)
        except Exception as exc:
            _set_status(f"Error: {str(exc)[:250]}", (255, 100, 100))
        finally:
            dpg.configure_item(btn_tag, enabled=True)

    threading.Thread(target=_run, daemon=True).start()


def _open_file(path: str):
    import subprocess
    try:
        if sys.platform.startswith("linux"):
            subprocess.Popen(["xdg-open", path],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            os.startfile(path)  # type: ignore[attr-defined]
    except Exception:
        pass  # viewer not available (e.g. WSL without xdg-open); path shown in status bar


def _update_stats(*_):
    w = dpg.get_value("sl_w");  h = dpg.get_value("sl_h")
    s = dpg.get_value("sl_start"); f = dpg.get_value("sl_finish")
    teams = max(0, f - s + 1)
    if dpg.does_item_exist("stats"):
        dpg.set_value("stats",
            f"{w}×{h}  •  {w*h} blanks/page  •  {w*h} questions/team  •  "
            f"{teams} teams  •  {teams} pages total")


# ── Callbacks ─────────────────────────────────────────────────────────────────
def cb_range(sender, _):
    s = dpg.get_value("sl_start");  f = dpg.get_value("sl_finish")
    if sender == "sl_start" and s > f:
        dpg.set_value("sl_finish", s)
    elif sender == "sl_finish" and f < s:
        dpg.set_value("sl_start", f)
    schedule_preview()


def cb_prev_pdf(*_):
    s = dpg.get_value("sl_start")
    _compile_pdf(s, s, PREVIEW_PDF, "btn_prev")


def cb_gen(*_):
    _compile_pdf(dpg.get_value("sl_start"), dpg.get_value("sl_finish"),
                 OUTPUT_PDF, "btn_gen")


# ── UI font with Cyrillic support ─────────────────────────────────────────────
def _find_ui_font() -> str | None:
    # Highest priority: user-provided font near project/app.
    # Works for source run and for frozen app when user drops assets near .exe.
    roots: list[str] = [SCRIPT_DIR]

    if getattr(sys, "frozen", False):
        roots.append(os.path.dirname(os.path.abspath(sys.executable)))

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(meipass)

    for root in roots:
        for rel in (
            os.path.join("assets", "font.ttf"),
            os.path.join("assets", "DejaVuSans.ttf"),
            os.path.join("assets", "NotoSans-Regular.ttf"),
        ):
            p = os.path.join(root, rel)
            if os.path.exists(p):
                return p

    windir = os.environ.get("WINDIR", r"C:\Windows")
    for p in [
        "/usr/share/fonts/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        os.path.join(windir, "Fonts", "arialuni.ttf"),
        os.path.join(windir, "Fonts", "arial.ttf"),
        os.path.join(windir, "Fonts", "calibri.ttf"),
        os.path.join(windir, "Fonts", "segoeui.ttf"),
        os.path.join(windir, "Fonts", "tahoma.ttf"),
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]:
        if os.path.exists(p):
            return p
    return None


# ── Viewport resize ───────────────────────────────────────────────────────────
LEFT_W = int(500 * SCALE)   # left panel width scales with DPI


def on_resize():
    vw = dpg.get_viewport_width()
    vh = dpg.get_viewport_height()
    aw = max(80, vw - LEFT_W - 28)
    ah = max(80, vh - 90)
    # Fit page within available area, keeping A4 portrait ratio PREV_W:PREV_H
    if aw / ah > PREV_W / PREV_H:
        ph = ah;  pw = int(ah * PREV_W / PREV_H)
    else:
        pw = aw;  ph = int(aw * PREV_H / PREV_W)
    dpg.configure_item("preview_img", width=pw, height=ph)
    # Center the image horizontally in the right panel
    offset = max(0, (aw - pw) // 2)
    dpg.configure_item("preview_group", indent=offset)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    dpg.create_context()

    # Load a Cyrillic-capable font, sized for the display DPI
    font_path = _find_ui_font()
    font_note = "default"
    if font_path:
        font_size = max(13, int(15 * SCALE))
        with dpg.font_registry():
            # DearPyGui defaults to a limited glyph range; add Cyrillic explicitly.
            with dpg.font(font_path, font_size) as fnt:
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Default)
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Cyrillic)
                # Include Cyrillic blocks explicitly for Dear ImGui builds
                # where range hints are not enough.
                dpg.add_font_range(0x0020, 0x00FF)  # basic latin + latin-1
                dpg.add_font_range(0x0400, 0x052F)  # Cyrillic + Cyrillic Supplement
                dpg.add_font_range(0x2DE0, 0x2DFF)  # Cyrillic Extended-A
                dpg.add_font_range(0xA640, 0xA69F)  # Cyrillic Extended-B
                dpg.add_font_range(0x2116, 0x2116)  # Numero sign
        dpg.bind_font(fnt)
        font_note = os.path.basename(font_path)

    # Initial grey texture — replaced by rendered preview asap
    blank_data = [0.82, 0.82, 0.82, 1.0] * (TEX_W * TEX_H)
    with dpg.texture_registry():
        dpg.add_dynamic_texture(TEX_W, TEX_H, blank_data, tag="preview_tex")

    dpg.create_viewport(title="Blanks Generator",
                         width=int(980 * SCALE), height=int(700 * SCALE),
                         resizable=True)

    with dpg.window(tag="win", no_title_bar=True, no_resize=True,
                    no_move=True, no_close=True):

        with dpg.table(header_row=False, borders_innerV=True, pad_outerX=True):
            dpg.add_table_column(width_fixed=True, init_width_or_weight=LEFT_W)
            dpg.add_table_column()

            with dpg.table_row():

                # ── Left: settings ────────────────────────────────────────────
                with dpg.table_cell():
                    dpg.add_text("Event / Location")
                    dpg.add_input_text(
                        tag="in_loc", width=-1,
                        on_enter=True, callback=schedule_preview,
                        default_value="", hint="Location  (press Enter to update preview)",
                    )

                    dpg.add_spacer(height=4)
                    dpg.add_text("Team Label Prefix")
                    dpg.add_input_text(
                        tag="in_pfx", width=-1,
                        on_enter=True, callback=schedule_preview,
                        default_value="Team №", hint="e.g. Team №",
                    )

                    dpg.add_spacer(height=4)
                    dpg.add_text("Font  (blank = typst default)")
                    dpg.add_input_text(
                        tag="in_font", width=-1,
                        on_enter=True, callback=schedule_preview,
                        default_value="", hint="e.g. Arial, PT Sans, Roboto",
                    )

                    dpg.add_spacer(height=8)
                    dpg.add_text("Team Range")
                    with dpg.group(horizontal=True):
                        dpg.add_slider_int(
                            tag="sl_start", label="from",
                            default_value=1, min_value=1, max_value=300,
                            width=int(215 * SCALE), callback=cb_range,
                        )
                        dpg.add_spacer(width=4)
                        dpg.add_slider_int(
                            tag="sl_finish", label="to",
                            default_value=60, min_value=1, max_value=300,
                            width=int(215 * SCALE), callback=cb_range,
                        )

                    dpg.add_spacer(height=8)
                    dpg.add_separator()
                    dpg.add_text("Page Layout", color=(180, 210, 255))
                    dpg.add_spacer(height=4)

                    dpg.add_slider_int(
                        tag="sl_w", label="Columns",
                        default_value=4, min_value=1, max_value=10,
                        width=-1, callback=schedule_preview,
                    )
                    dpg.add_slider_int(
                        tag="sl_h", label="Rows   ",
                        default_value=9, min_value=1, max_value=14,
                        width=-1, callback=schedule_preview,
                    )

                    dpg.add_spacer(height=4)
                    dpg.add_checkbox(
                        tag="chk_land", label="Landscape (A4 rotated 90°)",
                        default_value=False, callback=schedule_preview,
                    )

                    dpg.add_spacer(height=8)
                    dpg.add_text("Logo image  (path from project root, or empty)")
                    dpg.add_input_text(
                        tag="in_pic", width=-1,
                        on_enter=True, callback=schedule_preview,
                        default_value="", hint="e.g. /assets/logo.svg  (Enter to update)",
                    )

                    dpg.add_spacer(height=10)
                    dpg.add_separator()
                    dpg.add_spacer(height=6)

                    dpg.add_button(
                        tag="btn_prev", label="Save Preview PDF  (1 team)",
                        width=-1, height=42, callback=cb_prev_pdf,
                    )
                    dpg.add_spacer(height=4)
                    dpg.add_button(
                        tag="btn_gen", label="Generate PDF  —  all teams",
                        width=-1, height=42, callback=cb_gen,
                    )

                # ── Right: live rendered preview ───────────────────────────────
                with dpg.table_cell():
                    with dpg.group(horizontal=True):
                        dpg.add_text("Preview team \u2116")
                        dpg.add_input_int(
                            tag="in_prev_team",
                            default_value=1, min_value=1, max_value=300,
                            min_clamped=True, max_clamped=True,
                            width=100, callback=schedule_preview,
                            on_enter=True,
                        )
                    with dpg.group(tag="preview_group"):
                        dpg.add_image("preview_tex", tag="preview_img",
                                      width=PREV_W, height=PREV_H)

    dpg.set_primary_window("win", True)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_viewport_resize_callback(on_resize)
    dpg.configure_app(wait_for_input=True)
    if dpg.does_item_exist("status"):
        dpg.set_value(
            "status",
            f"Ready. UI font: {font_note} | scale: {SCALE:.2f}",
        )
    _update_stats()
    schedule_preview()      # kick off initial render
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()

# ── PyInstaller portable exe ──────────────────────────────────────────────────
# If 'pyinstaller' is not in PATH, use: python3 -m PyInstaller
#
# Windows/Linux one-file build (run from the project folder):
#
#   python3 -m PyInstaller --onefile --noconsole \
#       --collect-all dearpygui \
#       --collect-all typst \
#       --collect-all PIL \
#       app.py
#
# To bundle a Cyrillic font so the UI looks correct on machines without
# DejaVu / Arial, copy any .ttf to assets/font.ttf first:
#
#   mkdir -p assets
#   cp /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf assets/font.ttf
#   python3 -m PyInstaller --onefile --noconsole \
#       --collect-all dearpygui --collect-all typst --collect-all PIL \
#       --add-data "assets/font.ttf:assets" \
#       app.py

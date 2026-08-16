#!/usr/bin/env python3
"""
sbc_grid.py — Authentic Sarvatobhadra Chakra 9x9 board + geometric vedha engine.

This replaces the faked index-offset model that used to live in sbc_scoring.py
(VEDA_OFFSETS = [9,18]... — invented numbers). Here the vedha is computed the
way the classical chakra actually works: from real cell coordinates and each
planet's live motion state.

VERIFIED CLASSICAL CONSTRUCTION (sources below)
-----------------------------------------------
* 9x9 = 81 cells, counted clockwise from the NE (Ishana) corner.
* Concentric rings:
    - outer 32-box ring : 28 nakshatras + 4 vowel corners (a, aa, i, ii)
    - 7x7 ring          : 20 consonants + vowel corners (u, uu, ri, rii)
    - 5x5 ring          : 12 rashis     + vowel corners (lu, luu, e, ai)
    - 3x3 ring          : tithis+weekdays + vowel corners (o, au, am, ah)
    - centre            : Poorna tithi + Saturday
* Nakshatra order is DIRECTIONAL around the border:
    - East  (top)    : Krittika -> Ashlesha
    - South (right)  : Magha -> Vishakha
    - West  (bottom) : Anuradha -> Shravana (Abhijit inserted before Shravana)
    - North (left)   : Dhanishta -> Bharani
* VEDHA is geometric + motion-driven. A graha pierces (a) the cell it sits on,
  and (b) a line across the chakra:
    - mean/normal speed -> FRONT  (Sammukha) : straight through the centre
    - swift & direct    -> LEFT   (Vaama)    : one diagonal
    - retrograde        -> RIGHT  (Dakshina) : the other diagonal
  The Sun and the two lunar nodes (Rahu/Ketu) cast all three simultaneously.
  Vedha by benefics (Mo, Me, Ju, Ve) is favourable; by malefics
  (Su, Ma, Sa, Ra, Ke) unfavourable.

Sources:
  en.wikipedia.org/wiki/Sarvatobhadra_Chakra
  sarvatobhadrachakra.com/introduction-of-sarvatobhadra-chakra/
  modernastro.com/astrology/vedic/sarvatobhadra  (motion->direction rule)
  Classical: Brihmayamala, Phaladeepika ch.26, Narapati Jayacharya.

NOTE ON FIDELITY: the ring/corner *ornamentation* (which exact vowel/consonant
sits in each non-nakshatra cell) is not yet fully populated — only the pieces
the trading engine consumes (nakshatra + rashi positions, and the geometric
vedha rays) are authoritative here. Border nakshatra placement is validated
against the reference screenshot's top row (Krittika..Ashlesha, L->R).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

Coord = Tuple[int, int]  # (row, col), row 0 = top = East

GRID_N = 9
CENTER: Coord = (4, 4)


class CellType(Enum):
    NAKSHATRA = "nakshatra"
    VOWEL = "vowel"
    CONSONANT = "consonant"
    RASHI = "rashi"
    TITHI = "tithi"
    CENTER = "center"


# --- Directional nakshatra sequences (7 per side) ---------------------------
# Every one of the 27 nakshatras + Abhijit (28) placed exactly once.
_EAST = ["Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu",
         "Pushya", "Ashlesha"]
_SOUTH = ["Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra",
          "Swati", "Vishakha"]
_WEST = ["Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
         "Abhijit", "Shravana"]
_NORTH = ["Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada",
          "Revati", "Ashwini", "Bharani"]

# 12 rashis on the 5x5 ring, in zodiacal order starting from the sign shown at
# the top-left of the reference screenshot.
RASHIS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
          "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

# Vowel corners per ring (outermost -> inner).
_VOWEL_CORNERS = [
    ["a", "aa", "i", "ii"],
    ["u", "uu", "ri", "rii"],
    ["lu", "luu", "e", "ai"],
    ["o", "au", "am", "ah"],
]


@dataclass
class Cell:
    coord: Coord
    ctype: CellType
    label: str = ""          # nakshatra / rashi / vowel / consonant name
    ring: int = 0            # 0 = outermost ... 4 = centre


def _ring_perimeter(n: int, ring: int) -> List[Coord]:
    """Clockwise perimeter coords of the `ring`-th concentric square.

    ring 0 -> full 9x9 border; ring 1 -> 7x7 border; etc. Clockwise starting
    from that ring's top-left corner, i.e. top row L->R, right col T->B,
    bottom row R->L, left col B->T.
    """
    lo = ring
    hi = n - 1 - ring
    if lo == hi:
        return [(lo, lo)]
    coords: List[Coord] = []
    for c in range(lo, hi + 1):        # top row L->R
        coords.append((lo, c))
    for r in range(lo + 1, hi + 1):    # right col T->B
        coords.append((r, hi))
    for c in range(hi - 1, lo - 1, -1):  # bottom row R->L
        coords.append((hi, c))
    for r in range(hi - 1, lo, -1):    # left col B->T
        coords.append((r, lo))
    return coords


def _place_border_nakshatras(cells: Dict[Coord, Cell]) -> Dict[str, Coord]:
    """Place 28 nakshatras + 4 vowel corners on the outer ring.

    Sides map to screenshot orientation: top=East, right=South, bottom=West,
    left=North — a continuous clockwise loop that puts Krittika at (0,1) and
    Ashlesha at (0,7), matching the reference chakra's top row.
    """
    nak_at: Dict[str, Coord] = {}
    top = [(0, c) for c in range(1, 8)]          # East  : (0,1)..(0,7) L->R
    right = [(r, 8) for r in range(1, 8)]        # South : (1,8)..(7,8) T->B
    bottom = [(8, c) for c in range(7, 0, -1)]   # West  : (8,7)..(8,1) R->L
    left = [(r, 0) for r in range(7, 0, -1)]     # North : (7,0)..(1,0) B->T

    for side_coords, seq in ((top, _EAST), (right, _SOUTH),
                             (bottom, _WEST), (left, _NORTH)):
        for coord, name in zip(side_coords, seq):
            cells[coord] = Cell(coord, CellType.NAKSHATRA, name, ring=0)
            nak_at[name] = coord

    # 4 vowel corners of the outer ring
    for coord, vw in zip([(0, 0), (0, 8), (8, 8), (8, 0)], _VOWEL_CORNERS[0]):
        cells[coord] = Cell(coord, CellType.VOWEL, vw, ring=0)
    return nak_at


def _place_rashis(cells: Dict[Coord, Cell]) -> Dict[str, Coord]:
    """Place the 12 rashis on the 5x5 ring (ring index 2)."""
    rashi_at: Dict[str, Coord] = {}
    perim = _ring_perimeter(GRID_N, 2)   # 16 cells: 12 rashi + 4 vowel corners
    corners = {(2, 2), (2, 6), (6, 6), (6, 2)}
    seq = iter(RASHIS)
    cidx = 0
    for coord in perim:
        if coord in corners:
            vw = _VOWEL_CORNERS[2][cidx % 4]
            cidx += 1
            cells[coord] = Cell(coord, CellType.VOWEL, vw, ring=2)
        else:
            name = next(seq)
            cells[coord] = Cell(coord, CellType.RASHI, name, ring=2)
            rashi_at[name] = coord
    return rashi_at


def _place_remaining(cells: Dict[Coord, Cell]) -> None:
    """Fill 7x7 consonant ring, 3x3 tithi ring, and centre (placeholders)."""
    for coord in _ring_perimeter(GRID_N, 1):       # consonant ring
        cells.setdefault(coord, Cell(coord, CellType.CONSONANT, "", ring=1))
    for coord in _ring_perimeter(GRID_N, 3):       # tithi/weekday ring
        cells.setdefault(coord, Cell(coord, CellType.TITHI, "", ring=3))
    cells.setdefault(CENTER, Cell(CENTER, CellType.CENTER, "Poorna/Sat", ring=4))


@dataclass
class SBCBoard:
    cells: Dict[Coord, Cell]
    nakshatra_at: Dict[str, Coord]
    rashi_at: Dict[str, Coord]

    def coord_of(self, nakshatra: str) -> Optional[Coord]:
        return self.nakshatra_at.get(nakshatra)

    def nakshatra_at_coord(self, coord: Coord) -> Optional[str]:
        cell = self.cells.get(coord)
        if cell and cell.ctype == CellType.NAKSHATRA:
            return cell.label
        return None


def build_board() -> SBCBoard:
    cells: Dict[Coord, Cell] = {}
    nak_at = _place_border_nakshatras(cells)
    rashi_at = _place_rashis(cells)
    _place_remaining(cells)
    # any still-empty cell -> blank consonant, so the board is fully 81 cells
    for r in range(GRID_N):
        for c in range(GRID_N):
            cells.setdefault((r, c), Cell((r, c), CellType.CONSONANT, "", ring=1))
    return SBCBoard(cells=cells, nakshatra_at=nak_at, rashi_at=rashi_at)


# --- Geometric vedha ray tracing --------------------------------------------

VedhaDir = str  # 'sammukha' | 'vama' | 'dakshina'


def _line_cells(a: Coord, b: Coord) -> List[Coord]:
    """Integer grid cells on the straight segment a->b (Bresenham), excl. a."""
    (r0, c0), (r1, c1) = a, b
    dr, dc = abs(r1 - r0), abs(c1 - c0)
    sr = 1 if r1 > r0 else -1
    sc = 1 if c1 > c0 else -1
    err = dr - dc
    r, c = r0, c0
    out: List[Coord] = []
    while (r, c) != (r1, c1):
        e2 = 2 * err
        if e2 > -dc:
            err -= dc
            r += sr
        if e2 < dr:
            err += dr
            c += sc
        out.append((r, c))
    return out


def _diagonal_cells(start: Coord, dr: int, dc: int) -> List[Coord]:
    """Walk a diagonal from `start` in (dr,dc) until off-grid, excl. start."""
    r, c = start
    out: List[Coord] = []
    r += dr
    c += dc
    while 0 <= r < GRID_N and 0 <= c < GRID_N:
        out.append((r, c))
        r += dr
        c += dc
    return out


def vedha_targets(board: SBCBoard, source: Coord,
                  direction: VedhaDir) -> List[Coord]:
    """Cells pierced by a vedha ray of `direction` from `source`.

    * sammukha (front) : straight line through the centre to the mirror cell
    * vama    (left)   : the '/' diagonal through the cell (both arms)
    * dakshina(right)  : the '\\' diagonal through the cell (both arms)
    """
    if direction == "sammukha":
        mirror = (GRID_N - 1 - source[0], GRID_N - 1 - source[1])
        return _line_cells(source, mirror)
    if direction == "vama":       # '/' diagonal : (+1,-1) and (-1,+1)
        return _diagonal_cells(source, 1, -1) + _diagonal_cells(source, -1, 1)
    if direction == "dakshina":   # '\' diagonal : (+1,+1) and (-1,-1)
        return _diagonal_cells(source, 1, 1) + _diagonal_cells(source, -1, -1)
    raise ValueError(f"unknown vedha direction: {direction}")


def ray_segment(source: Coord, direction: VedhaDir) -> Tuple[Coord, Coord]:
    """The (start, end) grid cells of a vedha ray, for drawing a line.

    * sammukha : source -> mirror cell through the centre
    * vama     : the full '/' diagonal across the board through source
    * dakshina : the full '\\' diagonal across the board through source
    """
    if direction == "sammukha":
        return source, (GRID_N - 1 - source[0], GRID_N - 1 - source[1])
    dr, dc = (1, -1) if direction == "vama" else (1, 1)
    # walk both ways to the board edge
    def _edge(sr: int, sc: int) -> Coord:
        r, c = source
        while 0 <= r + sr < GRID_N and 0 <= c + sc < GRID_N:
            r += sr
            c += sc
        return (r, c)
    return _edge(-dr, -dc), _edge(dr, dc)


def active_directions(retrograde: bool, fast: bool,
                      casts_all: bool) -> List[VedhaDir]:
    """Which vedha ray(s) a graha casts, from its motion state.

    mean/normal -> front; swift-direct -> left; retrograde -> right.
    Sun and the nodes (casts_all) cast all three.
    """
    if casts_all:
        return ["sammukha", "vama", "dakshina"]
    if retrograde:
        return ["dakshina"]
    if fast:
        return ["vama"]
    return ["sammukha"]


def nakshatra_vedhas(board: SBCBoard, source_nakshatra: str,
                     directions: List[VedhaDir]) -> Dict[VedhaDir, List[str]]:
    """For a graha on `source_nakshatra`, the nakshatras it pierces per ray."""
    src = board.coord_of(source_nakshatra)
    out: Dict[VedhaDir, List[str]] = {}
    if src is None:
        return out
    for d in directions:
        hits: List[str] = []
        for coord in vedha_targets(board, src, d):
            nak = board.nakshatra_at_coord(coord)
            if nak and nak != source_nakshatra:
                hits.append(nak)
        out[d] = hits
    return out


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    b = build_board()
    print(f"Board: {len(b.cells)} cells, "
          f"{len(b.nakshatra_at)} nakshatras, {len(b.rashi_at)} rashis")
    print("\nTop row (East, should read Krittika..Ashlesha):")
    print("  " + " ".join(b.nakshatra_at_coord((0, c)) or "·"
                          for c in range(GRID_N)))
    print("\nExample vedhas — Krittika, all three rays:")
    for d, hits in nakshatra_vedhas(
            b, "Krittika", ["sammukha", "vama", "dakshina"]).items():
        print(f"  {d:9s}: {', '.join(hits) or '(none)'}")

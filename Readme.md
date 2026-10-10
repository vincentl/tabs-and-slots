# Tabs & Slots

An Inkscape extension for laser-cut boxes: add kerf-compensated tabs and slots to each side of a panel, one side at a time.

## Install

Copy `tabslot.py` and `tabslot.inx` into your Inkscape user extensions folder, then restart Inkscape.

| OS      | Folder                                                                  |
| ------- | ----------------------------------------------------------------------- |
| macOS   | `~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions/` |
| Linux   | `~/.config/inkscape/extensions/`                                        |
| Windows | `%APPDATA%\inkscape\extensions\`                                        |

The extension appears under **Extensions → Modify Path → Tabs & Slots**.

## Make a panel

1. **Draw** a rectangle for the panel's outer edge.
2. **Split/Join → Split into Sides.** The rectangle becomes one path per side.
3. **Tabs & Slots.** Select a side, choose its settings, and apply. Repeat for each side.
4. **Split/Join → Join Sides and Holes.** Select all the sides, plus any inner shapes that should be cut out, and apply.

The result is a single path. Its fill covers only the material you keep: the outline including tabs, minus the inner holes.

## Tabs & Slots settings

| Setting            | What it does                                                        |
| ------------------ | ------------------------------------------------------------------- |
| Material Thickness | Depth of each tab or slot, in mm                                    |
| Laser Kerf         | Width of the laser cut, in µm; tabs and slots are adjusted for it   |
| Steps              | Number of tabs or slots along the side                              |
| Operation          | Tabs stick out from the edge; slots cut into it                     |
| Normal Vector      | Which side of the line the tabs or slots go                         |
| Phantom Material   | Space the tabs as if the side ran one material thickness past its start, end or both, for corners where another panel overlaps |
| Add a slot for each tab | Also draw a matching slot for each tab, as a separate cut      |

## Tips

- Run **Join** on all the sides at once. Sides can be in any order or direction.
- To add decoration such as a pattern over an inner hole, convert it to a filled shape (**Path → Stroke to Path**), overlap it with the frame, and **Path → Union** the two.

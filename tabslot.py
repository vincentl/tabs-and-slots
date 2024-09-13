
#!/usr/bin/env python3
'''
Copyright 2024 Vincent Lucarelli

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the “Software”), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

'''
import inkex

def slot_path(src, step, notch):
    path = inkex.paths.Path()
    path.append(inkex.paths.Move(src.x, src.y))
    for add in (step, notch, -step):
        src += add
        path.append(inkex.paths.Line(src.x, src.y))
    path.append(inkex.paths.ZoneClose())
    element = inkex.PathElement()
    element.set_path(path)
    return element

def create_plan(prefix, count, body, suffix):
    for item in prefix:
        yield item
    for _ in range(count):
        for item in body:
            yield item
    for item in suffix:
        yield item  

# Kerf = diameter of laser beam
#
# +-----+----------+-----+       +-----+----------+-----+       +-----+----------+-----+
# | k/2 | s        | k/2 | s - k | k/2 | s        | k/2 | s - k | k/2 | s        | k/2 |
# |                      +-------+                      +-------+                      |
#
#                  +-------------------+               +-------------------+
#                  |                   |               |                   |
# +----------------+                   +---------------+                   +----------------+
# | k/2 | s - k/2  | s + k             | s - k         | s + k             | s - k/2  | k/2 |
#
#  Input is a path from the left + to the right +, but when the laser follows the perpendicular
#  edges, the total length of the top edge is k shorter than the length of cut line. After
#  cutting, we want the final top edge evenly divided into sections.
#
#  s +/- k is horizontal motion of the laser. n is vertical
#
#  Turn into the part      - slots - (s+k),  n, (s-k), -n, (s+k),  n, (s-k), -n, (s+k)
#  Turn away from the part - tab   - (s  ), -n, (s+k),  n, (s-k), -n, (s+k),  n, (s  )

def steps(src, dst, options, transform, svg):
    # setup return types
    result = []
    slots = inkex.Group(id='slots')
    slots.style = inkex.Style({"stroke": "#000000", "stroke-width": "0.1", "fill": "none"})

    # Convert dimensional options to user units
    material = svg.to_dimensionless(options.material)
    kerf_norm = svg.to_dimensionless(options.kerf / 1000.0)
    vec_to_line = lambda v: inkex.paths.Line(v.x + src.x, v.y + src.y)

    full = dst - src                                                  # vector pointed along the edge
    unit = full/abs(full)                                             # unit vector pointing the edge
    phantom = material * unit if options.phantom else 0 * unit        # phantom vector
    kerf = kerf_norm * unit                                           # kerf correction in direction of edge
    step = (full + 2 * phantom - kerf) / (1 + 2*options.count)        # final edge length of each step
    notch = inkex.transforms.Vector2d(-full.y, full.x)                # perpendicular
    notch = material * notch / abs(notch)                             # perpendicular equal to material thickness
    notch = notch if options.normal == 'positive' else -notch

    match options.operation:
        case 'tab':
            plan = create_plan([step - phantom       ], options.count - 1, [-notch, step + kerf, notch, step - kerf], [-notch, step + kerf, notch, step - phantom       ])
        case 'slot':
            plan = create_plan([step - phantom + kerf], options.count - 1, [notch, step - kerf, -notch, step + kerf], [notch, step - kerf, -notch, step - phantom + kerf])

    mark = 0 * unit
    for move in plan:
        mark = move + mark
        result += [vec_to_line(mark)]


#        if (i & 0x01) == slot_parity:
#            slot = slot_path(src + mark - 1.5 * notch + 2*kerf, step - 2*kerf, notch * (1 - kerf_norm/abs(notch)))
#            slot.transform = transform
#            slots.add(slot)

    return result, slots

class TabSlot(inkex.EffectExtension):
    def add_arguments(self, options):
        options.add_argument('-m', '--material', type=float, default=3.0, help='material thickness in mm')
        options.add_argument('-k', '--kerf', type=float, default=0.08, help='laser kerf in mm')
        options.add_argument('-n', '--count', type=int, default=2, help='number of steps to take along path')
        options.add_argument('-t', '--normal', type=str, default='positive', help='normal vector direction')
        options.add_argument('-o', '--operation', type=str, default='slots', help='cut tabs or slots')
        options.add_argument('-s', '--slots', type=inkex.Boolean, default=False, help='add matching slots')
        options.add_argument('-p', '--phantom', type=inkex.Boolean, default=False, help='add phantom material at ends')

    def effect(self):
        # Iterate over the selected paths
        for node in self.svg.selection.get(inkex.PathElement):
            transform = node.composed_transform()
            path = node.path.to_absolute()
            result = []
            # Iterate over the elements in the path
            for proxy in path.proxy_iterator():
                if proxy.letter == "M":
                    # Keep Move element as is
                    result += [inkex.paths.Move(*proxy.args)]
                else:
                    # For other elements, form tabs along the line between start and finish
                    edge, slots = steps(proxy.previous_end_point, proxy.end_point, self.options, transform, self.svg)
                    result += edge
                    # Add optional slot group
                    if self.options.slots:
                        self.svg.add(slots)
            node.path = result

if __name__ == '__main__':
    TabSlot().run()

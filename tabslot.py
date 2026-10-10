
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
    match options.phantom:                                            # phantom vectors
        case 'none':
            start_phantom, finish_phantom = 0*unit, 0*unit
        case 'both':
            start_phantom, finish_phantom = material*unit, material*unit
        case 'start':
            start_phantom, finish_phantom = material*unit, 0*unit
        case 'finish':
            start_phantom, finish_phantom = 0*unit, material*unit
    phantom = start_phantom + finish_phantom

    kerf = kerf_norm * unit                                           # kerf correction in direction of edge
    step = (full + phantom - kerf) / (1 + 2*options.count)            # final edge length of each step
    notch = inkex.transforms.Vector2d(-full.y, full.x)                # perpendicular
    notch = material * notch / abs(notch)                             # perpendicular equal to material thickness
    notch = notch if options.normal == 'positive' else -notch

    match options.operation:
        case 'tab':
            plan = create_plan([     step - start_phantom       ], options.count - 1, [-notch, 's', step + kerf, notch, step - kerf], [-notch, 's', step + kerf, notch, step - finish_phantom       ])
        case 'slot':
            plan = create_plan(['x', step - start_phantom + kerf], options.count - 1, [notch, step - kerf, -notch, 's', step + kerf], [notch, step - kerf, -notch, 's', step - finish_phantom + kerf])

    mark = 0 * unit
    for move in plan:
        match move:
            case str(mode):
                base = src + mark - 1.625 * notch + kerf - (start_phantom if mode == 'x' else 0 * start_phantom)
                slot = slot_path(base, step - kerf, notch * (1 - kerf_norm/abs(notch)))
                slot.transform = transform
                slots.add(slot)
            case move:
                mark = move + mark
                result += [vec_to_line(mark)]
    return result, slots

def join(nodes, svg):
    # Collect every selected path in document coordinates
    pieces = [node.path.to_absolute().transform(node.composed_transform()) for node in nodes]
    tolerance = svg.to_dimensionless('0.01mm')
    near = lambda a, b: abs(a - b) < tolerance
    first = lambda p: inkex.transforms.Vector2d(*p[0].args[-2:])
    last = lambda p: list(p.end_points)[-1]
    is_closed = lambda p: p[-1].letter in 'Zz' or near(first(p), last(p))

    closed = [p for p in pieces if is_closed(p)]
    open_ = [p for p in pieces if not is_closed(p)]

    # Chain open pieces end-to-start (reversing when needed) into closed loops
    loops = []
    while open_:
        loop = open_.pop(0)
        while not near(first(loop), last(loop)):
            for i, piece in enumerate(open_):
                if near(last(loop), first(piece)):
                    break
                if near(last(loop), last(piece)):
                    piece = piece.reverse()
                    break
            else:
                break                                                 # dead end - leave loop open
            open_.pop(i)
            loop = inkex.paths.Path(list(loop) + list(piece)[1:])     # drop the joining Move
        loops.append(loop)

    # Combine outer loops and inner shapes into one path; evenodd fills the area between them
    combined = inkex.paths.Path()
    for loop in loops + closed:
        if loop[-1].letter not in 'Zz':
            loop.append(inkex.paths.ZoneClose())
        combined += loop

    target = nodes[0]
    element = inkex.PathElement()
    element.style = target.style
    element.style['fill-rule'] = 'evenodd'
    element.path = combined.transform(-target.getparent().composed_transform())
    target.addprevious(element)
    for node in nodes:
        node.delete()
    return element

SHAPES = (inkex.PathElement, inkex.Rectangle, inkex.Circle, inkex.Ellipse, inkex.Polygon, inkex.Polyline, inkex.Line)

def split(node):
    # Replace a shape with one open path per side, so each side can get its own tab/slot plan
    path = node.path.to_absolute().to_non_shorthand()
    sides = []
    for proxy in path.proxy_iterator():
        if proxy.letter == 'M':
            continue
        if proxy.letter == 'Z':
            if abs(proxy.end_point - proxy.previous_end_point) < 1e-9:
                continue                                              # closing segment has no length
            command = inkex.paths.Line(*proxy.end_point)
        else:
            command = proxy.command
        side = inkex.PathElement()
        side.path = inkex.paths.Path([inkex.paths.Move(*proxy.previous_end_point), command])
        side.style = node.style
        side.transform = node.transform
        node.addprevious(side)
        side.set_random_id("side")
        sides.append(side)
    node.delete()
    return sides

class TabSlot(inkex.EffectExtension):
    def add_arguments(self, options):
        options.add_argument('--tab', type=str, default='edge', help='notebook page: edge or shape')
        options.add_argument('-a', '--action', type=str, default='split', help='shape action: split or join')
        options.add_argument('-m', '--material', type=float, default=3.0, help='material thickness in mm')
        options.add_argument('-k', '--kerf', type=float, default=160, help='laser kerf in µm')
        options.add_argument('-n', '--count', type=int, default=2, help='number of steps to take along path')
        options.add_argument('-t', '--normal', type=str, default='positive', help='normal vector direction')
        options.add_argument('-o', '--operation', type=str, default='slot', help='cut tabs or slots')
        options.add_argument('-s', '--slots', type=inkex.Boolean, default=False, help='add matching slots')
        options.add_argument('-p', '--phantom', type=str, default='none', help='add phantom material at ends')

    def effect(self):
        # Older Inkscape versions pass the notebook page name wrapped in quotes
        page = self.options.tab.strip('"')
        if page == 'shape':
            nodes = list(self.svg.selection.filter(*SHAPES).values())
            if not nodes:
                raise inkex.AbortExtension('Split/Join: select a rectangle or path first.')
            if self.options.action == 'split':
                for node in nodes:
                    split(node)
            else:
                join(nodes, self.svg)
            return
        # Iterate over the selected paths
        if not self.svg.selection.filter(inkex.PathElement):
            raise inkex.AbortExtension('Tabs & Slots: select a side to add tabs or slots to. To split a rectangle into sides, switch to the Split/Join tab.')
        for node in self.svg.selection.filter(inkex.PathElement):
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

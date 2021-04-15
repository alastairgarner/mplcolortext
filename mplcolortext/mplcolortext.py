
import re
import numpy as np
from collections import namedtuple

from matplotlib.text import Text, _wrap_text
from matplotlib.transforms import Affine2D, Bbox

Chunk = namedtuple('Chunk', 'string x y fontargs gcargs')

class TextMultiColor(Text):
    
    def __init__(self, *args, highlight={}, flag='[:]', **kwargs):
        super().__init__(*args, **kwargs)
        
        self._flag = flag
        self._highlight = highlight
        self._chunks = []
        
    def _get_layout(self, renderer):
        """
        Return the extent (bbox) of the text together with
        multiple-alignment information. Note that it returns an extent
        of a rotated text when necessary.
        """
        key = self.get_prop_tup(renderer=renderer)
        if key in self._cached:
            return self._cached[key]

        thisx, thisy = 0.0, 0.0
        lines = self.get_text().split("\n")  # Ensures lines is not empty.
        
        # AG >>>>>>>>>>>
        chunks = self._string_to_chunks(self.get_text(), self._flag, renderer)
        self._chunks = chunks                                                       # TODO maybe move this in __init__()
        lines = [chunk.string for chunk in chunks]
        # <<<<<<<<<<<<<<

        ws = []
        hs = []
        xs = []
        ys = []

        # Full vertical extent of font, including ascenders and descenders:
        _, lp_h, lp_d = renderer.get_text_width_height_descent(
            "lp", self._fontproperties,
            ismath="TeX" if self.get_usetex() else False)
        min_dy = (lp_h - lp_d) * self._linespacing
        
        pixels_per_pt = 1/72*self.figure._dpi
        line_height = (pixels_per_pt * self.get_fontsize()) * self._linespacing

        cws = [0]
        ln = 0
        lns = []
        for i, chunk in enumerate(chunks):        # |AG

            clean_line, ismath = self._preprocess_math(chunk.string)
            fontproperties = self._get_chunk_fontproperties(chunk.fontargs)
            if clean_line:
                w, h, d = renderer.get_text_width_height_descent(
                    clean_line, fontproperties, ismath=ismath)
            else:
                w = h = d = 0

            # For multiline text, increase the line spacing when the text
            # net-height (excluding baseline) is larger than that of a "l"
            # (e.g., use of superscripts), which seems what TeX does.
            h = max(h, lp_h)
            d = max(d, lp_d)
            
            ws.append(w)
            hs.append(h)
            
            if (i != 0) & (chunk.x == 0):
                ln += 1
                cws.append(0)
                
            cws[ln] += w
            lns.append(ln)

            # Metrics of the last line that are needed later:
            baseline = (h - d) - thisy

            if i == 0:
                # position at baseline
                thisy = -(h - d)
            elif not chunk.y:      # |AG
                thisy += d      # |
            else:
                # put baseline a good distance from bottom of previous line
                # thisy -= max(min_dy, (h - d) * self._linespacing)
                # AG edit - define change in y independent of font dimensions
                thisy -= line_height - d # reduce by d, because d is minus'd 3 lines later anyway

            thisx = chunk.x        # AG
            
            xs.append(thisx)  # == 0.
            ys.append(thisy)

            thisy -= d

        ws = [cws[ln] for ln in lns]

        # Metrics of the last line that are needed later:
        descent = d

        # Bounding box definition:
        width = max(ws)
        xmin = 0
        xmax = width
        ymax = 0
        ymin = ys[-1] - descent  # baseline of last line minus its descent
        height = ymax - ymin

        # get the rotation matrix
        M = Affine2D().rotate_deg(self.get_rotation())

        # now offset the individual text lines within the box
        malign = self._get_multialignment()
        if malign == 'left':
            offset_layout = [(x, y) for x, y in zip(xs, ys)]
        elif malign == 'center':
            offset_layout = [(x + width / 2 - w / 2, y)
                            for x, y, w in zip(xs, ys, ws)]
        elif malign == 'right':
            offset_layout = [(x + width - w, y)
                            for x, y, w in zip(xs, ys, ws)]

        # the corners of the unrotated bounding box
        corners_horiz = np.array(
            [(xmin, ymin), (xmin, ymax), (xmax, ymax), (xmax, ymin)])

        # now rotate the bbox
        corners_rotated = M.transform(corners_horiz)
        # compute the bounds of the rotated box
        xmin = corners_rotated[:, 0].min()
        xmax = corners_rotated[:, 0].max()
        ymin = corners_rotated[:, 1].min()
        ymax = corners_rotated[:, 1].max()
        width = xmax - xmin
        height = ymax - ymin

        # Now move the box to the target position offset the display
        # bbox by alignment
        halign = self._horizontalalignment
        valign = self._verticalalignment

        rotation_mode = self.get_rotation_mode()
        if rotation_mode != "anchor":
            # compute the text location in display coords and the offsets
            # necessary to align the bbox with that location
            if halign == 'center':
                offsetx = (xmin + xmax) / 2
            elif halign == 'right':
                offsetx = xmax
            else:
                offsetx = xmin

            if valign == 'center':
                offsety = (ymin + ymax) / 2
            elif valign == 'top':
                offsety = ymax
            elif valign == 'baseline':
                offsety = ymin + descent
            elif valign == 'center_baseline':
                offsety = ymin + height - baseline / 2.0
            else:
                offsety = ymin
        else:
            xmin1, ymin1 = corners_horiz[0]
            xmax1, ymax1 = corners_horiz[2]

            if halign == 'center':
                offsetx = (xmin1 + xmax1) / 2.0
            elif halign == 'right':
                offsetx = xmax1
            else:
                offsetx = xmin1

            if valign == 'center':
                offsety = (ymin1 + ymax1) / 2.0
            elif valign == 'top':
                offsety = ymax1
            elif valign == 'baseline':
                offsety = ymax1 - baseline
            elif valign == 'center_baseline':
                offsety = ymax1 - baseline / 2.0
            else:
                offsety = ymin1

            offsetx, offsety = M.transform((offsetx, offsety))

        xmin -= offsetx
        ymin -= offsety

        bbox = Bbox.from_bounds(xmin, ymin, width, height)

        # now rotate the positions around the first (x, y) position
        xys = M.transform(offset_layout) - (offsetx, offsety)

        ret = bbox, list(zip(lines, zip(ws, hs), *xys.T)), descent
        self._cached[key] = ret
        return ret
    
    def draw(self, renderer):
        # docstring inherited

        if renderer is not None:
            self._renderer = renderer
        if not self.get_visible():
            return
        if self.get_text() == '':
            return

        renderer.open_group('text', self.get_gid())

        with _wrap_text(self) as textobj:
            bbox, info, descent = textobj._get_layout(renderer)
            trans = textobj.get_transform()

            # don't use textobj.get_position here, which refers to text
            # position in Text:
            posx = float(textobj.convert_xunits(textobj._x))
            posy = float(textobj.convert_yunits(textobj._y))
            posx, posy = trans.transform((posx, posy))
            if not np.isfinite(posx) or not np.isfinite(posy):
                # _log.warning("posx and posy should be finite values")
                return
            canvasw, canvash = renderer.get_canvas_width_height()

            # Update the location and size of the bbox
            # (`.patches.FancyBboxPatch`), and draw it.
            if textobj._bbox_patch:
                self.update_bbox_position_size(renderer)
                self._bbox_patch.draw(renderer)

            angle = textobj.get_rotation()
            
            i = 0
            colors = ["black", "red", "blue", "green", "magenta"]
            for line, wh, x, y in info:
                
                fontproperties = textobj._get_chunk_fontproperties(self._chunks[i].fontargs)
                
                gc = renderer.new_gc()
                self._update_gcproperties(gc, self._chunks[i].gcargs)
                
                if i == 0:
                    textobj._set_gc_clip(gc)
                i += 1

                mtext = textobj if len(info) == 1 else None
                x = x + posx
                y = y + posy
                if renderer.flipy():
                    y = canvash - y
                clean_line, ismath = textobj._preprocess_math(line)

                if textobj.get_path_effects():
                    from matplotlib.patheffects import PathEffectRenderer
                    textrenderer = PathEffectRenderer(
                        textobj.get_path_effects(), renderer)
                else:
                    textrenderer = renderer
                
                if textobj.get_usetex():
                    textrenderer.draw_tex(gc, x, y, clean_line,
                                          fontproperties, angle,
                                          mtext=mtext)
                else:
                    textrenderer.draw_text(gc, x, y, clean_line,
                                           fontproperties, angle,
                                           ismath=ismath, mtext=mtext)
                gc.restore()
        
        renderer.close_group('text')
        self.stale = False
        
    def _parse_text_args(self, **kwargs):
        """docstring"""
        
        gc_args = ["color", "alpha", "url"]
        fp_args = ["family", "style", "variant", "weight", "stretch", "size", "fname", "math_fontfamily"]
        
        gcproperties = {}
        fontproperties = {}
        
        if kwargs is not None:
            for arg,val in kwargs.items():
                if arg in gc_args:
                    gcproperties.update({arg: val})

                if arg in fp_args:
                    fontproperties.update({arg: val})
                                
        return fontproperties, gcproperties
    
    def _update_gcproperties(self, gc, properties=None):
        
        update = {        
            "color": gc.set_foreground,
            "alpha": gc.set_alpha,
            "url": gc.set_url,
        }

        if properties is None:
            return

        for prop,value in properties.items():
            if prop in update.keys():
                update[prop](value)
                
    def _get_chunk_fontproperties(self, properties=None):
        """
        dosctring
        """
        fp = self._fontproperties.copy()
        
        update = {        
            "family": fp.set_family,
            "style": fp.set_style,
            "variant": fp.set_variant,
            "weight": fp.set_weight,
            "stretch": fp.set_stretch, 
            "size": fp.set_size, 
            "fname": fp.set_file, 
            # "math_fontfamily": fp.set_math_fontfamily, ## TODO work out why this doesn't work
        }
        
        if properties is None:
            return fp

        for prop,value in properties.items():
            if prop in update.keys():
                update[prop](value)
                
        return fp

    def _string_to_chunks(self, string, flag, renderer):
        """
        docstring
        """
        opn,sep,clo = flag

        expr = f"([\{opn}].*?[\{clo}])"
        parts = re.split(expr, string)

        expr = f"[\{opn}](.*?)[\{sep}](.*?)[\{clo}]"
        chunks = []
        offsetx = 0.0
        for part in parts:
            offsety = False
            p = re.match(expr,part)    
            
            hl = {}
            fontargs = {}
            if p:
                part,fmt = p.groups()
                fmt = int(fmt)
                
                if fmt in self._highlight.keys():
                    hl = self._highlight[fmt]
            
            fontargs,gcargs = self._parse_text_args(**hl)
            fontproperties = self._get_chunk_fontproperties(fontargs)
            
            phrase = part.split('\n')
            for i,row in enumerate(phrase):
                w,h,d = renderer.get_text_width_height_descent(
                            row, prop=fontproperties, ismath=False
                        )
                
                if i != 0:
                    offsetx = 0.0
                    offsety = True 
                    
                chunk = Chunk(row, offsetx, offsety, fontargs, gcargs)
                chunks.append(chunk)
                
            offsetx += w
        
        return chunks

    
    
def multicolor_text(x=None, y=None, string=None, flag='[:]', highlight={}, linespacing=1.2, parent=None, system=None, anchor='bl', **kwargs):
    """
    Docstring
    """
        
    text = TextMultiColor(
        x, y, string,
        flag=flag, highlight=highlight, linespacing=linespacing, 
        parent=parent, system=system, anchor=anchor, **kwargs
    )
    
    return text.draw()
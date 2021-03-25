
import re

from matplotlib.axes import Axes
from matplotlib.figure import  Figure
from matplotlib.text import Text
from matplotlib.offsetbox import AnchoredOffsetbox, TextArea, HPacker

from mpltransform import transform_factory

class TextMultiColor(object):
    """
    docstring
    """
    
    def __init__(self, x=None, y=None, string=None, flag='[:]', highlight={}, linespacing=1.2, parent=None, system=None, anchor=None, **kwargs):
        
        self.parent = parent
        if isinstance(parent, Axes):
            self.figure = parent.figure
            self.transform = parent.transAxes
        elif isinstance(parent, Figure):
            self.figure = parent
            self.transform = parent.transFigure
        else:
            raise Exception('Object passed must be a Figure or Axes instance')
        
        self.string = string
        assert isinstance(flag,str) & (len(flag) == 3)
        self.flag = flag
        
        self.x = x
        self.y = y
        
        self.linespacing = linespacing
        self.base = kwargs
        self.highlight = highlight
        
        self.transform = self._generate_transform(system, anchor)

        self.renderer = self.figure.canvas.get_renderer()
        self.boxes = None
        self.children = None
        
        self._generate_lines()

    def _generate_transform(self, system=None, anchor='bl'):
        """docstring"""
        
        if system is not None:
            self.transform = transform_factory(self.parent, system=system, anchor=anchor)
            
        return self.transform
    
    def _get_default_fontproperties(self):
        """docstring"""
        
        default_text = Text(0,0,'', **self.base)
        fp = default_text._fontproperties
        del(default_text)
        
        return fp

    def _generate_lines(self):
        """
        docstring
        """
        opn,sep,clo = self.flag

        expr = f"([\{opn}].*?[\{clo}])"
        parts = re.split(expr, self.string)

        expr = f"[\{opn}](.*?)[\{sep}](.*?)[\{clo}]"
        lines = [[]]
        n = 0
        for part in parts:
            opts = self.base.copy()
            
            p = re.match(expr,part)
            if p:
                part,fmt = p.groups()
                fmt = int(fmt)
                opts.update(self.highlight[fmt])
                
            rows = part.split('\n')
            for i,row in enumerate(rows):
                if i != 0:
                    lines.append([])
                    n += 1
                
                txt = TextArea(row, textprops=opts)
                lines[n].append(txt)
                
        boxes  = []
        for line in lines:
            box = HPacker(children=line, align="baseline", pad=0, sep=0)
            boxes.append(box)
            
        self.boxes = boxes
        return boxes
    
    def _get_xy_px(self,x,y):
        
        # Get default font properties and text descent, in px
        fp = self._get_default_fontproperties()
        _,_,descent = self.renderer.get_text_width_height_descent("lp", fp, ismath=False)

        # Determine the x,y position in display coordinates
        xy_px = self.transform.transform([x, y]) - [0, descent]
    
        return xy_px
    
    def _get_y_increment(self):
        
        fp = self._get_default_fontproperties()

        # determine line increment, in px
        dpi = self.figure._dpi
        fs = fp.get_size()
        return (fs*self.linespacing) * (dpi/72)
    
    def _get_line_max_extent(self):

        fp = self._get_default_fontproperties()
        
        width = height = descent = 0
        for line in self.string.split('\n'):
            w,h,d = self.renderer.get_text_width_height_descent(line, fp, ismath=False)
            
            width = max(width,w)
            height = max(height,h)
            descent = max(descent,d)
        
        return width,height,descent
    
    def draw(self, x=None, y=None):
        """
        Docstring
        """
        # https://stackoverflow.com/questions/33159134/matplotlib-y-axis-label-with-multiple-colors
        
        if x is None:
            x = self.x
        if y is None:
            y = self.y
        if (x is None) and (y is None):
            raise Exception('No x,y arguments passed!')
        
        xy_px = self._get_xy_px(x,y)
        y_incr_px = self._get_y_increment()
        boxes = self.boxes

        for box in boxes[::-1]:
            x,y = self.transform.inverted().transform(xy_px)
            anchored_xbox = AnchoredOffsetbox(loc=3, child=box, pad=0, frameon=False,
                                        bbox_to_anchor=(x,y), bbox_transform=self.transform, borderpad=0)
            self.parent.add_artist(anchored_xbox)
            xy_px[1] += y_incr_px
            
        self.children = [textarea.get_children() for box in boxes for textarea in box.get_children()]
        
        return self.children
    
    
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
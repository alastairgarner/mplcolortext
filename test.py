# TODO If the text overlaps perfectly, the colors don't render correctly

import matplotlib.pyplot as plt
from mplcolortext import TextMultiColor

from collections import namedtuple

Chunk = namedtuple('Chunk', 'text x y format')
chunk = Chunk('this is a string', 25, True, dict(color='red'))

import re

def _parse_multicolor_string(self, string, flag, renderer):
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
                hl = self._highlight[fmt]
                fontargs,_ = self._parse_text_args(**hl)
            
            fontproperties = self._get_updated_fontproperties(fontargs)
            
            phrase = part.split('\n')
            for i,row in enumerate(phrase):
                w,h,d = renderer.get_text_width_height_descent(
                            row, prop=fontproperties, ismath=False
                        )
                
                if i != 0:
                    offsetx = 0.0
                    offsety = True 
                    
                chunk = Chunk(row, offsetx, offsety, hl)
                chunks.append(chunk)
                
            offsetx += w
        
        return chunks

TextMultiColor._parse_multicolor_string = _parse_multicolor_string

fig = plt.figure()
ax = fig.add_subplot()

string = "This is a string with [multi:1]\n-[coloured:2] text"
highlight = {
  1: dict(weight='bold', color="red"),
  2: dict(style='italic', color='blue', size=24)
}

# txt1 = Text(0.1, 0.5, string)
# ax._add_text(txt1)

txt2 = TextMultiColor(0.5, 0.5, string, highlight=highlight, rotation=45)
ax._add_text(txt2)


# plt.savefig("./test/testfig.png", dpi=450)

plt.show()
plt.close()
"""GI type 0 <-> editable RGB/RGBA PNG, with explicit header metadata.

RGB565 is expanded by Pillow's BGR;16 reader and rebuilt from the upper 5/6/5
bits of the PNG channels. ARGB8888 is stored losslessly as RGBA, including RGB
values of fully transparent pixels. No original GI blob is used as input.
"""
from pathlib import Path
from array import array
import os, struct, sys, tempfile
from PIL import Image

def export(data, png_path):
    assert len(data)>=96 and data[:4]==b'gi\0\0'
    h=struct.unpack_from('<15I',data,4)
    assert h[9:11]==(0,1), 'Only single-layer GI type 0 is supported'
    offset,size,*layer=struct.unpack_from('<8I',data,64)
    width,height=layer[2]-layer[0],layer[3]-layer[1]
    assert offset==96 and size==len(data)-96
    masks=list(h[5:9])
    if masks==[0xf800,0x7e0,0x1f,0]:
        kind='rgb565';mode='RGB';raw_mode='BGR;16';stride=2
    elif masks==[0xff0000,0xff00,0xff,0xff000000]:
        kind='argb8888';mode='RGBA';raw_mode='BGRA';stride=4
    else:raise ValueError('Unsupported channel masks')
    assert size==width*height*stride
    image=Image.frombytes(mode,(width,height),data[96:],'raw',raw_mode)
    png_path=Path(png_path);png_path.parent.mkdir(parents=True,exist_ok=True)
    # Publish only a complete PNG, so readers cannot see an unfinished export.
    descriptor,temporary=tempfile.mkstemp(prefix='gi-export-',suffix='.png',dir=png_path.parent)
    os.close(descriptor)
    try:
        image.save(temporary,format='PNG',compress_level=9)
        with Image.open(temporary) as check:check.load()
        os.replace(temporary,png_path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {'format':'srhd-gi0-png-v1','version':h[0],'bounds':list(h[1:5]),
            'masks':masks,'reserved':list(h[11:15]),'pixel_format':kind,
            'layer_bounds':layer[:4],'layer_reserved':layer[4:]}

def encode(source,png_path):
    assert source['format']=='srhd-gi0-png-v1'
    bounds=source['layer_bounds'];width,height=bounds[2]-bounds[0],bounds[3]-bounds[1]
    with Image.open(png_path) as image:
        assert image.size==(width,height), 'PNG dimensions differ from layer bounds'
        kind=source['pixel_format']
        if kind=='rgb565':
            assert source['masks']==[0xf800,0x7e0,0x1f,0]
            assert image.mode=='RGB', 'RGB565 source PNG must use RGB mode'
            raw=image.tobytes()
            pixels=array('H', (((r>>3)<<11)|((g>>2)<<5)|(b>>3)
                         for r,g,b in zip(raw[0::3],raw[1::3],raw[2::3])))
            if sys.byteorder!='little':pixels.byteswap()
            payload=pixels.tobytes()
        elif kind=='argb8888':
            assert source['masks']==[0xff0000,0xff00,0xff,0xff000000]
            assert image.mode=='RGBA', 'ARGB8888 source PNG must use RGBA mode'
            payload=image.tobytes('raw','BGRA')
        else:raise ValueError('Unsupported pixel format')
    header=struct.pack('<4s15I',b'gi\0\0',source['version'],*source['bounds'],*source['masks'],0,1,*source['reserved'])
    descriptor=struct.pack('<8I',96,len(payload),*bounds,*source['layer_reserved'])
    return header+descriptor+payload

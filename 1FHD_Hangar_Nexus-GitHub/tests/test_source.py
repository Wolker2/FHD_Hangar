from pathlib import Path
import copy, hashlib, json, shutil, struct, subprocess, sys, tempfile, unittest, zipfile
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build import compile_source, compile_configs, resource_audit, load, INSTALL_PREFIX
from gi_png import export, encode

class SourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files,cls.configs=compile_source()
        cls.variants=load(ROOT/'source/variants.json')['variants']

    def test_all_original_hashes_and_resource_references(self):
        self.assertEqual({name:hashlib.sha256(data).hexdigest() for name,data in self.files.items()},load(ROOT/'original-file-sha256.json'))
        self.assertEqual(len(self.files),24)
        audit=resource_audit(self.files,self.configs)
        self.assertEqual(audit['cache_references_checked'],12);self.assertEqual(audit['missing'],[])

    def test_shared_config_only_changes_three_sizes(self):
        base=load(ROOT/'source/CFG/Main.json')
        def differences(a,b):
            if isinstance(a,dict):return sum(differences(a[key],b[key]) for key in a)
            if isinstance(a,list):
                self.assertEqual(len(a),len(b));return sum(differences(x,y) for x,y in zip(a,b))
            return int(a!=b)
        for variant in self.variants:
            tree=self.configs[variant['name']]['CFG/Main.dat']
            self.assertEqual(differences(base,tree),0 if variant['name']=='FHD_HangarHD' else 3)
            self.assertEqual([e['name'] for e in tree['root']['entries'][0]['value']['entries']],['EquipmentShop','GoodsShop','Hangar'])
            metadata=self.files[variant['name']+'/ModuleInfo.txt']
            self.assertEqual(metadata.startswith(b'\xff\xfe'),variant['module_encoding']=='utf-16le-bom')

    def test_every_rgb565_color_roundtrips_through_png(self):
        # Exhaust the complete color space, rather than testing a matching formula.
        source=copy.deepcopy(next(v for v in self.variants if v['name']=='FHD_HangarHD')['graphics'][0])
        source['bounds']=source['layer_bounds']=[0,0,256,256]
        samples=struct.pack('<65536H',*range(65536))
        header=struct.pack('<4s15I',b'gi\0\0',source['version'],*source['bounds'],*source['masks'],0,1,*source['reserved'])
        descriptor=struct.pack('<8I',96,len(samples),*source['layer_bounds'],*source['layer_reserved'])
        original=header+descriptor+samples
        with tempfile.TemporaryDirectory() as folder:
            png=Path(folder)/'colors.png';decoded=export(original,png)
            self.assertEqual(encode(decoded,png),original)
            with Image.open(png) as image:
                image.load();image.putpixel((0,0),(255,0,0));image.save(png)
            edited=encode(decoded,png)
            self.assertEqual(struct.unpack_from('<H',edited,96)[0],0xf800)
            self.assertNotEqual(edited,original)

    def test_argb8888_preserves_transparent_rgb_and_edits(self):
        source=copy.deepcopy(next(v for v in self.variants if v['name']=='FHD_HangarFHD')['graphics'][1])
        self.assertEqual(source['pixel_format'],'argb8888')
        source['bounds']=source['layer_bounds']=[0,0,2,2]
        colors=[(10,20,30,0),(40,50,60,1),(70,80,90,128),(100,110,120,255)]
        with tempfile.TemporaryDirectory() as folder:
            png=Path(folder)/'alpha.png';image=Image.new('RGBA',(2,2));image.putdata(colors);image.save(png)
            data=encode(source,png)
            self.assertEqual(data[96:],bytes(value for r,g,b,a in colors for value in [b,g,r,a]))
            restored=Path(folder)/'restored.png';metadata=export(data,restored)
            with Image.open(restored) as result:self.assertEqual(list(result.getdata()),colors)
            self.assertEqual(encode(metadata,restored),data)
            image.putpixel((0,0),(1,2,3,4));image.save(png)
            self.assertNotEqual(encode(source,png),data)

    def test_isolated_source_only_build(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)
            for name in ['source','scripts']:
                shutil.copytree(ROOT/name,target/name,ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copy2(ROOT/'original-file-sha256.json',target/'original-file-sha256.json')
            self.assertFalse(any(p.suffix.lower() in ['.dat','.gi','.dll','.exe','.scr'] for p in target.rglob('*') if p.is_file()))
            result=subprocess.run([sys.executable,str(target/'scripts/build.py'),'--strict-original'],cwd=target,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
            restored={}
            for variant in self.variants:
                with zipfile.ZipFile(target/'dist'/(variant['name']+'_FROM_SOURCE.zip')) as archive:
                    self.assertIsNone(archive.testzip());self.assertEqual(len(archive.namelist()),6)
                    for name in archive.namelist():restored[name[len(INSTALL_PREFIX):]]=hashlib.sha256(archive.read(name)).hexdigest()
            self.assertEqual(restored,load(ROOT/'original-file-sha256.json'))
if __name__=='__main__':unittest.main()

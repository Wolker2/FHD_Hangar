#!/usr/bin/env python3
"""Build all four Hangar variants from shared configuration and PNG sources."""
from pathlib import Path
import argparse, copy, hashlib, json, platform, sys, zipfile, zlib
from PIL import __version__ as pillow_version
from dat_codec import encode as encode_dat, decode as decode_dat
from gi_png import encode as encode_gi

ROOT=Path(__file__).resolve().parents[1]
INSTALL_PREFIX='Mods/FHD_MODS/'
BACKGROUND_NAMES={'EquipmentBackground','MarketBackground','HangarBackground'}
def load(path):return json.loads(Path(path).read_text('utf-8'))
def sha(data):return hashlib.sha256(data).hexdigest()
def walk(block,path=''):
    for entry in block['entries']:
        name=path+'.'+entry['name'] if path else entry['name']
        if entry['kind']=='block':yield from walk(entry['value'],name)
        else:yield name,entry['value']

def compile_configs(root,variant):
    source=root/'source';main=copy.deepcopy(load(source/'CFG/Main.json'));patched=[]
    def resize(block):
        parameters={entry['name']:entry for entry in block['entries'] if entry['kind']=='parameter'}
        name=parameters.get('Name',{}).get('value')
        if name in BACKGROUND_NAMES:
            assert parameters['Image']['value'].startswith('GI,Bm.FormHangar2.')
            parameters['Size']['value']=','.join(str(x) for x in variant['background_ui_size'])
            patched.append(name)
        for entry in block['entries']:
            if entry['kind']=='block':resize(entry['value'])
    resize(main['root']);assert set(patched)==BACKGROUND_NAMES and len(patched)==3
    def expand(obj):
        if isinstance(obj,dict):return {key:expand(value) for key,value in obj.items()}
        if isinstance(obj,list):return [expand(value) for value in obj]
        if isinstance(obj,str):return obj.replace('{variant}',variant['name'])
        return obj
    configs={'CFG/Main.dat':main,'CFG/CacheData.dat':expand(load(source/'CFG/CacheData.json'))}
    files={}
    for name,tree in configs.items():
        data=encode_dat(tree)
        assert decode_dat(data,tree['format'])==tree, 'DAT roundtrip failed: '+name
        files[name]=data
    metadata=(source/variant['name']/'ModuleInfo.txt').read_bytes().decode('utf-8')
    encoding=variant['module_encoding']
    if encoding=='utf-16le-bom':files['ModuleInfo.txt']=b'\xff\xfe'+metadata.encode('utf-16le')
    elif encoding=='cp1251':files['ModuleInfo.txt']=metadata.encode('cp1251')
    else:raise ValueError('Unsupported ModuleInfo encoding')
    return files,configs

def compile_source(root=ROOT,only=None):
    files={};all_configs={};variants=load(root/'source/variants.json')['variants']
    for variant in variants:
        if only is not None and variant['name']!=only:continue
        compiled,configs=compile_configs(root,variant)
        for graphic in variant['graphics']:
            png=(root/'source'/graphic['png']).resolve()
            assert png.is_relative_to((root/'source').resolve())
            compiled[graphic['runtime_path']]=encode_gi(graphic,png)
        files.update({variant['name']+'/'+name:data for name,data in compiled.items()})
        all_configs[variant['name']]=configs
    assert files, 'No matching variant'
    return files,all_configs

def resource_audit(files,configs):
    references=[];external=set()
    for variant,trees in configs.items():
        for alias,value in walk(trees['CFG/CacheData.dat']['root']):
            path=value.replace('\\','/')
            if path.startswith(INSTALL_PREFIX):
                references.append({'variant':variant,'alias':alias,'present':path[len(INSTALL_PREFIX):] in files})
        # Other FormHangar2 resources, fonts, sounds and styles come from the game.
        import re
        own={alias for alias,_ in walk(trees['CFG/CacheData.dat']['root'])}
        for _,value in walk(trees['CFG/Main.dat']['root']):
            for alias in re.findall(r'\bBm\.[\w.]+',value):
                if alias not in own:external.add(alias)
    return {'cache_references_checked':len(references),'missing':[r for r in references if not r['present']],
            'external_game_image_aliases':sorted(external)}

def main():
    variants=load(ROOT/'source/variants.json')['variants']
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--strict-original',action='store_true')
    parser.add_argument('--variant',choices=['all']+[v['name'] for v in variants],default='all')
    args=parser.parse_args();only=None if args.variant=='all' else args.variant
    files,configs=compile_source(only=only);expected=load(ROOT/'original-file-sha256.json')
    if only:expected={name:digest for name,digest in expected.items() if name.startswith(only+'/')}
    if set(files)!=set(expected):raise SystemExit('Runtime file list differs from upload')
    hashes={name:sha(data) for name,data in sorted(files.items())}
    changed=[name for name in hashes if hashes[name]!=expected[name]]
    if args.strict_original and changed:raise SystemExit('Original SHA-256 mismatch: '+repr(changed))
    audit=resource_audit(files,configs)
    if audit['missing']:raise SystemExit('Referenced resources missing: '+repr(audit['missing']))
    out=ROOT/'dist';out.mkdir(exist_ok=True);packages={}
    for variant in configs:
        archive=out/(variant+'_FROM_SOURCE.zip')
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for name,data in sorted(files.items()):
                if name.startswith(variant+'/'):
                    info=zipfile.ZipInfo(INSTALL_PREFIX+name,date_time=(2026,10,28,0,0,0));info.external_attr=0o644<<16
                    z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
        with zipfile.ZipFile(archive) as z:assert z.testzip() is None
        packages[archive.name]=sha(archive.read_bytes())
    report={'runtime_files':len(files),'variants':list(configs),'byte_identical_to_upload':not changed,
            'different_files':changed,'prebuilt_runtime_inputs_used':False,'game_required_for_build':False,
            'dat_files':2*len(configs),'gi_files':3*len(configs),'module_files':len(configs),'dll_files':0,'scr_files':0,
            'resource_audit':audit,'sha256':hashes,'package_sha256':packages,
            'python':platform.python_version(),'zlib':zlib.ZLIB_RUNTIME_VERSION,'pillow':pillow_version,
            'game_executed':False}
    (out/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'PASS: {len(files)} runtime files built; {len(files)-len(changed)} original hashes match')
    print('Variants:',', '.join(configs))
    print('CacheData:',audit['cache_references_checked'],'local references; missing:',len(audit['missing']))
    print('Installable ZIPs:',', '.join(packages))
if __name__=='__main__':main()

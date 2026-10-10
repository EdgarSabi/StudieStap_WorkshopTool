import nbformat, json, sys
from html.parser import HTMLParser
class P(HTMLParser):
    def __init__(s): super().__init__(); s.tables=[]; s.cur=None; s.row=None; s.cell=None
    def handle_starttag(s,t,a):
        if t=='table': s.cur=[]; 
        elif t=='tr': s.row=[]
        elif t in('td','th'): s.cell=''
    def handle_endtag(s,t):
        if t in('td','th'): s.row.append(s.cell); s.cell=None
        elif t=='tr': s.cur.append(s.row); s.row=None
        elif t=='table': s.tables.append(s.cur); s.cur=None
    def handle_data(s,d):
        if s.cell is not None: s.cell+=d
def frame(html):
    p=P(); p.feed(html); t=p.tables[-1]
    hdr=t[0]; rows=t[1:]
    return [dict(zip(['idx']+hdr[1:],r)) for r in rows]
out={}
base='C:/Users/School/Projects/StudieStap_WorkshopTool/Data-analysis/Notebooks/'
for f,idx,names in [('03-transcription-evaluation.ipynb',[14,21,28],['testaudio1','testaudio2','testaudio5']),('05-fixing-diarization-problems.ipynb',[2,6,14],['testaudio6_before','testaudio6_after','testaudio7'])]:
    nb=nbformat.read(base+f,as_version=4)
    for i,n in zip(idx,names):
        for o in nb.cells[i].outputs:
            if o.output_type=='execute_result':
                out[n]=frame(o['data']['text/html'])
json.dump(out,open(sys.argv[1]+'/nb_hyp.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
for k,v in out.items(): print(k,len(v),list(v[0].keys()))

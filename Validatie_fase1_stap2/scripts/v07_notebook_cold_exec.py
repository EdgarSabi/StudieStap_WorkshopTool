"""V07: koude uitvoering van notebook-codecellen in volgorde van de bestandspositie (lege namespace, cwd=Notebooks, MPLBACKEND=Agg).
Dit is GEEN Jupyter-kernelrun (geen nbclient, geen magics); het toetst alleen of de cellen in documentvolgorde kunnen draaien.
Statische controle toonde: geen enkele codecel bevat schrijfoperaties of magics. Notebooks worden niet opgeslagen."""
import json, os, sys, io, contextlib, traceback, warnings
os.environ["MPLBACKEND"]="Agg"; sys.dont_write_bytecode=True; warnings.filterwarnings("ignore")
ROOT=r"C:\Users\School\Projects\StudieStap_WorkshopTool"; NB=os.path.join(ROOT,"Data-analysis","Notebooks"); os.chdir(NB)
res={}
for f in sorted(x for x in os.listdir(NB) if x.endswith(".ipynb")):
    nb=json.load(open(f,encoding="utf-8")); env={"__name__":"__main__"}; ok=[]; fail=None
    for i,c in enumerate(nb["cells"],1):
        src="".join(c["source"])
        if c["cell_type"]!="code" or not src.strip(): continue
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()): exec(compile(src,f"{f}:{i}","exec"),env)
            ok.append(i)
        except BaseException as e:
            fail=dict(cell=i,error=type(e).__name__,msg=str(e)[:160]); break
    res[f]=dict(code_cells=sum(1 for c in nb["cells"] if c["cell_type"]=="code" and "".join(c["source"]).strip()),executed_ok=ok,first_failure=fail)
os.chdir(os.path.join(ROOT,"Validatie_fase1_stap2"))
json.dump(res,open("resultaten/v07_notebook_cold_exec.json","w",encoding="utf-8"),indent=1)
for k,v in res.items(): print(k,json.dumps(v,ensure_ascii=False))

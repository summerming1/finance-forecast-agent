"""Freeze exact applicable nodes/source/deps and run original pytest assertions.

Test orchestration only, not a Controller/evaluator. No Provider, installation,
permission change, remote CI, push, artifact rewriting or test replacement.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from collect_v24_receipt import inspect_junit, run_manifest, source_files

from finance_forecast_agent.focused_identity import file_sha256, identity
from finance_forecast_agent.focused_state import atomic_json, process_birth, terminate_owned_tree


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--temp-prefix',required=True)
    parser.add_argument('--shards',type=int,default=3,choices=[1,2,3,4])
    args=parser.parse_args();repo=Path.cwd().resolve();root=args.out.resolve()
    if root.exists() or repo not in root.parents:raise ValueError('fresh repository-local evidence directory required')
    env=os.environ.copy()
    for key in ['OPENAI_API_KEY','TEACHER_API_KEY','DASHSCOPE_API_KEY','FFA_BROWSER_E2E',
        'FFA_ADMISSION_REAL_RAW','FFA_ADMISSION_SOURCE','FFA_ADMISSION_SHA256']:
        env.pop(key,None)
    env.update(OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
        PYTHONPATH=os.pathsep.join(str(repo/n) for n in ['src','apps','scripts']))
    excluded=['tests/test_models_and_harness.py::test_harness_runs_real_data',
        'tests/test_methodcard_p0_pipeline.py::test_methodcard_derived_paperspec_runs_p0_harness']
    deselect=['--deselect='+n for n in excluded]
    root.mkdir(parents=True)
    collect=[sys.executable,'-m','pytest','--collect-only','-q','tests',*deselect]
    result=subprocess.run(collect,env=env,capture_output=True,text=True,check=False)
    (root/'collection.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError('collection failed; preserve collection.txt')
    nodes=[n.split('::',1)[0].replace('\\','/')+'::'+n.split('::',1)[1]
        for n in result.stdout.splitlines() if n.startswith('tests/') and '::' in n]
    assert len(nodes)==len(set(nodes)) and len(nodes)>1000
    serial=['tests/test_focused_v25_delivery.py','tests/test_evidence_research_workspace.py']
    files=sorted({n.split('::',1)[0] for n in nodes}-set(serial));weights={f:1. for f in files}
    timing=[*sorted((repo/'.v250/final3').glob('shard-*.xml')),*sorted((repo/'.evidence-loop').glob('*.xml'))]
    for report in timing:
        totals={}
        for c in ET.parse(report).getroot().iter('testcase'):
            path=c.get('classname','').replace('.','/')+'.py'
            totals[path]=totals.get(path,0)+float(c.get('time','0'))
        for f,seconds in totals.items():
            if f in weights:weights[f]=max(weights[f],seconds)
    groups=[[] for _ in range(args.shards)];loads=[0.]*args.shards
    for f in sorted(files,key=lambda f:(-weights[f],f)):
        index=min(range(args.shards),key=lambda i:loads[i]);groups[index].append(f);loads[index]+=weights[f]
    packages=lambda:sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())
    before=source_files(repo);deps=packages()
    inputs=[repo/'pyproject.toml',Path(__file__).resolve()]
    plan={'schema_version':'evidence_final_regression_v1','expected_nodes':nodes,'source_files':before,
        'dependencies':deps,'runner_sha256':file_sha256(__file__),'collection_command':collect,
        'excluded_not_authorized':excluded,'exclusion_reason':'both call original run_harness real-market research, not authorized in this batch',
        'serial_files':serial,'groups':groups,'estimated_group_seconds':loads,'commands':[]}
    for i,group in enumerate([serial,*groups]):
        temporary=(repo/(args.temp_prefix+str(i))).resolve()
        if temporary.parent!=repo or temporary.exists():raise ValueError('fresh direct-child temporary directory required')
        plan['commands'].append([sys.executable,'-u','-m','pytest','-q',*group,*deselect,
            '--basetemp='+str(temporary),'--junitxml='+str(root/f'part-{i}.xml'),'--tb=short'])
    atomic_json(root/'preregistration.json',plan)
    running=[];handles=[];exits={}
    def start(i):
        command=plan['commands'][i];name=f'part-{i}.xml'
        run_manifest(root,repo,name,command=subprocess.list2cmdline(command),required=[serial,*groups][i],inputs=inputs)
        h=(root/f'part-{i}.stdout.txt').open('w',encoding='utf-8');handles.append(h)
        p=subprocess.Popen(command,env=env,stdout=h,stderr=subprocess.STDOUT)
        running.append((i,p,process_birth(p.pid)));return p
    def finish(i,p):
        exits[i]=p.returncode
        (root/f'part-{i}.exit.txt').write_text(str(p.returncode),encoding='ascii')
        run_manifest(root,repo,f'part-{i}.xml',exit_code=p.returncode)
        print(json.dumps({'part':i,'actual_exit':p.returncode}),flush=True)
        atomic_json(root/'progress.json',{'completed_exits':exits,'total_parts':len(groups)+1})
    try:
        p=start(0);p.wait();finish(0,p)
        if source_files(repo)!=before or packages()!=deps:
            raise RuntimeError('frozen source/dependencies changed; do not start later parts')
        for i in range(1,len(groups)+1):start(i)
        while len(exits)<len(groups)+1:
            for i,p,_ in running:
                if i not in exits and p.poll() is not None:finish(i,p)
            if len(exits)<len(groups)+1:time.sleep(2)
    except BaseException:
        for _,p,birth in running:
            if p.poll() is None:terminate_owned_tree(p.pid,birth)
        raise
    finally:
        for h in handles:h.close()
    actual=[];reports=[]
    for i in range(len(groups)+1):
        path=root/f'part-{i}.xml'
        reports.append({'part':i,'exit':exits[i],**inspect_junit(path)})
        actual.extend(c.get('classname','').replace('.','/')+'.py::'+c.get('name','')
            for c in ET.parse(path).getroot().iter('testcase'))
    coverage={'expected':len(nodes),'actual':len(actual),'missing':sorted(set(nodes)-set(actual)),
        'extra':sorted(set(actual)-set(nodes)),'duplicates':len(actual)-len(set(actual))}
    unchanged=source_files(repo)==before and packages()==deps
    coverage['exact']=not coverage['missing'] and not coverage['extra'] and not coverage['duplicates']
    body={'reports':reports,'coverage':coverage,'source_dependencies_unchanged':unchanged,
        'source_identity':identity(before,domain='evidence-final-source-v1'),
        'actual_exit':0 if coverage['exact'] and unchanged and not any(exits.values()) else 1,
        'excluded_not_authorized':excluded,'scope':'engineering_only_not_live_or_financial_or_human_acceptance'}
    atomic_json(root/'aggregate.json',body);print(json.dumps(body,ensure_ascii=False),flush=True)
    return body['actual_exit']


if __name__=='__main__':raise SystemExit(main())

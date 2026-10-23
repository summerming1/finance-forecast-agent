"""V24 pure projections of accepted evidence; no fit, network or runtime authority."""
import hashlib
import time
from copy import deepcopy

import numpy as np

from .focused_feature_program import _expression_values, compute_price_features
from .focused_identity import identity

VERSION = "diagnostic_research_v4"


def validate_diagnostic_query(query, accepted_ids, variable_names):
    """New protocol only. Resolve permissions before supplying these allowlists."""
    keys={'schema_version','kind','object_ids','scope','variable_pairs','factor','parameters'}
    if not isinstance(query,dict) or set(query)!=keys:
        raise ValueError('diagnostic query requires exact versioned fields')
    if query['schema_version']!='evidence_diagnostic_query_v1' or query['kind'] not in {
            'DQ-01','DQ-02','DQ-03','DQ-04','DQ-05','DQ-06'}:
        raise ValueError('unknown diagnostic query type/version')
    objects=query['object_ids'];pairs=query['variable_pairs']
    if (not isinstance(objects,list) or not 1<=len(objects)<=2
            or any(not isinstance(x,str) or x not in accepted_ids for x in objects)
            or len(set(objects))!=len(objects)):
        raise ValueError('diagnostic objects must be distinct accepted visible objects')
    if query['scope'] not in {'selected_train','calibration','development_oof'} or query['parameters']!={}:
        raise ValueError('unknown diagnostic scope or parameters')
    scopes={'DQ-01':{'selected_train'},'DQ-02':{'development_oof'},
        'DQ-03':{'selected_train','calibration'},'DQ-04':{'development_oof'},
        'DQ-05':{'development_oof'},'DQ-06':{'selected_train','development_oof'}}
    if query['scope'] not in scopes[query['kind']]:raise ValueError('diagnostic kind/scope mismatch')
    if not isinstance(pairs,list) or len(pairs)*len(objects)>8:
        raise ValueError('at most eight declared pairs total per query')
    for pair in pairs:
        if (not isinstance(pair,list) or len(pair)!=2
                or any(not isinstance(x,str) or x not in variable_names for x in pair)):
            raise ValueError('unknown named diagnostic variable')
    if query['kind'] in {'DQ-03','DQ-06'}:
        if not pairs or query['factor'] is not None:
            raise ValueError('relationship query requires named pairs only')
        if query['kind']=='DQ-03' and any(v in {'target','prediction'} for pair in pairs for v in pair):
            raise ValueError('factor relationships require factors; use DQ-06 for target relations')
        if query['kind']=='DQ-06' and any(pair.count('target')!=1 for pair in pairs):
            raise ValueError('DQ-06 requires exactly one corresponding target per declared pair')
    elif pairs:
        raise ValueError('this diagnostic type does not accept pair scanning')
    if query['kind']=='DQ-04':
        if (not isinstance(query['factor'],str) or query['factor'] not in variable_names
                or query['factor'] in {'target','prediction'}):
            raise ValueError('tail query requires one permitted named factor')
    elif query['factor'] is not None:
        raise ValueError('unexpected factor for diagnostic type')
    return deepcopy(query)


def correlation_summary(left, right):
    """Descriptive paired coefficients; average tied ranks, no IID inference."""
    import pandas as pd

    a,b=np.asarray(left,dtype=float),np.asarray(right,dtype=float)
    if a.ndim!=1 or a.shape!=b.shape:
        raise ValueError('correlation requires aligned one-dimensional pairs')
    valid=np.isfinite(a)&np.isfinite(b);x,y=a[valid],b[valid];n=len(x)
    result={'original_n':len(a),'valid_n':n,'excluded_n':int(len(a)-n),
        'missing_policy':'finite_paired_subset_diagnostic_only','low_support':n<20,
        'rank_method':'average','near_constant_rtol':1e-13,'pearson':None,'spearman':None,
        'scientific_support':'not_established','reason':None}
    if n<2:
        result['reason']='insufficient_pairs'
    elif any(np.ptp(v)<=1e-13*max(1.,float(np.max(abs(v)))) for v in (x,y)):
        result['reason']='near_constant'
    else:
        result['pearson']=float(np.corrcoef(x,y)[0,1])
        result['spearman']=float(np.corrcoef(pd.Series(x).rank(method='average'),
                                            pd.Series(y).rank(method='average'))[0,1])
    return result


def tail_error_summary(control_train_factor, evaluation_factor, actual, predicted, *, control_pred=None):
    """One named variable, control-selected linear q01/q99, shared evaluation mask.

    Inputs must already be identity/time/permission aligned by the dispatcher.
    This diagnostic never changes evaluation targets or the primary MAE.
    """
    train=np.asarray(control_train_factor,dtype=float)
    x,y,p=(np.asarray(v,dtype=float) for v in (evaluation_factor,actual,predicted))
    if (train.ndim!=1 or not len(train) or not np.isfinite(train).all()
            or x.ndim!=1 or x.shape!=y.shape or x.shape!=p.shape):
        raise ValueError('tail query requires finite selected thresholds and aligned arrays')
    c=None if control_pred is None else np.asarray(control_pred,dtype=float)
    if c is not None and c.shape!=x.shape:raise ValueError('unaligned paired predictions')
    lower,upper=np.quantile(train,[.01,.99],method='linear')
    valid=np.isfinite(x)&np.isfinite(y)&np.isfinite(p)
    if c is not None:valid &= np.isfinite(c)
    tail=valid&((x<lower)|(x>upper));other=valid&~tail
    error=abs(p-y)
    mean=lambda v,m:float(np.mean(v[m])) if np.any(m) else None
    result={'thresholds':[float(lower),float(upper)],'quantile_method':'linear',
        'threshold_source':'control_selected_train','mask_definition':'strict_below_q01_or_above_q99',
        'original_n':len(x),'valid_pair_n':int(valid.sum()),'excluded_n':int((~valid).sum()),
        'n_tail':int(tail.sum()),'n_other':int(other.sum()),'tail_fraction':float(tail.sum()/len(x)) if len(x) else None,
        'tail_mae':mean(error,tail),'other_mae':mean(error,other),'low_support':int(tail.sum())<10,
        'scientific_support':'not_established','primary_targets_changed':False}
    if c is not None:
        delta=error-abs(c-y)
        result.update(tail_loss_delta=mean(delta,tail),other_loss_delta=mean(delta,other),
            direction='candidate_minus_control_positive_is_worse')
    return result


def dispatch_diagnostic_query(query, objects, *, campaign_id):
    """Execute one bounded query over accepted, permission-filtered input views.

    ``variables`` are approved deterministic arrays in research row order, never
    supplied executable formulas. The Controller owns artifact/receipt acceptance.
    This function has no fitting, filesystem, Provider or persistence capability.
    """
    started=time.perf_counter()
    ids=query.get('object_ids',[]) if isinstance(query,dict) else []
    names=set.intersection(*(set(objects[x]['variables']) for x in ids if x in objects)) if ids and all(x in objects for x in ids) else set()
    names |= {'prediction','target'}
    q=validate_diagnostic_query(query,set(objects),names)
    selected=[objects[x] for x in q['object_ids']]
    rows=[_validated_rows(o['artifact']) for o in selected]
    if len(selected)==2:aligned_predictions(selected[0]['artifact'],selected[1]['artifact'])
    requested={v for pair in q['variable_pairs'] for v in pair}
    if q['factor']:requested.add(q['factor'])
    bound=[]
    for o in selected:
        variable_hashes={}
        for name in sorted(requested-{'prediction','target'}):
            array=np.ascontiguousarray(o['variables'][name],dtype='<f8')
            if array.ndim!=1:raise ValueError('named diagnostic variable must be one-dimensional')
            variable_hashes[name]={'dtype':'float64_le','shape':list(array.shape),
                'sha256':hashlib.sha256(array.tobytes()).hexdigest()}
        if 'target' in requested and q['scope']=='selected_train' and o.get('targets') is not None:
            array=np.ascontiguousarray(o['targets'],dtype='<f8')
            if array.ndim!=1:raise ValueError('mature training targets must be one-dimensional')
            variable_hashes['target']={'dtype':'float64_le','shape':list(array.shape),
                'sha256':hashlib.sha256(array.tobytes()).hexdigest()}
        bound.append({'artifact':o['artifact'],'method_identity':o['method_identity'],
            'training_receipts':o['training_receipts'],
            'variables':variable_hashes,
            'variable_origins':{k:v for k,v in o.get('variable_origins',{}).items() if k in requested},
            'diagnostic':o['diagnostic'] if q['kind'] in {'DQ-01','DQ-05'} else None})
    key=identity({'namespace':campaign_id,'query':q,'objects':bound,
        'implementation':'bounded-evidence-diagnostics-v1'},domain='evidence-query-v1')
    tools={'DQ-01':'execution_conformance','DQ-02':'prediction_performance',
        'DQ-03':'named_relationships','DQ-04':'tail_errors',
        'DQ-05':'fixed_period_state','DQ-06':'contemporaneous_relationships'}
    out={'schema_version':'evidence_diagnostic_result_v1','query':q,'query_identity':key,
        'diagnostic_id':campaign_id+':query:'+key,
        'owner_campaign_id':campaign_id,'tool':tools[q['kind']],'status':'available','results':[],
        'fit_calls':0,'provider_requests':0,'cpu_seconds':None,'scientific_support':'not_established'}
    functions={'DQ-01':['accepted_execution_receipts'],'DQ-02':['saved_residual_diagnostic','paired_absolute_loss'],
        'DQ-03':['pearson','spearman_average_rank'],'DQ-04':['quantile_linear_q01_q99','strict_shared_mask','mean_absolute_loss'],
        'DQ-05':['frozen_volatility_groups','paired_absolute_loss'],'DQ-06':['pearson','spearman_average_rank']}
    out['read_receipts']=[{'object_id':cid,'method_identity':o['method_identity'],
        'prediction_artifact_hash':identity(o['artifact'],domain='diagnostic-prediction-v1'),
        'scope':q['scope'],'functions':functions[q['kind']],
        'variables':{name:deepcopy(o.get('variable_origins',{}).get(name,{
            'kind':'accepted_prediction_row' if name in {'prediction','target'} else 'caller_bound_variable',
            'name':name})) for name in sorted(requested)},
        'row_source':'results.*.row_ids/evaluation_row_ids/threshold_row_ids; DQ01 original training receipts; DQ02/05 accepted artifact fixed folds',
        'input_identity':key} for cid,o in zip(q['object_ids'],selected,strict=True)]
    def finish():
        out['result_hash']=identity(out,domain='evidence-diagnostic-result-v1')
        out['compute_wall_seconds']=time.perf_counter()-started
        return out
    if q['kind']=='DQ-01':
        out['results']=[{'object_id':cid,'artifact_hash':identity(o['artifact'],domain='diagnostic-prediction-v1'),
            'training_receipts':deepcopy(o['training_receipts'])} for cid,o in zip(q['object_ids'],selected,strict=True)]
        return finish()
    if q['kind']=='DQ-02':
        out['results']=[{'object_id':cid,'values':residual_diagnostic(o['artifact']),
            'folds':[{'fold_id':fold,'values':residual_diagnostic({**o['artifact'],
                'rows':[r for r in o['artifact']['rows'] if r['fold_id']==fold]})}
                for fold in sorted({r['fold_id'] for r in o['artifact']['rows']})]}
            for cid,o in zip(q['object_ids'],selected,strict=True)]
        if len(selected)==2:
            out['paired_loss_delta']=float(np.mean([abs(a['y_pred']-a['y_true'])-abs(b['y_pred']-b['y_true'])
                for a,b in zip(rows[0],rows[1],strict=True)]))
            out['direction']='first_minus_control_positive_is_worse'
            out['paired_fold_losses']=[{'fold_id':a['fold_id'],'n':a['values']['rows'],
                'first_mae':a['values']['mae'],'control_mae':b['values']['mae'],
                'loss_delta':a['values']['mae']-b['values']['mae']}
                for a,b in zip(out['results'][0]['folds'],out['results'][1]['folds'],strict=True)]
        return finish()
    if q['kind']=='DQ-05':
        out['results']=[{'object_id':cid,'values':deepcopy(o['diagnostic'].get('volatility_groups','unavailable'))}
            for cid,o in zip(q['object_ids'],selected,strict=True)]
        if any(x['values']=='unavailable' for x in out['results']):out['status']='unavailable'
        if len(selected)==2 and isinstance(selected[-1]['diagnostic'].get('volatility_groups'),list):
            out['paired_group_losses']=relative_group_losses(selected[0]['artifact'],selected[-1]['artifact'],
                selected[-1]['diagnostic']['volatility_groups'])
        return finish()
    if q['kind']=='DQ-04' and q['scope']!='development_oof':
        raise ValueError('tail errors require common development OOF scope')
    for cid,o,predictions in zip(q['object_ids'],selected,rows,strict=True):
        if q['scope']=='selected_train' and any(v=='prediction' for pair in q['variable_pairs'] for v in pair):
            out.update(status='unavailable',reason='no_saved_train_predictions');continue
        for fold in sorted({r['fold_id'] for r in predictions}):
            test=[r for r in predictions if r['fold_id']==fold]
            test_ids=np.array([r['row_id'] for r in test],dtype=int)
            receipts=[r for r in o['training_receipts'] if r['fold_id']==fold]
            control=selected[-1];control_receipts=[r for r in control['training_receipts'] if r['fold_id']==fold]
            if ((q['scope']!='development_oof' or q['kind']=='DQ-04') and
                    (not receipts or (q['kind']=='DQ-04' and not control_receipts))):
                out.update(status='unavailable',reason='missing_actual_training_scope');continue
            if q['kind']=='DQ-04':
                if cid!=q['object_ids'][0]:continue  # One shared query, not two separate tail searches.
                train=np.asarray(control_receipts[0]['selected_train'],dtype=int)
                factor=q['factor'];control_values=np.asarray(control['variables'][factor],dtype=float)
                current_values=np.asarray(o['variables'][factor],dtype=float)
                left_origin=o.get('variable_origins',{}).get(factor,{})
                right_origin=control.get('variable_origins',{}).get(factor,{})
                if left_origin.get('formula_hash')!=right_origin.get('formula_hash'):
                    raise ValueError('tail objects require the same approved formula identity')
                if not np.array_equal(current_values[test_ids],control_values[test_ids],equal_nan=True):
                    raise ValueError('tail query requires the exact same formula/mask for both objects')
                cp=[r['y_pred'] for r in rows[-1] if r['fold_id']==fold] if len(selected)==2 else None
                values=tail_error_summary(control_values[train],control_values[test_ids],
                    [r['y_true'] for r in test],[r['y_pred'] for r in test],control_pred=cp)
                out['results'].append({'fold_id':fold,'object_id':cid,'control_id':q['object_ids'][-1],
                    'evaluation_row_ids':test_ids.tolist(),'threshold_row_ids':train.tolist(),'values':values})
                continue
            scope_ids=(test_ids if q['scope']=='development_oof' else
                np.asarray(receipts[0]['selected_train' if q['scope']=='selected_train' else 'calibration_rows'],dtype=int))
            def values(name, test=test, o=o, scope_ids=scope_ids):
                if name in {'prediction','target'}:
                    if name=='target' and q['scope']=='selected_train' and o.get('targets') is not None:
                        return np.asarray(o['targets'],dtype=float)[scope_ids]
                    if q['scope']!='development_oof':return None
                    return np.array([r['y_pred' if name=='prediction' else 'y_true'] for r in test])
                return np.asarray(o['variables'][name],dtype=float)[scope_ids]
            for left,right in q['variable_pairs']:
                a,b=values(left),values(right)
                if a is None or b is None:
                    out.update(status='unavailable',reason='no_verified_training_target_or_predictions');continue
                out['results'].append({'fold_id':fold,'object_id':cid,'variables':[left,right],
                    'scope':q['scope'],'row_ids':scope_ids.tolist(),'values':correlation_summary(a,b)})
    return finish()


def query_projection(body):
    """Keep all numerical entries; full scope lists stay in accepted audit."""
    original={k:v for k,v in body.items() if k not in {'compute_wall_seconds','result_hash'}}
    if identity(original,domain='evidence-diagnostic-result-v1')!=body['result_hash']:
        raise ValueError('accepted diagnostic query result hash mismatch')
    out=deepcopy({k:v for k,v in body.items() if k!='compute_wall_seconds'})
    for result in out['results']:
        for key in ('row_ids','evaluation_row_ids','threshold_row_ids'):
            if key in result:
                ids=result.pop(key)
                result[key+'_hash']=identity(ids,domain='evidence-query-scope-v1')
                result[key+'_count']=len(ids)
    out['projection_version']='evidence_query_projection_v1'
    return out
RECIPES = {"RCP-01": "overall", "RCP-02": "contribution", "RCP-03": "simplification",
           "RCP-04": "diagnose", "RCP-05": "diagnose"}


def selection_policy():
    return {"schema_version": "research_selection_v1", "primary_metric": "mae",
            "min_relative_mae_improvement": .0025, "evidence_tier": "development_only",
            "reference": "best_fixed_control_or_user_start", "tie_policy": "retain_start_then_candidate_id",
            "max_degradation": 0., "fallback": "qualified_start_or_unresolved"}


def research_policy(visibility="on", *, support="J"):
    if visibility not in {"on", "off"}:
        raise ValueError("diagnostic visibility must be on or off")
    if support not in {"R", "D", "J"}:
        raise ValueError("unknown bounded decision support")
    templates = [rule_template(k) for k in ("overall", "high_volatility", "contribution", "simplification", "diagnose")]
    shared = {k:v for k,v in templates[0].items() if all(t[k] == v for t in templates)}
    columns = [k for k in templates[0] if k not in shared]
    return {"schema_version": VERSION, "diagnostic_visibility": visibility,
            "knowledge_mode": "present_day_research", "automatic_fit_limit": 0,
            "recipes": RECIPES, "selection_policy": selection_policy(),
            "rule_templates": {"shared":shared,"columns":columns,
                               "values":[[t[k] for k in columns] for t in templates]},
            "memory": "cold", "pair_diagnostic_limit": 1,
            "planning_projection": "diagnostic_planning_projection_v2",
            "diagnostic_reference": "baseline_ridge",
            "predeclared_pair": ["baseline_ridge", "baseline_rf"],
            "decision_support":support, "decision_contract":"research_decision_v1",
            "legacy_design_policy":"old_policy_or_R_D_Random_reference_only",
            "require_j_decision": support == "J",
            "decision_link_projection":"frozen_decision_links_v1",
            "shared_field_encoding":"diagnostic_shared_fields_v3",
            "design_text_budget": 1000,
            "formation_policy":"frozen_context_timing_v2"}


def rule_template(question):
    if question not in {"overall", "high_volatility", "contribution", "simplification", "diagnose"}:
        raise ValueError("unknown observation rule")
    return {"schema_version": "observation_rule_v1", "question": question, "metric": "mae",
            "unit": "return", "evidence_tier": "development_only", "precision": "float64_native",
            "group": "past_volatility20_train_q75_linear_strict_v1" if question == "high_volatility" else "all_targets",
            "minimum_rows": 30 if question == "high_volatility" else 1,
            "minimum_rows_per_fold": 10, "minimum_folds": 2, "minimum_improved_folds": 2,
            "max_degradation": 0., "missing_policy": "insufficient_evidence"}


def freeze_rule(question, control_id, control_fingerprint, candidate_id, candidate_fingerprint=None):
    out = {**rule_template(question), "control_candidate_id": control_id,
           "control_fingerprint": control_fingerprint, "candidate_id": candidate_id,
           "candidate_fingerprint": candidate_fingerprint}
    out["rule_hash"] = identity(out, domain="observation-rule-v1")
    return out


def verify_rule(rule):
    expected = freeze_rule(rule["question"], rule["control_candidate_id"], rule["control_fingerprint"], rule["candidate_id"], rule["candidate_fingerprint"])
    if rule != expected:
        raise ValueError("observation rule identity or policy changed")


def _validated_rows(artifact):
    rows = artifact["rows"]
    if not rows:
        raise ValueError("prediction contract: empty target rows")
    ids = [(r["fold_id"], r["row_id"]) for r in rows]
    if ids != sorted(ids) or len({r["row_id"] for r in rows}) != len(rows):
        raise ValueError("prediction contract: order or duplicate targets")
    if any(r["candidate_id"] != artifact["candidate_id"] or
           r["candidate_fingerprint"] != artifact["candidate_fingerprint"] for r in rows):
        raise ValueError("prediction contract: candidate identity")
    if not np.isfinite([[r["y_true"], r["y_pred"]] for r in rows]).all():
        raise ValueError("prediction contract: non-finite values")
    return rows


def aligned_predictions(a, b):
    left, right = _validated_rows(a), _validated_rows(b)
    for key in ("task_id", "task_version", "dataset_fingerprint", "split_spec", "evaluation_policy"):
        if a[key] != b[key]:
            raise ValueError("prediction contract: incompatible " + key)
    keys = ("fold_id", "row_id", "raw_row_id", "session_date", "decision_time", "target_observed_at", "y_true")
    if len(left) != len(right) or any(tuple(x.get(k) for k in keys) != tuple(y.get(k) for k in keys)
                                      for x, y in zip(left, right, strict=True)):
        raise ValueError("prediction contract: incomplete or incompatible target identity")
    return left, right


def residual_diagnostic(artifact):
    rows = _validated_rows(artifact)
    actual, predicted = np.asarray([[r["y_true"], r["y_pred"]] for r in rows], dtype=float).T
    residual = predicted-actual
    return {"source": "complete_prediction_artifact", "rows": len(rows), "mae": float(np.mean(abs(residual))),
            "residual_mean": float(np.mean(residual)), "residual_median": float(np.median(residual)),
            "negative_fraction": float(np.mean(residual < 0)), "zero_fraction": float(np.mean(residual == 0)),
            "positive_fraction": float(np.mean(residual > 0)), "residual_quantiles": np.quantile(residual, [.05, .25, .5, .75, .95], method="linear").tolist(),
            "prediction_std": float(np.std(predicted)), "automatic_correction": False,
            "near_constant_is_failure": False, "train_development_gap": "unavailable_no_saved_train_predictions",
            "continuous_autocorrelation": "unavailable_disjoint_development_windows"}


def pair_diagnostic(a, b):
    left, right = aligned_predictions(a, b)
    ra = np.array([r["y_pred"]-r["y_true"] for r in left])
    rb = np.array([r["y_pred"]-r["y_true"] for r in right])
    return {"source": "aligned_existing_predictions", "weights": [.5, .5],
            "residual_correlation": float(np.corrcoef(ra, rb)[0, 1]) if np.std(ra) > 0 and np.std(rb) > 0 else None,
            "equal_weight_mae": float(np.mean(abs((ra+rb)/2))),
            "best_member_mae": min(float(np.mean(abs(ra))), float(np.mean(abs(rb)))),
            "recommendation_authorized": False, "new_fit_calls": 0}


def prediction_information_id(artifact):
    """Exact numeric/execution identity; audit aliases are not new evidence."""
    _validated_rows(artifact)
    content = {k:v for k,v in artifact.items() if k not in {"candidate_id", "campaign_id"}}
    content["rows"] = [{k:v for k,v in row.items() if k != "candidate_id"} for row in artifact["rows"]]
    return identity(content, domain="prediction-information-v1")


def classify_observation(rule, child, control, *, history=(), cached=False,
                         evidence_tier="development_only", formation=None, groups=None):
    """Finite audit projection, not an execution/novelty permission or significance test."""
    verify_rule(rule)
    left, right = aligned_predictions(child, control)
    child_id, control_id = prediction_information_id(child), prediction_information_id(control)
    base = identity(sorted([child_id, control_id]), domain="comparison-measurements-v1")
    semantics = {k:v for k,v in rule.items() if k not in {"rule_hash", "candidate_id",
        "candidate_fingerprint", "control_candidate_id", "control_fingerprint"}}
    observed = identity({"child":child_id, "control":control_id, "rule":semantics,
        "groups":groups if rule["question"] == "high_volatility" else None}, domain="comparison-observation-v1")
    prior = [row.get("information", row) for row in history]
    exact = [r for r in prior if r.get("observation_identity") == observed]
    reverse = [r for r in prior if r.get("base_comparison_id") == base and
        r.get("child_prediction_id") == control_id and r.get("control_prediction_id") == child_id]
    # Reverse overall/contribution are the already observed full-target loss
    # comparison, but their denominator and question conclusion are recomputed.
    known = bool(exact or (reverse and rule["question"] in {"overall", "contribution"}))
    cl = float(np.mean([abs(r["y_pred"]-r["y_true"]) for r in left]))
    pl = float(np.mean([abs(r["y_pred"]-r["y_true"]) for r in right]))
    proof = (formation or {}).get("timing_proof")
    timing = ("predeclared" if proof in {"frozen_batch_plan_before_execution", "frozen_automatic_rule_before_results"}
              else "posthoc_exploratory" if proof == "both_predictions_already_visible_before_new_question"
              else "timing_unverified")
    return {"schema_version":"research_information_v2", "base_comparison_id":base,
        "observation_identity":observed, "child_prediction_id":child_id, "control_prediction_id":control_id,
        "prediction_provenance":"cache_reuse" if cached else "new_execution",
        "analysis_novelty":"known_or_reverse_comparison" if known else
            "first_valid_derived_analysis" if cached else "first_valid_analysis",
        "evidence_tier":evidence_tier, "formation_status":timing,
        "formation":deepcopy(formation or {"timing_proof":"unavailable"}),
        "reference_observation_ids":[r["observation_identity"] for r in exact or reverse],
        "child_mae":cl, "control_mae":pl,
        "relative_mae_improvement":(pl-cl)/pl if pl > 0 else None,
        "recommendation_authorized":False}


def comparison_projection(observations):
    """Rebuild from immutable first-event records, never reclassify against itself."""
    out, seen = [], set()
    for observation in observations:
        row = observation.get("information", observation)
        if row.get("schema_version") not in {"research_information_v1", "research_information_v2"}:
            continue  # Legacy facts remain legacy, not fabricated migrations.
        key = row["observation_identity"]
        if key not in seen:
            out.append(deepcopy(row))
            seen.add(key)
    return out


def volatility_groups(prices, raw_splits):
    prices = np.asarray(prices, dtype=float)
    if prices.ndim != 1 or not np.isfinite(prices).all() or np.any(prices <= 0):
        raise ValueError("raw price contract invalid")
    returns = np.r_[np.nan, prices[1:]/prices[:-1]-1]
    vol, _, _ = _expression_values({"op": "rolling_std", "window": 20,
        "arg": {"op": "input", "name": "return_1"}}, returns)
    groups = []
    for fold_id, (train, test) in enumerate(raw_splits):
        train, test = np.asarray(train, dtype=int), np.asarray(test, dtype=int)
        if (len(train) == 0 or len(test) == 0 or len(set(train)) != len(train) or
                np.any(train < 20) or np.any(test >= len(prices)) or train[-1] >= test[0]):
            raise ValueError("volatility calibration contract invalid")
        threshold = float(np.quantile(vol[train], .75, method="linear"))
        groups.append({"fold_id": fold_id, "calibration_rows": train.tolist(),
                       "threshold": threshold, "rows": test[vol[test] > threshold].tolist(),
                       "source": "contract_bound_raw_prices_not_prediction_labels"})
    return groups


def _protection_events(node, returns, masks):
    """Node-level input-time events; do not confuse them with output dependencies."""
    if node["op"] == "safe_divide":
        a, al, _ = _expression_values(node["left"], returns)
        b, bl, _ = _expression_values(node["right"], returns)
        mask = np.zeros(len(returns), dtype=bool)
        begin = max(al, bl)
        mask[begin:] = (abs(b[begin:]) < 1e-8) & np.isfinite(a[begin:])
        masks.append(mask)
    for key in ("arg", "left", "right"):
        if key in node:
            _protection_events(node[key], returns, masks)


def relative_group_losses(artifact, reference, groups):
    """Paired complete-target losses; positive delta means candidate is worse."""
    rows, controls = aligned_predictions(artifact, reference)
    losses = np.array([abs(r["y_pred"]-r["y_true"]) for r in rows])
    ref = np.array([abs(r["y_pred"]-r["y_true"]) for r in controls])
    out = {"reference_candidate_id":reference["candidate_id"],
           "reference_prediction_hash":identity(reference, domain="diagnostic-prediction-v1"),
           "delta_sign":"candidate_minus_frozen_reference_positive_is_worse",
           "overall":{"rows":len(rows), "candidate_mae":float(losses.mean()),
                      "reference_mae":float(ref.mean()), "loss_delta":float((losses-ref).mean())}, "folds":[]}
    if not isinstance(groups, list):
        out["groups"] = "unavailable_no_raw_state_source"
        return out
    if [g["fold_id"] for g in groups] != sorted({r["fold_id"] for r in rows}):
        raise ValueError("relative diagnostic group fold mismatch")
    for group in groups:
        fold_indices = [i for i, r in enumerate(rows) if r["fold_id"] == group["fold_id"]]
        selected = set(group["rows"])
        if len(selected) != len(group["rows"]) or not selected <= {rows[i]["row_id"] for i in fold_indices}:
            raise ValueError("relative diagnostic group target mismatch")
        for name in ("all", "high_volatility", "other"):
            idx = [i for i in fold_indices if name == "all" or (rows[i]["row_id"] in selected) == (name == "high_volatility")]
            out["folds"].append({"fold_id":group["fold_id"], "group":name, "rows":len(idx),
                "candidate_mae":float(losses[idx].mean()) if idx else None,
                "reference_mae":float(ref[idx].mean()) if idx else None,
                "loss_delta":float((losses[idx]-ref[idx]).mean()) if idx else None})
    return out


def derive_diagnostic(artifact, *, candidate, raw_history, frame, splits, reference=None, training_execution=None):
    started = time.perf_counter()
    out = {"schema_version": "deterministic_diagnostic_v1", "candidate_id": artifact["candidate_id"],
           "prediction_hash": identity(artifact, domain="diagnostic-prediction-v1"),
           "residual": residual_diagnostic(artifact), "volatility_groups": "unavailable",
           "training_features": "unavailable", "protected_division": "unavailable",
           "evidence_tier": "development_only", "new_fit_calls": 0, "provider_requests": 0}
    if raw_history is not None:
        raw_map = frame["raw_row_id"].to_numpy(dtype=int)
        expected = [(i, int(row)) for i, (_, test) in enumerate(splits) for row in test]
        if [(r["fold_id"], r["row_id"]) for r in artifact["rows"]] != expected:
            raise ValueError("prediction contract: targets differ from frozen split")
        if any(r.get("raw_row_id") != int(raw_map[r["row_id"]]) or
               r["y_true"] != float(frame.iloc[r["row_id"]]["label"]) for r in artifact["rows"]):
            raise ValueError("prediction contract: raw mapping or label changed")
        prices = raw_history["spy_adj_close"].to_numpy(dtype=float)
        raw_splits = [(raw_map[train], raw_map[test]) for train, test in splits]
        groups = volatility_groups(prices, raw_splits)
        inverse = {int(raw): int(i) for i, raw in enumerate(raw_map)}
        for group in groups:
            group["raw_rows"] = group["rows"]
            group["rows"] = [inverse[r] for r in group["rows"]]
        out["volatility_groups"] = groups
        out["raw_history_hash"] = identity(raw_history.to_dict(orient="list"), domain="diagnostic-raw-v1")
        if candidate.feature_program is not None:
            matrix = compute_price_features(prices, candidate.feature_program, candidate.feature_groups)
            stats, protected = [], []
            returns = np.r_[np.nan, prices[1:]/prices[:-1]-1]
            masks = []
            for feature in candidate.feature_program.to_dict()["features"]:
                _protection_events(feature["expression"], returns, masks)
            for fold_id, (train, _) in enumerate(raw_splits):
                if getattr(candidate, 'training_policy', None) is not None:
                    if not training_execution or len(training_execution) != len(raw_splits):
                        raise ValueError('method diagnostic requires actual training receipts')
                    receipt = training_execution[fold_id]
                    if receipt['fold_id'] != fold_id:
                        raise ValueError('method diagnostic training fold mismatch')
                    train = raw_map[np.asarray(receipt['selected_train'], dtype=int)]
                x = matrix.values[train]
                variances = np.var(x, axis=0)
                nonconstant = variances > 0
                correlations = np.corrcoef(x[:, nonconstant], rowvar=False) if sum(nonconstant) > 1 else np.empty((0, 0))
                stats.append({"fold_id": fold_id, "source": "actual_training_feature_matrix",
                    "raw_training_rows": train.tolist(), "columns": list(matrix.columns), "variance": variances.tolist(),
                    "max_abs_off_diagonal_correlation": float(np.max(abs(correlations-np.eye(len(correlations))))) if correlations.size else None})
                # Names, not array tail position, identify redundant components.
                columns = list(matrix.columns)
                active = [i for i, value in enumerate(nonconstant) if value]
                stats[-1]["generated_correlations"] = [
                    {"feature":columns[i], "other":columns[j], "correlation":float(correlations[a, b])}
                    for a, i in enumerate(active) for b, j in enumerate(active)
                    if i < j and (columns[i].startswith("gen_") or columns[j].startswith("gen_"))]
                event_counts = [int(mask[train].sum()) for mask in masks]
                triggered = int(np.logical_or.reduce([mask[train] for mask in masks]).sum()) if masks else 0
                protected.append({"fold_id": fold_id, "scope": "division_node_input_events_on_actual_training_raw_rows",
                    "node_event_count": sum(event_counts), "node_counts": event_counts,
                    "distinct_triggered_rows": triggered, "denominator_rows": len(train), "row_rate": triggered/len(train)})
            out["training_features"], out["protected_division"] = stats, protected
            if getattr(candidate, 'training_policy', None) is not None:
                out['training_policy'] = candidate.training_policy.to_dict()
    if reference is not None:
        out["relative_losses"] = relative_group_losses(artifact, reference, out["volatility_groups"])
    out["limitations"] = ["Descriptive development evidence, not significance or causal proof.",
                          "No bias correction, ensemble selection, refit or source download."]
    # Measured cost is audit-only, excluded from deterministic numeric identity.
    out["diagnostic_hash"] = identity(out, domain="deterministic-diagnostic-v1")
    out["compute_wall_seconds"] = time.perf_counter()-started
    return out


def observation_result(rule, child, control, *, groups=None):
    verify_rule(rule)
    if control["candidate_id"] != rule["control_candidate_id"] or control["candidate_fingerprint"] != rule["control_fingerprint"]:
        raise ValueError("observation contract: wrong control")
    cr, pr = aligned_predictions(child, control)
    if rule["candidate_fingerprint"] is not None and child["candidate_fingerprint"] != rule["candidate_fingerprint"]:
        raise ValueError("observation contract: child execution differs from frozen plan")
    losses = np.array([abs(r["y_pred"]-r["y_true"]) for r in cr])
    reference = np.array([abs(r["y_pred"]-r["y_true"]) for r in pr])
    improvement = float(np.mean(reference)-np.mean(losses))
    out = {"rule": deepcopy(rule), "overall_abs_improvement": improvement,
           "prediction_improvement": improvement > 0, "folds": [],
           "observation_status": "does_not_meet", "interpretation_review": False}
    question = rule["question"]
    if question == "high_volatility":
        if groups is None or isinstance(groups, str):
            out.update(observation_status="insufficient_evidence", reason="raw state source unavailable")
            return out
        if groups and [g['fold_id'] for g in groups] != sorted({r['fold_id'] for r in cr}):
            raise ValueError('observation contract: group folds incomplete, reordered or duplicate')
        index = {r["row_id"]: i for i, r in enumerate(cr)}
        total = 0
        for group in groups:
            if any(row not in index or cr[index[row]]["fold_id"] != group["fold_id"] for row in group["rows"]):
                raise ValueError("observation contract: wrong group targets")
            indices = [index[row] for row in group["rows"]]
            if len(set(indices)) != len(indices):
                raise ValueError("observation contract: duplicate group rows")
            delta = float(np.mean(reference[indices]-losses[indices])) if indices else None
            total += len(indices)
            out["folds"].append({"fold_id": group["fold_id"], "rows": len(indices), "abs_improvement": delta,
                                 "eligible": len(indices) >= rule["minimum_rows_per_fold"]})
        eligible = [r for r in out["folds"] if r["eligible"]]
        if total < rule["minimum_rows"] or len(eligible) < rule["minimum_folds"]:
            out.update(observation_status="insufficient_evidence", reason="descriptive sample minima not met")
            return out
        pooled = sum(r["rows"] * (r["abs_improvement"] or 0.) for r in out["folds"])/total
        out["group_abs_improvement"] = pooled
        met = pooled > 0 and improvement >= 0 and sum(r["abs_improvement"] > 0 for r in eligible) >= rule["minimum_improved_folds"]
    else:
        met = improvement < 0 if question == "contribution" else improvement >= 0 if question == "simplification" else improvement > 0
    out["observation_status"] = "meets_predeclared_observation" if met else "does_not_meet"
    return out


def select_recommendation(policy, start, research, controls, *, execution_status):
    if policy != selection_policy():
        raise ValueError("selection policy differs from frozen approved policy")
    def rank(row):
        return (row["metrics"]["mae"], row["candidate_id"])
    def qualified(row):
        return row is not None and np.isfinite(row["metrics"]["mae"]) and row["metrics"]["mae"] >= 0
    if any(not qualified(row) for row in [*research, *controls]):
        raise ValueError("selection contract: invalid metric")
    best = min(research, key=rank) if research else None
    ref = min([*controls, *([start] if qualified(start) else [])], key=rank) if controls or qualified(start) else None
    selected = start if qualified(start) else None
    action = "retain_start" if selected else "unresolved"
    relative = (ref["metrics"]["mae"]-best["metrics"]["mae"])/ref["metrics"]["mae"] if ref and best and ref["metrics"]["mae"] > 0 else None
    if execution_status == "completed" and best and relative is not None and relative >= policy["min_relative_mae_improvement"] and (selected is None or best["metrics"]["mae"] < selected["metrics"]["mae"]):
        selected, action = best, "select_research_candidate"
    available = [*controls, *research, *([start] if qualified(start) else [])]
    gain_floor = 1e-12  # Frozen reporting boundary, not a new primary selection threshold.
    gain = ((start['metrics']['mae']-selected['metrics']['mae'])/start['metrics']['mae']
            if execution_status == 'completed' and qualified(start) and selected and start['metrics']['mae'] > gain_floor else None)
    return {"schema_version": "frozen_recommendation_v1", "selection_policy": deepcopy(policy),
            "research_start":start, "recommendation_gain_vs_start":gain, "gain_ratio_min_start_mae":gain_floor,
            "selection_reason":("incomplete_execution_conservative_fallback" if execution_status != 'completed' else
                "no_research_candidate" if best is None else "passed_frozen_primary_screen" if action == 'select_research_candidate' else
                "research_candidate_did_not_qualify_to_replace_start"),
            "best_research_candidate": best, "selected_recommendation": selected, "selection_action": action,
            "best_available_model": min(available, key=rank) if available else None,
            "relative_research_improvement_vs_selection_reference": relative,
            "execution_status": execution_status, "evidence_tier": "development_only"}


def verify_diagnostic(body, artifact=None):
    numeric = {k: v for k, v in body.items() if k not in {"diagnostic_hash", "compute_wall_seconds"}}
    if identity(numeric, domain="deterministic-diagnostic-v1") != body["diagnostic_hash"]:
        raise ValueError("diagnostic contract: content changed")
    if artifact is not None and body["prediction_hash"] != identity(artifact, domain="diagnostic-prediction-v1"):
        raise ValueError("diagnostic contract: prediction changed")


def diagnostic_projection(body, *, version="diagnostic_planning_projection_v1"):
    """Bounded planning view; scope hashes retain identities, full rows stay in audit."""
    verify_diagnostic(body)
    out = deepcopy({k: v for k, v in body.items() if k != "compute_wall_seconds"})
    for group in out["volatility_groups"] if isinstance(out["volatility_groups"], list) else []:
        for key in ("rows", "raw_rows", "calibration_rows"):
            group[key+"_hash"] = identity(group[key], domain="diagnostic-scope-v1")
            group[key+"_count"] = len(group.pop(key))
    for fold in out["training_features"] if isinstance(out["training_features"], list) else []:
        fold["training_scope_hash"] = identity(fold["raw_training_rows"], domain="diagnostic-scope-v1")
        fold["training_rows_count"] = len(fold.pop("raw_training_rows"))
    out["projection_version"] = "diagnostic_planning_projection_v1"
    if version == "diagnostic_planning_projection_v2":
        out["projection_version"] = version
        # All scope/column identities remain references to the immutable audit.
        for fold in out["training_features"] if isinstance(out["training_features"], list) else []:
            fold["columns_hash"] = identity(fold["columns"], domain="diagnostic-columns-v1")
            names, variances = fold.pop("columns"), fold.pop("variance")
            fold["generated_variance"] = {n:v for n, v in zip(names, variances, strict=True) if n.startswith("gen_")}
            fold.pop("source", None)
            # Named correlations remain descriptive; extrema plus identity bind
            # the complete bounded pair list retained in the audit artifact.
            pairs = fold.pop("generated_correlations", [])
            fold["generated_correlations_hash"] = identity(pairs, domain="diagnostic-correlation-v1")
            fold["strongest_generated_pair"] = max(pairs, key=lambda p:abs(p["correlation"])) if pairs else None
        relative = out.get("relative_losses")
        if relative and "folds" in relative:
            columns = ["fold_id", "group", "rows", "candidate_mae", "reference_mae", "loss_delta"]
            relative["fold_columns"] = columns
            relative["fold_values"] = [[r[k] for k in columns] for r in relative.pop("folds")]
        out.pop("limitations", None)  # common policy below, not selective evidence removal
        out["limitations_ref"] = "diagnostic_common_limitations_v1"
    elif version != "diagnostic_planning_projection_v1":
        raise ValueError("unsupported diagnostic planning projection")
    return out


def default_design(recipe, *, question=None, basis="domain_hypothesis", symptom_refs=None):
    return {"recipe_id": recipe, "question": question or RECIPES[recipe], "basis": basis,
            "symptom_refs": symptom_refs or [], "competing_explanation": "unknown; descriptive experiment cannot distinguish market mechanisms",
            "falsification_condition": "Frozen deterministic observation does not meet its predeclared direction"}


def bind_design(design, hypothesis, candidate, results, prompt):
    from .focused_adaptive import EvidenceIndex
    if candidate is None:
        if design is None:
            return None
        if hypothesis.action_type != "diagnose":
            raise ValueError("control action cannot smuggle a training design")
    required = {"recipe_id", "question", "basis", "competing_explanation", "falsification_condition"}
    if not isinstance(design, dict) or not required <= set(design) or set(design)-required-{"symptom_refs", "decision_version", "decision"}:
        raise ValueError("training requires bounded research_design")
    policy = prompt.get("diagnostic_research_policy", {})
    if candidate is not None and policy.get("require_j_decision") and not {"decision", "decision_version"} <= set(design):
        raise ValueError("current J training requires four-part research decision")
    if "decision" in design or "decision_version" in design:
        if design.get("decision_version") != "research_decision_v1":
            raise ValueError("unknown research decision version")
        validate_decision(design.get("decision"), prompt["evidence_projection"])
    if policy.get("design_text_budget"):
        def text_size(value):
            if isinstance(value, str):
                return len(value)
            if isinstance(value, dict):
                return sum(text_size(v) for v in value.values())
            if isinstance(value, list):
                return sum(text_size(v) for v in value)
            return 0
        if text_size(design) > policy["design_text_budget"]:
            raise ValueError("research design exceeds frozen aggregate text budget")
    recipe = design["recipe_id"]
    expected = {"improve": {"RCP-01"}, "ablate": {"RCP-02"}, "simplify": {"RCP-03"}, "diagnose": {"RCP-04", "RCP-05"}}[hypothesis.action_type]
    if recipe not in expected or design["question"] not in ({"overall", "high_volatility"} if recipe == "RCP-01" else {RECIPES[recipe]}):
        raise ValueError("recipe/action/question mismatch")
    if design["basis"] not in {"domain_hypothesis", "visible_evidence"}:
        raise ValueError("unapproved proposal basis")
    for key in ("competing_explanation", "falsification_condition"):
        if not isinstance(design[key], str) or not design[key].strip() or len(design[key]) > 2000:
            raise ValueError("missing bounded research explanation")
    refs = design.get("symptom_refs", [])
    if not isinstance(refs, list) or any(not isinstance(r, str) for r in refs):
        raise ValueError("invalid symptom refs")
    index = EvidenceIndex(prompt["evidence_projection"])
    for ref in refs:
        index.require(ref, "diagnostic")
    if design["basis"] == "visible_evidence" and not refs and not hypothesis.evidence_refs and not hypothesis.based_on_feedback_ids:
        raise ValueError("visible evidence basis has no evidence")
    control_id = hypothesis.control_candidate_id or hypothesis.parent_candidate_id
    control = results[control_id].candidate
    if candidate is None:
        bound = {**deepcopy(design), "symptom_refs":refs, "control_candidate_id":control_id,
                 "execution":"demand_only_no_training"}
        bound["design_hash"] = identity(bound, domain="research-design-v1")
        return bound
    bound = {**deepcopy(design), "symptom_refs": refs, "applicability": "unknown" if not refs else "descriptive_development",
             "parent_candidate_id": hypothesis.parent_candidate_id, "control_candidate_id": control_id,
             "rule": freeze_rule(design["question"], control_id, control.fingerprint, candidate.candidate_id, candidate.fingerprint),
             "invariants": {"model_family": candidate.model_family, "model_params": candidate.model_params,
                            "seed": candidate.seed, "feature_groups": candidate.feature_groups},
             "program_hash": identity(candidate.feature_program.to_dict(), domain="diagnostic-program-v1")}
    if getattr(candidate, "training_policy", None) is not None:
        bound["method_contract"] = {"declared_axis":hypothesis.declared_axis,
            "control_method_identity":control.config_identity,"candidate_method_identity":candidate.config_identity,
            "training_policy":candidate.training_policy.to_dict()}
    bound["design_hash"] = identity(bound, domain="research-design-v1")
    return bound


def _reference_advice(prompt):
    """Finite rule policy actually branches on visible evidence, not relabelled enumeration."""
    from .focused_feature_program import empty_feature_program
    start = prompt["research_start_candidate_id"]
    count = int(prompt["max_hypotheses"])
    previous = prompt["prior_research_results"]
    diagnostics = {}
    for row in prompt["automatic_diagnostics"]:
        if "columns_ref" in row:
            columns = prompt["diagnostic_common_sources"][row["columns_ref"]]
            row = {"candidate_id":row["candidate_id"], "diagnostic_hash":row["diagnostic_hash"],
                   **prompt["diagnostic_common_sources"].get(row.get("constants_ref"), {}),
                   **dict(zip(columns, row["values"], strict=True))}
        diagnostics[row["candidate_id"]] = row
    if previous and prompt["feature_policy"]["arm"] != "one_shot":
        observations = {r["evaluated_candidate_id"]:r for r in prompt.get("observation_feedback", [])}
        # Prefer investigating a declared observation that failed; otherwise the
        # deterministic best actual candidate. This is a finite descriptive rule.
        unexplained = [r for r in previous if observations.get(r["candidate_id"], {}).get("observation_status") == "does_not_meet"]
        parent = min(unexplained or previous, key=lambda r: (r["metrics"]["mae"], r["candidate_id"]))
        features = parent["feature_program"]["features"]
        if not features:
            return {"hypotheses": [{"action_type": "stop", "statement": "No actual generated feature to ablate"}]}
        diag = diagnostics.get(parent["candidate_id"])
        # Constant generated feature -> real simplification, else contribution test.
        stats = diag.get("training_features", []) if diag else []
        if diag and "training_features_ref" in diag:
            stats = prompt["diagnostic_common_sources"][diag["training_features_ref"]]
            if isinstance(stats, dict) and "fold_values" in stats:
                stats = [dict(zip(stats["fold_columns"], row, strict=True)) for row in stats["fold_values"]]
        stats = stats if isinstance(stats, list) else []
        stats = [{**fold, **({"columns":prompt["diagnostic_common_sources"][fold["columns_ref"]]}
                            if "columns_ref" in fold else {})} for fold in stats]
        constant_names = [f["name"] for f in features if stats and all(
            fold.get("generated_variance", {}).get(f["name"],
                dict(zip(fold.get("columns", []), fold.get("variance", []))).get(f["name"])) == 0 for fold in stats)]
        constant = bool(constant_names)
        target_name = constant_names[0] if constant else features[-1]["name"]
        action, recipe = ("simplify", "RCP-03") if constant else ("ablate", "RCP-02")
        refs = ["diagnostic:"+diag["diagnostic_hash"]] if diag else []
        row = {"statement": "Remove the named feature constant in every training fold" if constant else "Test contribution of the actual feature after recorded observation; worse child is not a recommendation",
               "action_type": action, "parent_candidate_id": parent["candidate_id"], "control_candidate_id": parent["candidate_id"],
               "evidence_refs": [parent["candidate_id"]], "research_design": default_design(recipe,
                   basis="visible_evidence" if refs else "domain_hypothesis", symptom_refs=refs)}
        if action == "simplify":
            value = deepcopy(parent["feature_program"])
            value["features"] = [f for f in features if f["name"] != target_name]
            row.update(feature_program=value, simplification_dimension="feature_count")
        else:
            row["ablation_component"] = "generated_feature:"+target_name
        return {"hypotheses": [row]}
    diagnostic = diagnostics.get(start)
    groups = diagnostic.get("volatility_groups") if diagnostic else None
    if diagnostic and "volatility_groups_ref" in diagnostic:
        groups = prompt["diagnostic_common_sources"][diagnostic["volatility_groups_ref"]]
    state_available = isinstance(groups, list)
    enough_group = state_available and sum(g.get("rows_count", len(g.get("rows", []))) for g in groups) >= 30
    relative = diagnostic.get("relative_losses") if diagnostic else None
    if prompt.get("diagnostic_research_policy", {}).get("planning_projection") == "diagnostic_planning_projection_v2":
        # Same group membership and positive global MAE are not a symptom.
        folded = (relative or {}).get("folds", [])
        if relative and "fold_values" in relative:
            facts = prompt.get("diagnostic_common_sources", {}).get(relative.get("facts_ref"), {})
            columns = relative.get("fold_columns") or facts["fold_columns"]
            folded = [dict(zip(columns, row, strict=True)) for row in relative["fold_values"]]
            if "fold_reference" in facts:
                for row, scope in zip(folded, facts["fold_reference"], strict=True):
                    row.update(zip(("fold_id", "group", "rows", "reference_mae"), scope, strict=True))
        weak = [r for r in folded if r["group"] == "high_volatility"
                and r["rows"] >= 10 and r["loss_delta"] is not None and r["loss_delta"] > 0]
        scale = bool(enough_group and len(weak) >= 2)
    else:
        scale = bool(enough_group and diagnostic["residual"]["mae"] > 0)
    expressions = [
        {"op": "safe_divide", "left": {"op": "rolling_mean", "window": 5, "arg": {"op": "input", "name": "return_1"}},
         "right": {"op": "rolling_std", "window": 20, "arg": {"op": "input", "name": "return_1"}}},
        {"op": "rolling_mean", "window": 20, "arg": {"op": "input", "name": "return_1"}},
        {"op": "rolling_std", "window": 5, "arg": {"op": "input", "name": "return_1"}},
        {"op": "rolling_mean", "window": 5, "arg": {"op": "input", "name": "return_1"}},
    ]
    if not scale:
        expressions = expressions[1:]+expressions[:1]
    # A continuation's distinct incumbent already consumed real folds. Keep
    # the approved fit cap; do not emit an unaffordable full batch or add budget.
    from .focused_protocol import FocusedSplitSpec
    remaining = prompt.get('remaining_budget', {}).get('remaining_fit_calls')
    if remaining is not None:
        count = min(count, int(remaining)//FocusedSplitSpec().max_folds)
    if count == 0:
        return {'hypotheses':[{'action_type':'stop', 'statement':'Frozen fit capacity exhausted; retain qualified start'}]}
    hypotheses = []
    for expr in expressions[:count]:
        value = empty_feature_program().to_dict()
        inherited = deepcopy(prompt["fixed_model"]["feature_program"]["features"])
        if len(inherited) >= 2:
            return {"hypotheses": [{"action_type": "stop", "statement": "Frozen feature capacity exhausted"}]}
        value["features"] = inherited + [{"name": "gen_diagnostic_"+str(len(inherited)+1), "expression": expr}]
        refs = ["diagnostic:"+diagnostic["diagnostic_hash"]] if diagnostic else []
        design = default_design("RCP-01", question="high_volatility" if scale and expr["op"] == "safe_divide" else "overall",
                                basis="visible_evidence" if diagnostic else "domain_hypothesis", symptom_refs=refs)
        hypotheses.append({"statement": "Test scale in observed high-volatility development group" if scale else "Domain hypothesis: past returns may contain useful information",
            "parent_candidate_id": start, "evidence_refs": [start], "feature_program": value, "research_design": design})
    return {"hypotheses": hypotheses}


def validate_decision(decision, evidence):
    """Bounded pre-execution judgment fields, not a semantic/causal oracle."""
    from .focused_adaptive import EvidenceIndex
    if not isinstance(decision, dict) or set(decision) != {"visible_basis", "experiment_question", "priority_reason", "feedback_update"}:
        raise ValueError("four bounded research decision parts required")
    basis = decision["visible_basis"]
    if not isinstance(basis, dict) or set(basis) != {"kind", "evidence_refs", "description"} or basis["kind"] not in {"visible_evidence", "domain_hypothesis"}:
        raise ValueError("invalid visible research basis")
    refs = basis["evidence_refs"]
    if not isinstance(refs, list) or len(refs) > 8 or any(not isinstance(r, str) for r in refs):
        raise ValueError("invalid decision evidence refs")
    index = EvidenceIndex(evidence)
    for ref in refs:
        index.require(ref)
    if basis["kind"] == "visible_evidence" and not refs:
        raise ValueError("visible decision basis requires real refs")
    update = decision["feedback_update"]
    if not isinstance(update, dict) or set(update) != {"supports", "weakens", "not_distinguished", "next_step"}:
        raise ValueError("bounded feedback branches required")
    for text in [basis["description"], decision["experiment_question"], decision["priority_reason"], *update.values()]:
        if not isinstance(text, str) or not text.strip() or len(text) > 2000:
            raise ValueError("missing or overlong research judgment")
    return deepcopy(decision)


def _same_program(a, b):
    # Exact ASTs only, no algebraic equivalence or hidden applicability filter.
    return [f["expression"] for f in a["features"]] == [f["expression"] for f in b["features"]]


def diagnostic_advice(prompt):
    """Explicit reference/de-dup/judgment policies on the shared execution floor."""
    policy = prompt.get("diagnostic_research_policy", {})
    support = policy.get("decision_support", "R")  # Legacy pure prompts stay original.
    prior = prompt["prior_research_results"]
    reference = _reference_advice(prompt)
    # Named all-fold constant evidence is a bounded simplification opportunity,
    # not a reason to mechanically add a second feature.
    answer = reference if reference["hypotheses"][0].get("action_type") in {"simplify", "stop"} else None
    if answer is None and support == "J" and prior and prompt["feature_policy"]["arm"] != "one_shot":
        parent = min(prior, key=lambda r:(r["metrics"]["mae"], r["candidate_id"]))
        features = parent["feature_program"]["features"]
        # A local failed expression is not globally disproven. An already
        # completed B is a valid single control for B+A, never batch-future B.
        if len(features) == 1 and prompt.get("remaining_budget", {}).get("remaining_fit_calls", 4) >= 4:
            alternatives = [f["expression"] for r in prior if r["candidate_id"] != parent["candidate_id"]
                            for f in r["feature_program"]["features"]]
            alternatives += [{"op":"rolling_mean", "window":w, "arg":{"op":"input", "name":"return_1"}} for w in (5,20,10)]
            for expression in alternatives:
                if expression == features[0]["expression"]:
                    continue
                value = deepcopy(parent["feature_program"])
                name = next(f"gen_conditional_{i}" for i in range(2, 10)
                            if f"gen_conditional_{i}" not in {f["name"] for f in features})
                value["features"].append({"name":name, "expression":expression})
                if any(_same_program(value, r["feature_program"]) for r in prior):
                    continue
                answer = {"hypotheses":[{"action_type":"improve", "statement":"Test an unanswered conditional expression; local failure does not establish another cause",
                    "parent_candidate_id":parent["candidate_id"], "control_candidate_id":parent["candidate_id"],
                    "evidence_refs":[parent["candidate_id"]], "feature_program":value,
                    "research_design":default_design("RCP-01", basis="visible_evidence")}]}
                break
    if answer is None:
        answer = reference
    if support in {"D", "J"} and prior:
        for row in answer["hypotheses"]:
            if row.get("action_type") not in {"ablate", "simplify"}:
                continue
            parent = next((r for r in prior if r["candidate_id"] == row["parent_candidate_id"]), None)
            if not parent:
                continue
            target = row.get("feature_program")
            if target is None:
                target = deepcopy(parent["feature_program"])
                component = row["ablation_component"].split(":",1)[1]
                target["features"] = [f for f in target["features"] if f["name"] != component]
            available = [r["feature_program"] for r in prior]
            if "fixed_model" in prompt:
                available.append(prompt["fixed_model"]["feature_program"])
            if any(_same_program(target, p) for p in available):
                return {"hypotheses":[{"action_type":"stop", "statement":"Remaining reverse comparison is already visible; no suitable unanswered finite experiment. No extra request or fit."}]}
    if support == "J":
        if prompt['feature_policy']['arm'] == 'one_shot':
            next_step = 'Whole plan frozen: no feedback replanning; deterministic terminal summary only, no further Advisor call'
        elif prompt.get('round_index', 1) >= 2:
            next_step = 'Final decision: deterministic factual summary only; unresolved causes remain unknown, no third Advisor call'
        else:
            next_step = 'Use actual first-round feedback in the remaining second decision; no extra planning allowance'
        for row in answer["hypotheses"]:
            design = row.get("research_design")
            if not design:
                continue
            refs = list(dict.fromkeys([*design.get("symptom_refs", []), *row.get("evidence_refs", [])])) if design["basis"] == "visible_evidence" else []
            facts = next((r for r in prior if r["candidate_id"] == row.get("control_candidate_id")), None)
            design.update(decision_version="research_decision_v1", decision={
                "visible_basis":{"kind":"visible_evidence" if refs else "domain_hypothesis", "evidence_refs":refs,
                    "description":f"Completed control MAE={facts['metrics']['mae']}; local result only" if facts else "Visible diagnosis if supplied; otherwise an explicitly unverified domain hypothesis"},
                "experiment_question":f"{design['question']}: compare actual child with its completed single control under frozen conditions",
                "priority_reason":"Prefer an unanswered finite comparison over returning to the known start; no estimated success probability. Frozen remaining fits="+str(prompt.get('remaining_budget',{}).get('remaining_fit_calls','unknown')),
                "feedback_update":{"supports":"Only a meets observation supports this local pipeline question",
                    "weakens":"Does-not-meet weakens this local attempt, not every use of the feature",
                    "not_distinguished":"Noise, expression limits and training distribution remain competing explanations",
                    "next_step":next_step}})
    return answer

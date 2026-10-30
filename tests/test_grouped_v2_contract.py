"""V2 separates field roles; original V1 raw bytes retain their own decoder.

The compressed constants below are exact local snapshots of two real V1 prompt,
raw-envelope, and canonical-input files. They are not repaired answers or new
success fixtures. Every byte identity is checked before parsing, independently
of whether the ignored original evidence directory is available.
"""
import base64
import hashlib
import json
import zlib
from copy import deepcopy

import pytest
from evidence_repair_materials import build_case, validate_response
from jsonschema import Draft202012Validator

from finance_forecast_agent import grouped_decision as mod
from finance_forecast_agent.focused_identity import identity
from finance_forecast_agent.focused_methods import restore_method_references
from finance_forecast_agent.llm_adapters import _parse_json_object

V1_SNAPSHOTS = {
    '1_prompt': ('8fa1772ee617166e8b61c8094ae3a499a42d97c3f23acb126b9a1dfe8942028c',
        (
        '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'
        'LxWJ/yc0zAY6XNWDHFsN/ovZG5+8QjIXMDv5yky4g4R4fMMwnyLLlrhigS2VChxbKMc5LKBmqcSUmWIBWRwcW6GL5vmY8Jf4Yg4O'
        'bhDnr7q4tWtnPw/nlkT5qCbWz7SKxy6cmTlypnA631EVa/zocYad6+jHaqfEmdVSa230/OE0zs3uHuemewUSOfdkhZkdXbJWxqWz'
        'h8f4g7Oj03VmnBk9ckSqrxRXjcrBtcrs2rB5vHC6sce5Ezl3HNP1ODezx7l3mHNn5dSxvmySVSdUemSsmakwFRYJIaZQYMrleNZc'
        'LlTALK9wXIUtlfO/Zs48O3FI0w8JSr7BnWpp7bHFs0Kp3a4Od7rNqTV+8ejJNev08frJ0pK2nMaZuV3kzBVuUM6ssa3T7bnx4eOl'
        'oyel0cPHL0yoE1qdacwcX6ytLepnGtVu+cyYwKqcuceZ9zjzHmfeXc6cL4LCnM+XypVCoVJM4syFIleCemVgzYXqr5gzy51VrSye'
        'aI6e0MzqyszBgy3m1KhxfK10etSsjxvi+Gx+7nipWz86rqdx5vzucWa67zmRM9c7pUqhPXNu+fRopXjy3FJhcrq6KldGzzTLzFzZ'
        '4phjF1YbcxeqE0t7OvMeZ97jzLvKmQvVYr7IlArAlvNMvsQmcOZ8niuWKhWmypYq+Wpht1lz6vPJFKIj6IQrlKMfYxyCQeLgilzk'
        '+2C4vsWTjyz+sjRPWcLxh01y5BsQm/hwT2y5yJbYch79x3KVQlpT+8yF9nTLfrem4Si7pX3Uj6blHGXl0ds7tlBiq1yRYbiIXMmp'
        'Qnxf+JvXFVNiS6VitZAvc9BZpRLA1Yu04MmhkDODveUKRJwjWVfOPoYi39XjkFjonEoVwmkSKK/WUK0DjC02Txrtc0vyaU4+eOZY'
        'fqp1+AioDseb0+cOz54wz1TLh6YvTE2VpteOSUuVdVokRz+DKxFizr7sF5MZDz3iDzGP8AaHEmjleq9/0nvvs95/X+2/+Un/vUsP'
        'P7naf+vdB/e/enD/Wu/6vc1nf9j86L2HL7y0cf+V/ttvRpDezZiV2/zxld7lD3qXv9z48n7/yq3Ne/d6X9/tXXm+982zdje9Hz7v'
        'vXKt9/mlh89+3L/1bf/LV/uvXqF2SabLym3c+aZ34+qD+/d7L737j0vP9C5/Dj837tztv/MCzLn39Rf9lz/oXb/du3sVBVd6+aPe'
        'la8oPQayZD0V4Uw2tkQDIITyVeWWko47xXCsTrtCMH1UdGz/fJaNwfl5Cmqg3JB2VKHYKJ+ToeUkBpemRGqNSQ0CQAhHUAik5Ait'
        '0E2qkevf/BYFxnr+PsKk2x/0b361ceelh39+rv/3P9joEJotFeLB5BC5/psvPnz9BnSycfd27/nLgGg2Bm+8c3PjL1+FT3mp76Ai'
        'j5ajW5ocuj0x1pUbJdPCkYbICJl2ka9iH75Qai9MT08LbW6GPbtUnTl/VpUr3YWaZh0S2OmKOnaEWzs005xskgeK6FKpiWI5A38i'
        'goK4Dx8vEmFm3Ih1otAWaqErwrlaR1EtHLMTRTomF2O2V+1rD7xbh4hT5fflraRYYqQiWwapWpHEGvyQ8lKZE/NVpoaCdYmMLIty'
        'VcxXqpVCvs6JpUKtIItFLl+uVPKFQp3Wt8PMvZm4kXUCU9FbLaDTZcFodVDQoVKB+NIG7dMgV2X3g6PTkl1oIOCcGNwO3UZ025zk'
        'RsV3gvR6zRsySCC7sR9VPyBIJKGNDZiaYOFwLkQYe12TeVD+iAyYnmSz7ySQQe8QJEK3GiTQK8gXtDkc9YvgDr6a6I/qy2sifjHH'
        'hELyoXCFCIboJWlt1Q4Wnc8Xi6B+cmQdSW7jPDYFslBekUUcnjeyaPyZiJEUKF8wUQtnMLaUrwQ6VXV90QlbWwp80HTJaUGWogwf'
        'ugnqoanqWJIG2rhXmNAUGCLCO8oKIlh2DEI/2BqANRiOCMffb8mCRilG2g0hzSUpELSoZu8nETS3A/TVDoRCE2pk6DZTqKO7O4jO'
        'wyHK3YCQNjfC6BmMUEniBhRZuujcwXGqEZH2u2Rddy1gDzQ0J3xvDvTtpsUrGjK0cUTGsHblNJIkvU6GdvfgBWzEV0FzdTCq+GVF'
        'k/RlPwygv1ZebpuKaotIeZip0KqgSOBEkApMMyZ6AQ3r0XjVcvvg12RD52XV9ADpxwc0WsiICAXXc4MmhOBtzzZQN5WuvD9LTDQK'
        'mLddkbQJBtavQszDnYdPXygwOG8qa3KYlkhmxGWjCy+4M2Z/XuC0HK6I454TUeU5yioMuaGYlhEQMV4sQgp87cgT+2jFHL04Ty8u'
        '0IuLuUic0aWOItlC0J9NF0W+lx3DKrrpLR0RQDDRj1fIk8G3vUKOCXcSeKITGNo1zsiOiGK/KxLg+AodjkyM9Qgn0mzOj4OFrZnc'
        'qKoOabA2kHtDrqIwpJhDtgGD0EYaEjRpyGH00r4haDnUEoxF2RoiQu6bQ7oxBGyrI6hDeNShumJ5z9T3D401dRBH0NWQoIK9D72i'
        'a3pDIKna/wldDqGrf+aQYMhDNubil+vGkNWEuUCJAVglO6HZMI4GDB3OKbejCWSIsI0Cvtp2ycv3H75w7Z/fv+G0xYkDoGH/Tx+g'
        'P1EUVueLvNI2vDuF6LtfYNpRWUdPnvrn91c3Xvy29+MzvRvXHvz01sarr//j0u9jQ/Nuvgt20ccPX3/flXa992+hgmc/ht7seKz+'
        '+HboTzT01RfJgFAj6N4iCmrrpamwX8ePgCqjGz77dosJxIC59a/fePDd+7aRNGnPYs6eJ1rKh8/0vn914+bHD354c/zkNA5y+1nv'
        '0vcwR3txUMep8M213p/ftq2s/lvPgu5Nho0lIBWIsYr5lwt4avjXfC4sx2zoBfWnJhOyRCjq5/rUmQZ7Qhw9ObPKjUtz56bHF6dX'
        'S/XRslkSZ480xyvmhelT5ukF+fDMRPDK4YAKp78yiqCNc1JgXAvAJhTtdn2qMs0ct2ZWWqtHhLPF8toRaXFliS/UmGXlUPGIVSiz'
        '3cnV/MG1yWXFXCfD0bvYFxEfK6FwsZ7KRYTRd4MzOzI4xLFQDJ06DlSjOdli8P5hKeBbUnUyyUucbgcwqiNPsL/eduXQydPL5Vbr'
        '8LnGucWZ4Qvtk7PnJ9XJYr4rCSvMCam9fHqh3a6Ux327x+vG3yd3E+wV0BQYIrSpB4wi4fsrF0uhdXfaTjhzlCEAZAJGR67AhL4r'
        'ocSxbrnDlwqh4lBOIc7XOJdlpFY5sYJBnKOEQOQW0ymdFivUjusdNtyjYcUIM1Z3IlsSLgZcEhCooZQwRNhWMsNLOGQrDtiaWx8j'
        'zdZgPNZoNFbkFkH36yNpLZYDoWnJCJyeOuMn6aJdfSdysnntBgs3aYKGrdl5rLCQdfoxoNgmI293PZnURB5YJ0OZE43K0wdxDicN'
        'm1iqbIVqMQGKIj4EbS+UBc2TFraGZqBXC2GVDxcGkNWftSB1FVM3vBHYaBVyAiylC697lkBbPyOYY3Y4ZBt1k7hUmyMdJ0Yom0Hw'
        'PNePBx1wfzjf8MMN4Ajyiq89uDzYQeQcyFm9YyET27adkMLwwncPb3/au3HlyMnZmX9ceubBN5/2b72w8adPe9c/AOlox40f6b/9'
        'xoNvfgSRuHnvjyiw+ktIfvauPN+/ea9347nelduOjP/pcu/dvz68eZcUlZ5vbcRXcFDA9j+//fCF6zCEHZP9qXmQvP3bH2289FX/'
        '0jMgf23XVP+VazASEtM3v9346I+9Tz+0A7k/fPc+TuZk/QcLY2385Ts7zH3v8pXee5/1X3v5wY93es9/ufHpLVuYk/PxbISHl25s'
        '3H/Orr/xxY8b797dePEKdAJQAPteht0FsoAfbuq53n9ftc/aTOjOLYRONu890792939v261hrjCdBz++tfn3W2hpl6+BNtR/8RLM'
        'Aio4vswRAFz/6jMjvesA0WfI2fVvfda78n7/1qcIkD/cgN6i6etA1etffQFF9b/3df/z3/e+/sL7tPHGc/ZSbO809CwhLcRAja45'
        'gyNo3n4HKtgx82GGm/eeQykDYLbffwcd2l5wpLDdeYecm7vm/X603d6bHyMf9f3n/L3tPX8ZRnBQ5PLnsG67hg2eERK0v+9dv+eA'
        '9Mmn5nvXP4GJ9C5/1bv7LFRGnVz+GPnRv7tp99a/dB+0NXb//qC2TE5x895LADuEPh18gWDEU8JGUKS4EewYHcFB00bsyHIjTlg6'
        'GM6r+yTiur1rr/bufbv5+btIJbzxYe/K606fyE1/71uvMgw/fpwpAm15Rb073/XuvgH0ActGra9/8vD23d7XoBp/jQ4IfrrZu4OQ'
        'n5z4mK2wOqeoI5MPvvtD7+7bIxMb398CmgN0AhSz0zp4+44Q//5H/Rd/chrBMEAlD765tPnD32A1rk7Sf/PSxv0rdvdAqZvvfvzE'
        'kxzC0k9u966/50VHH0Fr7l+55egQI6Av/A70BKgIRgAsTsCZilByIHLaiAT3+z7x3vVbMFzvsz8iGF3+cuLBNzefeLKC+MjdHzfv'
        'vtu78VcwTXrvX7MjDPSuvwSo1n/7xuFxwFugakTBN65AxSeeRAkIMeCfs62GJ57Mcwz8ufE/HwbI5R20F44Of+1de8NG8AHZyObV'
        'Z3t3/jbSf/kvG+8Aqb11vf/SayO9z6733/naptPepzc2P3q+dwcxtv5r91C6ix9egd7deAooS8a9mw9+/AMwARAzIqh+ULTx+o+I'
        '8736GWJYeODNn154ePtjzB2fAV7Sf/M7sBlG+q/9uPnH2yMbf/ifjb/+wXb+j2zcudK78hdyAaalt10U5G0GDy16194BRLEtkv6b'
        'nwArQ4bNvetjzpkfUEKeAwkFAN38+9cbv/92BFa+cfmjkd77n2/+DTFu4CP2UUMBqo0gMN19e+P7V3qfvsZAAUwdJVywetc/BGij'
        'PXZcLoAa/3ubg/XOavIwctI+8WSh/9EP5IzBhAIrb+PTmyP9K58AsY08/PNbyMq7fq1/6S1AoKlTp+ZGgOT7L36Ljtne+sBmwSMP'
        '37ixefv64fERhKT4jAuo/cH9r0c2v3oJDCybPNCuvPynh59cBVD2Xv94871n7LXnCOXHtIyOiFAb1AdZlhzvqCsIcX6EA372A6Qx'
        'ezLWZxq+AEYNSJezq8iEc4jl7Idyjlw+OXee4pjyjghBn5VFRDKBVJJAbLqJtKio8uVnxCKtD+zq9vmvbihrTmAOnCLTELBLUvLz'
        '/OYUzc+tCZPS6zhJslC3ZGPIGsIOdOQLiTxYdJ4cBu//CNKC7XN/CuTs/NDIEFEwPzQ85FseGIi+iWK76DXbZYE9U77iwwUbuUcM'
        'Xr1wbg+7GqHfQg9Y5fr3f7v4/wFOrEov'
        )
    ),
    '1_raw': ('4cb7475a420bb23d1e294923e6fee86b60a4ceae16cf172b4389188eda57c556',
        (
        'eNqNVd1O41YQvl9p3wH5miDbsfOzUi960d71CQiyjM+YuOvYqY/JghBS2G7aiA2IaoHSTdrSdlnQdiEgKgiE3T7M5pyEK16hYztO'
        'HFTUJjc5M9+ZOfPNN5OVx4+mpoR5lywLT6ZWggMejaJrGUDRMhtZpmJX6DYtx6JFzQOdug6CBOq7ZWE6gbAcAkvoEZNG210oe+58'
        'ENZZtO2kqwSU6gswfsLQbriOD44f5FgpCNQoQknXKuBRy3UKwpOCABWLgGOARsCwAqtWSReE6YLwzSJQH88UYbNzaCgul12/CBRC'
        'y8rYYIUGPEt4UQqg1Nf9RRrG1w3fqkBBWA3sES3DukP3l1Kvc8226ry+NWiv893ju5vXhlsq656FkF5nE0N5fv/1i68+/4L9/D2C'
        'xRlRvrtpKHx9j9WO2NU5Htjpx9tvj3rdmjr4rdHrbPc+bPLtNm+soa/f7LDaOa8eijP5NEIwRJyp0T/8gR2/jaC89Y51r/t/vry7'
        'afY6G4OL8173YOjavhr83eT13f5JlTV28SLfqWGoQftF7+a0KLGri0H7kp89Z282+H7nU/V5yGDM6H2+IgLHhM2F2DI4hGohLbMB'
        'LwUhJF13iG05C/9JedzHIavhA3SKuWgJ+x9aLYcumqZlWGjQxngEoh5JlKQg3NY2WPsqoPvyBLn+VF1LUt2MqHY+UxMcNyc5RvLa'
        'a3xvk7euWf0iZsPFArVYVGEm1jrizb/Ym8MoJt+/5K332PL+y/fYBkza66wj14OPr1jtAOP3z7t8r8223rIPZ+zVBjurBrd2r/j5'
        'Dt+p819adze/RsRbtOxSa5SIgAmeB2SowkCS465EpxDnQfg+1GfFgmdhqIRUg6I2TkZyvScz/uM+voM1sOTviijqTfbTO/bHKZJz'
        '26r2rq/Z5UGkjqiEfvew3z0OJNWt8+PfQ5JW5/Cb3AI4v1F+7I2WmOT7GNcOBj9ot4XjgpixezX+OfwxNx1vKIzsA8F7UjaflrOi'
        'qKixzwrMOKy6b5TKdsowQcqlzWxKyYtKKi/mzJQOJklJGZ3IaVEU5bQaP0kouQTs4DoBKFOAp6mKMiOlTFunxZQkStkR0p3/Ggw/'
        'zjQTTL0NQS9GiMX7K00YgzTffQpOsAplRZ5+GIB7zdctm05uRsGHJX8ixIincSzctaVyAiVJeUV5wP1AGkPHjUvGISbWuVXC8h7w'
        'Tb4vzPwvL/RdX7cTMFnKZSJn2O4IKYCtYyeIRgE1RMJ6ZxRZlMVsPvioeTGfiZBF0Al4k0AMmc7I2GUpJ8vZJC5RrLCUGg5Paiie'
        '/6OZxBtx4VPQcEpdD6+buk0hcnj6M5xHnGcH/UUUUaj0XKBXUEBVISOZpgGSJEFOFY1MNpPJK8TMy0QFOaOmVZ0o0jwopqFIoprL'
        'SdksSQvD2HHc+WU//LOWFHFYYfQPFjAgio8frf4D73z2XA=='
        )
    ),
    '1_canonical_input': ('29ee4c982a06486c67fe2f40a01f50ecd8d7e3c5970df1a59b77eea265eae41d',
        (
        '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'
        )
    ),
    '2_prompt': ('e86d29338f750de2a15833ff4055f462945f69e7e1f6f76ac70bbf59acb3c10b',
        (
        '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'
        )
    ),
    '2_raw': ('e6790ccc3e112c7a1c328fc26a5043f894c075f0dfc7fe4da04351d6e9404f73',
        (
        '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'
        )
    ),
    '2_canonical_input': ('d64af6729f3c0a5e9a766c6f3226036fa1ccaf3fe17f7898b9c31ffc2ad16e0e',
        (
        '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'
        )
    ),
}


def frozen(name):
    digest,encoded=V1_SNAPSHOTS[name]
    raw=zlib.decompress(base64.b64decode(encoded))
    assert hashlib.sha256(raw).hexdigest()==digest
    return raw,json.loads(raw)


@pytest.fixture(scope='module')
def prompt():
    return mod.prepare_prompt(build_case(0,0,'authored-grouped-v2-role-boundary'))


def authored_review(p):
    facts=p['compact_decision_contract']['bindings']['facts'];fact=next(iter(facts))
    return {'schema_version':mod.WIRE,'question_updates':[],'hypothesis_updates':[],
        'choice_reason':'合成工程用例，仅记录证据不足，不补造研究结论。',
        'decisions':[{'selected_versions':[['h1',1]],'fact_dependencies':[fact],
            'handling':[{'hypothesis':['h1',1],'fact':fact,
                'assessment':'insufficient_evidence','finding':'当前事实不能区分机制。',
                'open_question':'需要实际干预或保持暂缓。','disposition':'deferred'}],
            'actions':[{'action':'request_review','reason':'保留未决问题，停止新增计算。'}]}]}


def test_v2_frozen_contract_uses_disjoint_names_without_scientific_completion(prompt):
    c=restore_method_references(prompt)['compact_decision_contract']
    assert c['schema_version']==mod.CONTRACT=='grouped_decision_contract_v2'
    assert mod.LEGACY_CONTRACT=='grouped_decision_contract_v1'
    schema=c['output_schema'];raw=authored_review(prompt);before=deepcopy((prompt,raw))
    assert Draft202012Validator(schema).is_valid(raw)
    canonical,binding=mod.expand_decision(raw,prompt)
    assert validate_response(canonical,build_case(0,0,'authored-grouped-v2-role-boundary'))['actions']==['request_review']
    assert (prompt,raw)==before
    assert canonical['research_update']['evidence_assessments'][0]['finding']==raw['decisions'][0]['handling'][0]['finding']
    assert binding['raw_response_hash']==identity(raw,domain='grouped-response-v1')
    assert binding['schema_version']=='grouped_decision_binding_v2'
    assert binding['contract_version']==mod.CONTRACT


def test_status_update_object_cannot_be_copied_into_selected_exact_version_pair(prompt):
    raw=authored_review(prompt)
    status={'hypothesis':['h1',1],'status':'active'}
    raw['hypothesis_updates']=[status]
    raw['decisions'][0]['selected_versions']=[deepcopy(status)]
    before=deepcopy(raw)
    with pytest.raises(ValueError) as caught:mod.expand_decision(raw,prompt)
    assert caught.value.validation_issues[0]['path']=='$.decisions.0.selected_versions.0'
    assert raw==before
    raw=authored_review(prompt);raw['hypothesis_updates']=[status]
    canonical,_=mod.expand_decision(raw,prompt)
    assert canonical['research_update']['hypotheses'][0]['id']=='h1'
    assert canonical['research_update']['hypotheses'][0]['claim']==restore_method_references(prompt)['evidence_research']['state']['hypotheses']['h1'][0]['claim']


@pytest.mark.parametrize('where',['question_basis','hypothesis_support','hypothesis_counter','dependencies','handling'])
def test_experiment_E_handles_are_rejected_in_every_fact_namespace(prompt,where):
    raw=authored_review(prompt);d=raw['decisions'][0];e=next(iter(prompt['compact_decision_contract']['bindings']['evidence']))
    if where=='question_basis':
        raw['question_updates']=[{'id':'new_q','goal':'合成问题。','scope':'development_only',
            'basis_facts':[e],'importance':'保留边界。','status':'active'}]
    elif where in {'hypothesis_support','hypothesis_counter'}:
        raw['hypothesis_updates']=[{'id':'new_h','version':1,'question_id':'q','claim':'合成机制仍待区分。',
            'conditions':'相同任务。','support_facts':[e] if where=='hypothesis_support' else [],
            'counter_facts':[e] if where=='hypothesis_counter' else [],'alternatives':'可能为噪声。','status':'active'}]
    elif where=='dependencies':d['fact_dependencies']=[e]
    else:d['handling'][0]['fact']=e
    before=deepcopy(raw)
    with pytest.raises(ValueError) as caught:mod.expand_decision(raw,prompt)
    assert caught.value.validation_issues[0]['code']=='invalid_enum'
    assert raw==before


def test_full_question_and_hypothesis_fact_fields_project_exactly(prompt):
    raw=authored_review(prompt);f=next(iter(prompt['compact_decision_contract']['bindings']['facts']))
    raw['question_updates']=[{'id':'new_q','goal':'合成待检验问题。','scope':'development_only',
        'basis_facts':[f],'importance':'有限预算内检验。','status':'active'}]
    raw['hypothesis_updates']=[{'id':'new_h','version':1,'question_id':'new_q','claim':'此开发事实不识别机制。',
        'conditions':'相同任务与完整控制。','support_facts':[f],'counter_facts':[],
        'alternatives':'可能由噪声解释。','status':'active'}]
    raw['decisions'][0]['selected_versions']=[['new_h',1]]
    raw['decisions'][0]['handling'][0]['hypothesis']=['new_h',1]
    before=deepcopy(raw);canonical,_=mod.expand_decision(raw,prompt)
    fact_id=restore_method_references(prompt)['compact_decision_contract']['bindings']['facts'][f]
    assert canonical['research_update']['questions'][0]['basis_refs']==[fact_id]
    assert canonical['research_update']['hypotheses'][0]['support_refs']==[fact_id]
    assert canonical['research_update']['hypotheses'][0]['counter_refs']==[]
    assert canonical['hypotheses'][0]['hypothesis_refs']==[['new_h',1]]
    assert raw==before


def test_same_subject_reference_remains_rejected_without_auto_null_correction(prompt):
    raw=authored_review(prompt);d=raw['decisions'][0]
    d['actions']=[{'action':'diagnose','reason':'合成诊断边界。','subject':'C1','reference':'C1',
        'kind':'DQ-05','scope':'development_oof','pairs':[],'factor':None,
        'request':{'question':'请求原工具返回的分组n和MAE。','expected':'描述不证明机制。',
            'branches':{'supports':'保留描述。','weakens':'保留反例。','insufficient':'暂缓。','next_step':'停止。'}}}]
    before=deepcopy(raw)
    with pytest.raises(ValueError):mod.expand_decision(raw,prompt)
    assert raw==before


def test_V1_valid_and_rejected_original_raw_keep_exact_bytes_and_original_decoder():
    for number in (1,2):
        prompt_bytes,p=frozen(f'{number}_prompt');raw_bytes,envelope=frozen(f'{number}_raw')
        _,canonical_input=frozen(f'{number}_canonical_input')
        assert restore_method_references(p)['compact_decision_contract']['schema_version']=='grouped_decision_contract_v1'
        raw=_parse_json_object(envelope['body']['choices'][0]['message']['content']);before=deepcopy((p,raw))
        assert mod.prepare_prompt(p)==p
        if number==1:
            canonical,binding=mod.expand_decision(raw,p)
            assert validate_response(canonical,canonical_input)['actions']==['request_review']
            assert binding['raw_response_hash']==identity(raw,domain='grouped-response-v1')
        else:
            with pytest.raises(ValueError) as caught:mod.expand_decision(raw,p)
            assert str(caught.value)=='grouped response field $.decisions.0.hypotheses.0: type'
            assert caught.value.validation_issues==[{'path':'$.decisions.0.hypotheses.0','code':'invalid_type'}]
        assert (p,raw)==before
        assert hashlib.sha256(prompt_bytes).hexdigest()==V1_SNAPSHOTS[f'{number}_prompt'][0]
        assert hashlib.sha256(raw_bytes).hexdigest()==V1_SNAPSHOTS[f'{number}_raw'][0]



def test_experiment_refs_are_explicit_E_only_and_project_to_original_design(prompt):
    raw=authored_review(prompt);c=prompt['compact_decision_contract'];e=next(iter(c['bindings']['evidence']))
    action={'action':'improve','reason':'合成窗口干预。','control':'C1',
        'change':{'axis':'training_window','policy':{'mode':'rolling','sessions':756}},
        'metric_scope':'overall','test':{'basis_kind':'visible_evidence','experiment_refs':[e],
            'question':'窗口改动是否改变配对开发MAE？','expected':'保留数值与反证。',
            'alternative':'差异可能是噪声。','falsifier':'改善未满足冻结规则。',
            'branches':{'supports':'保留局部支持。','weakens':'保留反证。','insufficient':'暂缓。','next_step':'停止或继续获准研究。'}}}
    raw['decisions'][0]['actions']=[action];before=deepcopy(raw)
    canonical,_=mod.expand_decision(raw,prompt)
    assert canonical['hypotheses'][0]['research_design']['decision']['visible_basis']['evidence_refs']==[c['bindings']['evidence'][e]]
    assert raw==before
    raw['decisions'][0]['actions'][0]['test']['experiment_refs']=[next(iter(c['bindings']['facts']))]
    before=deepcopy(raw)
    with pytest.raises(ValueError):mod.expand_decision(raw,prompt)
    assert raw==before


def test_numeric_facets_preserve_pair_direction_and_single_subview_scope():
    from grouped_decision_materials import prepare_numeric_cases

    from finance_forecast_agent.decision_facts import quantitative_fact_cards

    source=prepare_numeric_cases()[0]['payload'];p=mod.prepare_prompt(source)
    c=restore_method_references(p)['compact_decision_contract'];sentences=c['numeric_facts']
    wire_views=[dict(zip(sentences['views']['columns'],r,strict=True)) for r in sentences['views']['rows']]
    pair_aid=next(r for r in wire_views if r['type']=='paired_mae')
    assert pair_aid['subject']=='comparison' and pair_aid['reference']=='start'
    assert '0.025=2.5%' in pair_aid['statement'] and '0.0025=0.25%' in pair_aid['statement']
    assert '改善3、变差1、持平0、未知0' in pair_aid['statement']
    assert '不代表完整筛选通过' in pair_aid['statement']
    single_aid=next(r for r in wire_views if r['type']=='single_group_mae')
    assert single_aid['subject']=='start' and single_aid['reference'] is None
    assert single_aid['scope']=='development_oof'
    assert '无参照对象' in single_aid['statement'] and '未提供配对组差/相对改善' in single_aid['statement']
    # Check the full numeric projection and source path independently of the
    # Provider's smaller Chinese reading aid; no interpretation is filled in.
    cards=quantitative_fact_cards(source,c['bindings'])
    pair=next(v for card in cards for v in card['views'] if v['type']=='paired_mae')
    assert pair['relative_improvement']==pytest.approx(.025)
    assert pair['improvement_percent']==pytest.approx(2.5)
    assert pair['threshold_ratio']==.0025 and pair['threshold_percent']==.25
    assert pair['relative_threshold_met'] is True
    assert pair['fold_directions']=={'improved':3,'worsened':1,'flat':0,'unknown':0}
    single=next(v for card in cards for v in card['views'] if v['type']=='single_group_mae')
    assert single['path']==['result','groups','results',0,'group_losses']
    assert all(card['scientific_support']=='not_established' for card in cards)
    reverse={cid:handle for handle,cid in c['bindings']['controls'].items()}
    raw=authored_review(p)
    raw['decisions'][0]['actions']=[{'action':'diagnose','reason':'使用明确对象与方向读取原配对损失。',
        'subject':reverse['comparison'],'reference':reverse['start'],'kind':'DQ-02',
        'scope':'development_oof','pairs':[],'factor':None,'request':{
            'question':'读取comparison减start的绝对损失差。','expected':'返回数值不证明机制。',
            'branches':{'supports':'保留描述。','weakens':'保留反例。','insufficient':'暂缓。','next_step':'停止。'}}}]
    canonical,_=mod.expand_decision(raw,p)
    assert canonical['hypotheses'][0]['evidence_request']['query']['object_ids']==['comparison','start']

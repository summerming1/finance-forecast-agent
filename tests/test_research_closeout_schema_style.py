"""Readable new schemas and frozen legacy wire bytes; fake HTTP only.

The compressed legacy request is the exact sealed V2 call-02 prompt, not a
repaired answer. Artificial serializer boundary tests prove style dispatch only;
they are explicitly not the full worker's real joint-capacity evidence.
"""
import base64
import hashlib
import json
import zlib
from copy import deepcopy

import pytest
from evidence_repair_materials import build_case
from jsonschema import Draft202012Validator
from test_grouped_schema_projection import _actions
from test_research_closeout_contract import cold_source, declare, raw_diagnose

from finance_forecast_agent import grouped_decision as grouped
from finance_forecast_agent import llm_adapters as llm

LEGACY_REQUEST_SHA256 = '89686e1f41774640661d3e2a894e51f10ba25f65f42bddf93cbc23b0826713bc'
LEGACY_REQUEST_ZLIB_B64 = (
    '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'
    '86GfHJqKspHpBCZmYDSdXP7jydd/evT2lerFByMwp+P7L/WDtsEn1RU2NtacSYWajX1vQ6d5sE8KOKeYVW/oVG99Xb3zTtgZOTuh'
    'UhfK5s6csoOkP+iWjC3+q9feqN796uQvH4LceHTpGvy7+uWd7x/cOvnu9eqt3zy6fOPh/Y+r199XDSsvF5W0Vjh+56XmTnTt9S9q'
    '1+48vPd19fLL/3Xx5+7wn9nutgcqiQB10NxV9qMvK1u7kmWWCorWAfgNClDhr7MZ/iyBMoVHKGaEYr9/8I6z2OrlGw42/4Oq3foc'
    'VuxVPW2KpQ0vQbojIHkwUv3yr7XrH1dvvFV75fbJh1cdgEW6J+r5FfuFc70mgntPpHbx/sNvfjXy6OLN2qtv1+68Bms+vv/+yZ0P'
    'I22phZG50XjA0+qNq3VKcXfl0Mzx/ffgryP6h746OsTqrl4Gpqze+qD66U2YyKImFyw/t9kNV/LwKivnvn9wpfrVF9Urb1W/+lv1'
    'vcvHt//w/YNXghZ9/f3q7ddGau++Unvjykjt+n8++vVHQf2efPfL6r17tTc+G3n4zfXa63drV1+sfXD55M5nQ4cG0xsaDmaqn337'
    '6BefjFQvfVG984vcw3vXg9G6R6GRPVGsC/0uaPf056C9ruu97FP/rj841IWrY4PWp/Tw3se1Dx4cv3G1+tGbkf6AxIYG0qVPyKIe'
    '/ent2t9+W321N7j8XOBop765oKFMXr5/fP9XztBtei7MQrn+eKN25c1Hv32p9vfXYH3Ht+4Aav6BWSVAxfmdyFwpqxXAaWmLG5Fb'
    'odJmwSge2Erw5tWH9y7CAhKg3WBmwAmP3r50cvf+ybeXqq/Ceq8+eu83tTc/O7n7IojvkePbv6x++vvqlY9qb34KC/3k5NpN0Ji2'
    'R0U2MJ5LPAugPrn9cvXWt9WvQdF8CR3oZkaVDJXoyuvvE8Kzn5I1nXz4yfFHX8MAoIrhhVePBgW8OulR0tanMc0K+LG+Z7a67aA+'
    'w2i+RJvaI5sHlmEVwc+LIlGkdIVmZSzoSazpDMOqHIWSbd+0XMo+SD6Bn+DY9BMcm3mCY7NPcGzuCY7NP8GxhaGM3Qhx9TOy+MRG'
    'RtSTGxo9uaHxkxuafnJDM2c4dJBh4I58prWs7L6okihOyYKBSbjRksrulKCyoVVOoYCbRoHvefEgrwU19T8r2ZHRNu+4Hhr1Pa/b'
    'GP4+inLRicEOV+kn0LMBDOv43yTlqE0QamUtY+bJTCTT1Nved9lB7XJwxW0d+r+oOym2od50/cGsf86TccuDHeZY4+5XjaRRMOx8'
    'IYPnPPcjkGOdYCHXPv0d2I1OLAHMYzDijm/dI4O//lX1zZdqd19/+O1rUfY8Se4VOUGwDyKzz9kHAtnWw3+B7x699Unt9i3nC/Ia'
    'szAnzJJXD+9fcvda/epS9evf197948m334IFDTN9eO/aw/u/A4Oyeudq7Y3Pjz+99ejiK48uvnPy3WX4vHrj7sntFx2/B8DhdIL/'
    '6+KL1Rtvw7TJv8AWByufIv9694/H739MOZ3Wrv+hev1+9ca16s1fOiZq3Xu6887Db64RB+H6+3Xig8U3+37ueXSOvkAgaA/w3PPU'
    'OUx+OqM897z9b3sc+Dexe/sRIEH0iDrRoxMR/CFRpePtEVBdfaXuCzpkZocXAeDHH7xICPPmVWjmo0BwIgi91YntFjR4ToZx0kYq'
    'LZVNEmnMgGNzziymtQL0Ae/Bu6p+8wZQ6HMIt7B38yV4lRsBsh+BnsDpAfKovfvnvFxMA0KBjBzsVz972eEhh+DqBHrlTcdVJtP7'
    '8s7x7fu1j65Vr3wG38OTPpHZrgIT+IyES0E/e8HSSnPuX7S06pratRDDihZbkJBSCpxILjQhksX180coV7BXrtDDkiuBpHiWcmWI'
    'BPlUpnT11hP0WcmUIDSdhb3Skhz9iRUqpBihnqOegKigmqKCaooKZmiiwi0n3EKCOgdCpC43BpQVgSR2prJiqIT2VFx0DbAlmDPz'
    'bx6Dd9M6pCn0Ky08996SKt1cWPFhV2ERKYxokSGXZJLR3L+f+jeno8ez9W+eejdnI1ra4+cJ9oxEiz83/IxES/Mcfd+ihTg4gsgJ'
    'pJal0K9oAY+GAb8IkaqsZDT376ei5XT0eJaiZahU+VS0dN0eS3DDFS3Bh2LOyMFpHk7tW654SoH2EZPF53kRieSWEIYX7ZisLThc'
    'D5+AYKGbggWdgWAhjo9HtAxNsARS4xkIljOgyadSpevGd4I/I4PFf37xbARLq2xBv4LFc8lCvwFZXuQZHpPbjkSeRGTdv5+AWEFN'
    'sUKfgVjxBWTR8EKygeR4lvbKUInyqWTpmtaSEAIki5OeHoTEIDh3xVvAB0F9NNPgnaMHwaLjVitH3kYPgBygdvKLb2rX7tQ+/ejk'
    'zofHd95ys61D9LUbNx9+e+v4nZccbJBPPvyYoNbmjT4h2J6ekxCHB8H2zYjTws+9F/ZDgF9AkhE8Gx4Eg7eJTwvFVqrCDwKGQZvv'
    'aJgwHDoEPeHQHwQMAzYaER4eDIN87lPD0BX3+UHAMGADBtFDlIYhNX2frOwyN38IQAyINCPm1EDs7KOdGoCuKMHjAWCIgwZmqZgv'
    'FSUnt9Bz0OCfVU33JxAm/TefRP5Zzilps2AX+vDl78mqahdRljOLBTOvFYqGffhalzOW5jsfZ+Q8TbwF8CN59zv/0XMjZ5V03VAM'
    'kijY9prM0CnNFPmnHd85jRf8mMtp+wCJopY/ZT9WKZ83C0XrlN1UNHlXy/XbS5drZOzczWcbp9Y71cdXuuFY8eFYy5WCrlwYb1e0'
    '4+16Y7xdDI63M/V4e9h3vD1gM85HQlwWEVG7LU4Nt7igFL4ApRgg4wMkVkBMOyAaFeBJBngkYpCFGGTxBGnwII0UJGBDgVnrBmYt'
    'HJhlpWiUA5IGMqayq6ltz5WMaQU8VknKcSHgRV5zClWEWY7ebTl6uOW017n2HRqWUKcXnrrXQS9xt5d0t5dMt5fttOmqj90LZqlu'
    'MPPVB4kYRS3bSTfI+1P1t7hNa3R4A7DWjeZnPkx0Eaa7PURy+6cwByNr47v9sq2mvDVyRS2lFbpJ6gvBklouFOSDToI63Q3C6Q4Q'
    '9qvP0Eo6QE3jNp7qoqjtuiaAGKt+eKHtdTcFFYyORlXB4M7ycrGoFexzEv9fSstJz8vRwwvkDxUVpQs/pc4x/Av/3H7M0zUNq1jw'
    'S4g2xAXo7S6reCEsbXsJwPuulDP2SlrjQ1KbpwOBGN0IxAhJIE3mUEOuRDiDlex0W8lOW7WF/Vktl7JL2dKY8omGFlX83/+7Egme'
    'axviPZPZ7TaZ3S6TEbmhzCWoxHoYLo7ImcyC7hWI3nUYegAB9GDqRpFUqwMbknJYstHpdc/+XcaAmevSIsRIDZFhFru3CDkn39x6'
    'N+xoGwQ2tYreOqQdGxY04CGLlGohR74ivb640L3BC91ed3nZ8VWHF4GPAx6+0Ev6dvN30lquf4JOH+TJvoRlWFIpTyovd6Jsl/2B'
    'QqgqG0ukqNcpeu229gAJ4Sqc49fdrWrqHeERAZlmkDJmmmy103ewC+p1tjqJhqFYIwHSrIOV1kGyPZU/T+VPb/kTaCAGCpZ+6Mmp'
    '/K2pjdO83Smrm0wYrji90MvmZ/q0+bsyTic5UH9r5rRgDu/I571EQ4iPe4iLAZnUV1QyRPu+uLVzUcaO7TsU4uvY3lWbrnf7C72a'
    'vHAaKdB1wl2Zc3DstY6uh8Ndw3wnOwSRM4VGF5l47r8R/XcsC9rri34Zob1W41N+6I3LprWo/ONxgwbW5/AhSOjICgk9V3iFeYKk'
    'dBZi4R9SsHZ6deFcNxvOY0iJnZv2sHt6E2xf7oNTxjgUrsDDsYoBFbz7JaT+tUE/nktA+ezTOiW9VhOal5sgfP60QzbqoA/X6Wu4'
    'JXZ9oifmy517SviDYK8vF6Bfg6ljyeyhmUlPmbARNvOmez/lwn8oLgy4FuCHQ/ldAy6Dtw0X1hzQtavTVKf0ia4xjrZ0hVP4aGFQ'
    '4TNSO+wgD9Zv5+3i3mHDUO07ZR0MOuUQccsflLkTBkaKnDGSheGw9Y9GMIeIt4aaYHu0QB8S7zyVYaGd4lBNLvxw9W9f8bz2IOBT'
    'K/WplfrfwEr13+/zj2mihttyD0BOeLEayjLrz1Q+M+twvAUOdEYGZd9DPLVBh26D/lBE7wBR8LBCN2RSS4uf67cVaJHBVIVLwHdt'
    '1odEDkkEPW97PE2gr58gX8/7DE9ja/W92dpHuLHX7Xmn1H4XBqSoUBovrOYIr2HC+069zY/w6qEfOd+HjO+xH9kx67zHkN3bdstK'
    '74sCQm9tRuTcQRgHujfy+9gd7YX+Piit157+C2fBX/W8w96wDZ9T2k7Tnk/oc8NzKJIFcmZA65Olk6dlaW0/b1sb/Q27c9phG7nP'
    'Qx72NFkx3Y8ahaTBpkXYvVX9MpRelBqKn/pOdD3Xb/bkqdMP/HzDnXsiyc5N29DIwhBl7bRErKTlXCqc/R8ChP1FJgcWYh2RgkNm'
    'u/WVzdOY7b7RR3M3qtpurT+9Y+zYto1++5lVkx/TYadzBltIPQXU8MPg/12IrXEJl1QxcqpZGTbN5c2MoRz0NbU+5EZfKB0eak+J'
    '4lOhujW2qWr9f+ZGPdhBcvv5/+Eh3xXesXqe7xiGNT+QKBpsVf2LpkHGeUrXg9B1wcxkfuhU3e++aes/lmLO9f8Vz3L9fnThx8Bs'
    'YZte+Ecwbs5+Q7pI7ts+kxA/+B4FGSR4mNi+r0TqP9626g/N+ZOTAMtT+359k0dzfLJFWTCSpRC7rC/0jvtniR/bVxBlN/JDpxD+'
    'CVOIZWTzGUM/OC12VCOr5awzOIpdd14lxSzliqGkSA4MCSvkXmK+mD7z3f9+3O/wbvcZcm2dJgwlTHbEP/IGashNykYIrRfE69K2'
    '5056GJYbdGPAlrhmZlhL91UWHNYsi49372KoQjZDyhbJdnm+x7uPkJRJWZZdI6cOPZ3NzMpGTmoVfwklPcuGZSQzmqSVDdXe6Dtr'
    'Qfrfa9uIDFsw7DyXQlsx2k6Sqo/0sb4OmMdRyAPicRy2IR22IRO2IRu2IRe2IR+2oRC2oRi2YXvx0o4tQ+MGhUYOCo0dX1HUAb3s'
    'MLlsYfMdPE52iJwHu30/eQ/hrD5QU2BDaYWnu82hd5s77u52NglJIgRJgOouyZpmUU+jpKNVOqwN5vAh1idl7oYpftVP4asLZ1y4'
    'KthhCFeKKri8W388Elx+KnhSvcm1MaU+VupjsOBGpZxWljMlcFDUdnM6ZOmvHjlxvYVuCDEbUDyQ5GZK4KtrOWJndkRoC1NGmOq5'
    'aTmn2tsFj7c61yBOTR9xxT6EhkU2MoaZzAtCVs+QM165VORc6MRfI6eY4BBrITxn93UHLbej11cZU5EzUv1egp6tcybQmmGRRZQM'
    'K91ePD2App3kmN4tnUsNNPVMfGqYdN60jGFqgk7149v7a4iWM1kZ4f/w+WPqwFnwhrMpHnqknUFHcjnaoQdLDToYiIOcFNYqDLm4'
    'AQy1UFZg/+bUcOQpPQR5+pio9LHSTql37a9W2DhPbEGzZElhpMHZkVCg4dS/gYMep4UTsiJqD6OkK757rZc+s+WexY0BqPN1GOgM'
    'SvD3Lot9JndMiP3Wm23FpnvayDthbGQlIxvZ4fRk5hw4DGliZDdQK0hE6A7HHTDUXt3sRvopdD6k/qyiXCz1XKEWqivHAh4izOrS'
    'qvPlB7ZiQI9FInBnwPa9qtafCdNzfTK9sy00PKSmTDkzFB4dEgcYWUK1cseTZH3Oqst+eL89DcqaZ0H+9BmQv3MvotSBy135xHVP'
    'XGrceSCV6R53tgSusXkvYyO4mJYtcnVMhJNVWkAar3AoySFECbIoK4yKkSywCKsqEilaU8j/w0jFjEwnEafRuo54ihc0sbkvRM4O'
    'm6WC4uWkxvHpoqFIulGUFNNeVuvuHHcDK2M2W7QsjUhOq0hZrZg2VXcXrYRNIirJboAqKTJA1TOOb/FtUHdOA8OnTfDa0WwSFCs3'
    't2kasrgZFpEqZmE3Y3j32QFnmVI257sYLBK88QuL0lRLasTJJEOXSr5b5rrZ/K77NwpmxXLVcrEJwllvhMR+wGAh+8hZLWsWDux2'
    'jXeg4/eLUlbOGbonY4AUXZIAmaUMubOSsKFmwW9SnMGOrRKibl7ymTWKRW/ENfLo8rXqR9dqb14+vnpnhNy+/t3L5Mr2Ny9//+BK'
    'E4AgdwlxAlAffvfe8Ru//v7BK621R6o3rj36/ZXqjV+ffPcZfFV747PqxQethk67C52Rai8cUFinmsZaXRi1gGTkjHEoF32f7FiE'
    'xVCroU3TkpKW7TPXLI8Z7HvX5CSeYniV0USVoTieo2VBlHmNl7WkrKg0nWRoimY1PYlVhdJYWREFLLIqhwWRY5BMOWfz6qhrkiNQ'
    'x26TJsko1evv127crH14pXb1leqdq7U3Pj+58+3JnQ/JLI4//231wRvfP7h1fOWLEef+15PbL5IurO8fXH106drxN3dGVEPX4Wm+'
    'YJiF4/u/qv3m3REdiBEmuQtf1ru8/VL1yq9HHt67Vr3x9qPLNwDwZNxXvoKBqlf+07lUliD65V8Dlh5+/Rq5ITZo5sCWGdXFEiAl'
    'FCOvEQuuAcVm+KTxwFa6LQQcZPNFM+vs0zceEmxpJIwoafv5jJzzFBVobA86KVZS0zpuvm+J0jrJ+F+0ZFop4+iYC0GLaxExQczR'
    'cgMCLYkG88xC6zbBGLEoj+hYaJAgCdVKrXJekgy2iR38cF22VQJwyE7vhUJzfN+VXIRkjFyJiA/ygbv2wrNETcll2cjIRDSohrVj'
    'GjmyC9Cq/uEcXHKJLBBYMinhAGpJhve2VWRkSgWtfWj79JOnt5Sc94+aMyVLLjeqk7iWbPkVloU84sU2xgg1uObmuYEZZpqy3TRJ'
    'L8i+omgRJ4rb4V0L7FbRJYqbVTF817C7n3uvuG+92SsBtIyMO2fSkditn+Re8tZ0/LINUTZtbbb4ASEP6fwb2bPHrSysyP+20wzd'
    'KQ6RNfuR0A5ZbHe+5eqcbu9cFNs6x2E6Z+zOt12ds22dizxq65wJ0znn6SrqU7q6mVFdMqZh0Ely0pJMXZcIixIPolNNkkhKy2kF'
    '2Y4ayaApfFshrteuDixHE3isvGLBzKWIudX6gpTv8DYiVrNN0QHqvexdmWdXwXsDIXWewiLNUYKAMYtFhhc5r7vjO0seOfLdq912'
    '53jEEl2mpnuD1DMN5J8GgyhRQCJmKYriGcSedhZA8SGmgf3ToHmRRaLICLTIMLxw+mnQYaZB+6fBUgLiRJbDLMfyHMuefh5sJOD+'
    '9QttLMJ7WORZr9n9E+/PTZtX512clzHAtqvTdd3falds7kZl5JGlDdXotsuOllxNLLtL0HcFctet3atrgDJq53nBowhc4trLd5Ej'
    'xf3DK8kzjmogxXy8QrkusSM+PUZsjGaSuatXrV1Si094ej6l2HxfPy7cdfK4qzhVyJFWEqWRPJrW3v+1LFD1maIcJLzsF5JlpBwT'
    'u9ULWCZgQBTMQ40Up6oXs5GayhmsC/CwLLdStyW6u+5NOKEYaTsexbUxKCUAY1IihzgQWiwv0CG43DfK0aJ3EKZNGFE8DIEpEEdY'
    'oChWYPsfhLiRBe84uE32IoplscAJHBJE8qdv+R0OYiymWAacHJ6iRJ4dYBQ/xGgmAC2IFhiGoRFLMzBi/4MEQUxsH4dBCHE0Bn8M'
    'pDSF+9Y14UCGWZaD/xAQGCdSfP+j+EGGuHYiEwWGhqVwAg9gY9j+BwkAGcO3LwYQQoGVAQ4vhxkG960XQ4GM53kE2hvwAwOBEu9/'
    'lDaQCQGDYEbkiKGAMWJFof9BgkDGBowjAq8gLPIicAzCQSq8Je7qJzulDpW+WhXAbIn8bB0pFEIiQQ0LVOZmhUaQCLeY6AW3bmn0'
    '1ZLQdnw5ciRGgpr5VRtpudqmrmm3kHbP/X+Q6J2b7CL/ZHcxmTAXljbzxT1lQq9MJfGKmCxO6KsFTpwrjI5bU+MZaQnvcFvrq/Lu'
    'kUcL/Utbj//T6VHcOszE9YUptDaxS48ZY1urCVnaELbZcqpomtFR6ZCfSae3F9EG5e3xXx2YgjTlEINZhmCM4ng35h2n/Wjd890K'
    'ORHDuhkzsmo32/A0a/gnzQilGyF+WHlEYwNWSxOFQyW+ak5pscRCJrq9z+4v4RSani8nMgsoMZ+Y2ojt8hvT01mmHVbeHuuwEg7n'
    '4+ayvJFa2M/tHI5vJg7RoqIsjU9oVmJ9c1/UFsvSaEwpKdZuB1jxIBBAu9Esx/CYDQMqt+PaBNVmB1Ch3qDyiMQGqJSFyXhWsea2'
    'tumlcX5jls7HRVnNrk+vKxvj0ri1FK/Ei9yCND1baQeVt8c6qPbLW9xMIpUf5StsZn98AvHxuLxREdZikzgeHZ+emBT0zZlYcs+a'
    '6gAq8ElECnOM7Z2IKBSsRLEdVlsdYIVDwEoIgFVljosWdqM7aUNRUmuHY+yuvj5q8qNqcXVit7xpsPTCgrSSx3KcCoCVEACreY3J'
    '5fX5eCzOpTPx2ZWKtibnd/c2Y3tmfG1e21Cmk9ZhTlw1J6mOsMKgYxgWTDSeZ0LRlegVf6veSIQPVk177wW/VexEMCa5lDQ5E8eL'
    '6/RecVXIz43nZxcXxY0pbmw/lV1JSNJ8aX4qLc7uLG0dtaIdrP3xSusB10kg/rOzUvfs/pf9seyZ8Xq7bNnweHHwYKsV4q8/2fY3'
    'CS17+piWj49PNy00vGl5WeZ008JDm5aPOk83rc7Uy3sVDwmj2eQ8tbkbTU1NzS9yBzOJsfKymJ3NJhfNueLaajZWXl+bXo3Py4Yw'
    'w7o4koSC/LE7Ny3WY3d859Cde3Oj5eaD26rJBSUt+WtaucLcZD/PDjS4gBBp26+zi9Q0emtF+FF71L9L7N7drJHUDK+nXW+JNyvZ'
    '20nJkkoqvQPBUlRrXu61tWw3lynlbmIf83TqcZANW9cWhlnIOtsXTcBE6v5yYzerCCAB777cjMVGdnNmJaPBpKR6vR8ShLBIAF6V'
    'D5qgbjbPaClZOZDqS2qNQ0jL+SWZBWlZiknLYBc6WzB1C9DMZZoBhUhzb5HsgLb2dUic0x3RaaAQNRtk5JwToPDiYqnVBRiampKR'
    'C42wqTvA4jFOj8b9IQ1no8m7Gb08vhilkL1Gf+UU5x1uK6zha0AHnOH3NWE8VcN9L9mAkuKerXmjoEk7Tfr1bbeS7SigPRjdnzHT'
    'YfPZv7fmBK/Jlrc3NG7kjGwJEEzchABvJNsl3hJchCZytODzvEL4VW3uGtCQVXQVrcFUfbtoj2cJG5MtKXLXAdmt9x3UpKkwAwaj'
    'evAFdKKMwXtsJ6SefQUg0ErLBf8h68j5do3VFgZu1rogL/zBvwbZEGXkP7fUfFkv8KB2b0UoT8qTpEMiQohI9bayLFck89kQp1WI'
    '7GjyUETPmHKRY6R6bQHP7ouTKmNphbIjcG0m85ITSeupK5hiqdA6P/aC3+f1Rcmb+qjMuDIPMvXAeHsZxzaURP5PG9wDQvU6sB/Z'
    'vicv9kpyxkmGsYpyoUgkeClHUnMyZXd6CQG81Aw3wwANPNXPLJF4gsuF81QcjyTJhpZu7GtOakXBzNjDAAidQf1B/iYYWmv3bBYU'
    'Dc2FWifVpD59cse4NyzhB7lN2U6egQQTNOvHTDx5Ra42ViN/qs0WsVzZMc08lYay9VYJiLiNjrIIb2XV3tVWcsiVhQBiqWjuavbu'
    'NoCLNG6+JYETz3zT2j4QaFK2NI4pFTJuy2VXO/AIdreE91qXAZByywH3hx6BTcr7aT0+yHo+IClJmtXjE6/eqauoDjud7u9Mz3dN'
    'ZPRcUz74OzshrvuXe16ZUMpm5cJBj2+8u7j1ih09vrEiXZIAu39a9AEzpxspiayw6C7nFvxtyev61ss+2YZALxyW273mULiveFUF'
    'GKQZSZezRqbXXPcDPszLBTnba8QDL2w1rRe5HHo+kPOguhU56S2PF/zlaAeuI5K6+5djfiza+TRhmGLc86VLvNkx2O7fxnzf1tOG'
    '5IwkK0oJJFmvBce9VNDMwen+VSL8XqH7s4kA+6MX8ic93zRs0u7fTHlFoEZsAFtPFHuNNu39Mmv1QvuMlzadxMHeAJz1ZZPYSdHd'
    'P5nz8WshW8rIYWjEa/XZpZC6f7AQsKYenywGKIQenywFii6wVVIgEnp8u+z51r8h3v3bFR+LN29ndWxVp2Re9y5Wu3cRAidrgQrU'
    'th16E483LAqKwgSjTyY3MXXw8573BKW8EoMc2ib2TMFIpTRiTYXoY7ODOiaFW7p/6Q1rk6KDDsB7jbjd/p1WJi5CGHT9Dy9Ty5Xw'
    'mP6n4E9DYPiffWYYfOmuKhr80b/4Pwo3y//Z/lmIGf6v9mS1Hl/8q5ft0iBZ08St6/7VvwUza+jV/e/g753supAs8+/+7D3ARaqX'
    'pDjnk1BOLnUzftj942i7edUI5XT/8HxbcqOqgUhUvXUlg78d8bKJRIJEWSIZeg36rO8MQ8U5bAGqtteX/8fnnBvEwJbqsYXun/7E'
    '96lJBAkIMecgi2tgXwQQ7DhiBUiksJ3p3Jj2Qis4qewS6vA4coj6/sE7bW7bvydq73+cdOoXWOdt04fkv9+/dPLd29Xr7598/vva'
    'u38++fpPD+9/8/2DW45t/PDe17U3Pju+/9J/XXyReG/wu3rlT9Wb10bgi0ev3zn58Cq0rb3x+cN7f/2J/Ul9sP/4CRUVR6PbcvTw'
    '+J2XOHzy3a3qlS+qX9+o3vjyP2pvfVD97Nuj/7r486PFn8DHMMR/HMHknE81mNato8mfMPTDb641/cj/OHKmabuXMO+jI5jLEbT0'
    'QWfEcXNLOav21++gfVmENg3okOlff7l6469lsfa3T6ovX4WVwCyqn75Vu/N3cjoD/mEf8XAODMCr+smLVAlQRfgOwFW9/trxgz/U'
    'rl6u3nnn5Mu71W9fghVWv/zr8a/vn9z57OTbX1UvfXxy9/Pa29ebhwmcMI69Nk+YxM6JzhOvySqCdI8iUaR0hWZlLOhJrOkMw6oc'
    'hZLPtqxkF+VGUNjPnVMwz0Z6niJq6jZ3kkQrA7KVjO0/M6IqgiJqFMfzSU5QdI0TdBrJNMY0J7NI1lhBY3iEOV1GyaSiciyFNI0X'
    'MS2oKou4Zr5fpIk+D5mXRYlQutY67kUJiiIISY3iKcyIGsvSiFV1VUcaizRF5xUuyYITpCsMrUMDWaRVXRYFgeFEWU5irnUmyqZa'
    'dwTDpjksVUDWa5JzBa0LHq54hpvg7WCW943lzfd3x5lcSAwMNxEBaIcEk6Zpl5mBCaQAi5ZZcGeyONsZYBs7VbYCWhhkF6X+xhvj'
    'J6uUMnLK8j0j4WiJ5PIHPfcdHHA99x0caL6xZ+DJf1TIATFXLKzszpNvXTsS1Jce9DSVVN2gO5osaXl6doWepQVFnV/OjO+nohPq'
    'SpkTy9uHxh43Wa7sjSWMg3RswZ1SEgH/sWBHYZs1NT1JQ6SEmR39JbFdZw1F2dp1d9BcksNvkaDDga6HMXfO8DOucybPBDZvHKtx'
    'Rz9zMgl7NkDhDova4YaAF56rcV27X/Xzcs69n26a8NfbDzzxGLAF5trQe6a55+fZu/SlWrtO1XjQubm1Edvg6UyUW4tuWpOJSmpB'
    'Y/mdSkGv5K1oQV9KMnPj/Prs0opw5PlwIpniNjbWVrdWjMOlg/3xSlLIcYn0PLfMJDimWN5ldItZ2y2OMnMeOmgcnEyCsQb+ARjB'
    'oOYVzZJI2SdXzhhMVct4kqknqRVqQhhb3Fs9LI5HhUVe35dHLT5hiPG9nSVuyzAnosboXG5xZdXyzlWhVudQhYnq6zsJgS3FZnJj'
    'UUba1Cv6AR8VkvJs7pDfz86NLm/FvR/mcsXJVVWL4+hmtDI6u79XTm9MLJWy3PjBdoI6VNc39k1qbioxteyDzupmem89s725nV/b'
    'Rdl9prB2WCqm1T110jIZACbe3LV2p4tibN8zomqUHQzaTomRy5eKjmtiSeSYl1Ikp4VaRm/dg/CMvF8az8wmF2ljbktPJbWNDW7s'
    'YNNcLO5M4H16MmOtZQ8nKpaYtA5TR95U/KJTAKU5B2+iOBksDcxkgkHWtJNdJ1CaNFwPGHrf/7TdO7fa8hfq5kDda5fSmuxYcPax'
    'gjQV6Z5a0djNPhrzRfiad8WQUxL+PAhXkD/g2GlLx7TMihlPlvpIJ6mecdIoXE9M+wnnBrr9xBX/iuyRJwtJJ8bkkVqO1HsGJOQz'
    'niHPu3Hk3Qm2g5dkhAmfbdJ7MT5V1Gkx/BAXQ4Y8q8X49Gen5QhDXQ4Z9GwW5Ff7ndYjDnE99phntBw9xFrGh7kW/WwW4jOWOi0l'
    'NsSlkCGHuphAi7nTStDpV9Ia73TLkNukqzPpKf+kXd4eWLMT6XlTXl/Cs3h71dJK2eT64STaX9GYaIGLHaBssrRp7azKBxujR73X'
    'ejQdsITuE+b7nPBqlNte3t5OL65Ht8fEYnw9Njc5PVWI5Wcqk/MbFjOakA+ml3ZjW7Pm2UxY6HPCo6lYZjytMDtKFBkLe/nE+jjH'
    'rB5OackYSi1H0zg/V5hcpqRdde5sJiz2OeHpbZbZneKjZdrITHOyMYtzsTFKXIsipQjG68ry+iJ7MH6oc0g4mwmP9znhWHR6Zxnh'
    'hYQ+W5Rl66C0xIuL4uZ6bnRlqYTj2l5llTmcFhKCaJ3NhGN9TpgVuB1hU9uYmSwemqtMujTHTU9uLM9ujxY0dqygThupJLPOMjty'
    '6mwmjPqccCW5EJ01VipreHaMK4ost75b0qeWZtk9fQ8vTye2zE1hYUI35dXTkoSrikSAOdo6SDOpxg9Mid5aZefjUhplDlcNa7Yg'
    'lVcsNcVRMZqeSE4VFLSWpNYa5zDc4ad6jmcrVaWZHOUOoCWQLxfMVYSvnuriNeDrN6MEOuQEsJUcyHpFzuZlkkvqnB4KEWHzb8AS'
    '77+tDliuWZ5ac44MFwx7m7ZgZiVLzmpkD1vL20frW1UkbKdTlkiIGtrkM/4EOhfo2043Dyzb3BG+RuUOF2b76rR7jacEogbEYMPH'
    'PAv8NcrWBwzfAbn+E2cdLfvW9kg9H6CONn91uL46HNLKG4lomOUcRGc3ZrXd3ZWx1PpmZlufQxvLufRMZVuSo/TYfsWcXF5c51fW'
    '1EnBNI/aO3I20kmBsQZdO8A7715+19JljrfdzA1yxEp5KT4xnVJy67ENSVZHC9GckSyOTeVGlyelDGOom5PrsXJlcmNb8VN0Y8h2'
    'aAdmkpDsQYYc2uTE5l+6rTKf59giJ3K0wImi6C+P0MiuqB8FYiiBwSymMS9Cc64LDFzxJi8clPWcWsqKeGNVFPMFZSI2pnOz8bVl'
    'mi6sVky0MHvIR8Wtvd0DSunNhOjHzoRDZsHHxYD5/DpPKVJuc0nQtRWFHs+Vp6f1RGp60UyXxvXtWUab2ChrlRVZeWwMOLE8GZ3Y'
    'XNxl5fVJdbeY2B8rHG5mxhOlVHI2M7uV4nBiTZ1apM3D+BAYkKV4keZaf7vwHzmSzIqIYhH8L9WD/xgBwwe0yLM0Hoj/VsdWxcUD'
    'dV5O7R5azOz49KiaW4qOcRPRTVPaXhorIL28v7aPxvanevMf/nHznzfweGr+a+/urPjvMDO+vTWfl2LRw01tzuJncJGX1mZiOzMC'
    'Gs8Z1go/w5bN7Pi+tfXY+E+eW1LRZmZxspxEJTW/PMklcjPJ+OGUMrYgUuP6/mSc3krhmb2NyuPmP44BlhIolmVEmunOfzzLsBxD'
    'I5HDeBD2K2/HotEFLj9zuIHnUls7Ru7ASOyNbqeMJDWfKyW3DmZ39oztaAIt9WY/+sfNfr5g7Kn5L6C/s2JAOTG3sxaPpqTtmLBV'
    '2C/OHRaUrf3VMTyBk5vl8flkWabjmRkmhR8fA07klhZEJSWMUvEDfS6+nDrQqb3NxWiFTpl6YlbZwbn5nLQ8qyaEYTAgYgUeTMv6'
    'X7G7ARpcN6Od/zAvIIpCAsNzHMcPwoDSWDYnHRQOx8ayGh81uAo1VWJim1NSjKaonezYtDaVHM3PrRSSIZxA5kfJgEGB6kGZr1Nf'
    'Z8V4M3h9KaGNG3OmOpGdXlEO6dGFxAafTO+JojJZWttamSvMVeS05iugcJaMN1hix2NhPErkOBZ8OgHxlNCD82iR4xHLUjRCzCCc'
    'V5lWomt7CY7dKcc3C8U1ld0vxvWivEtp86qZTPLL+upG1JCyy2ZPzsNP42dd42eDRa57xM/66rQHAumnCOyKwMH2SnogsK9OeyCQ'
    'eYrArggcbDuxBwL76rQHAtmnCOyKwME2sHsgsK9OeyCQe4rArggcbG+xBwL76rQHAvmnCOyKwMF2s3sgsK9OeyBQ+HHHX7xJV6cO'
    'v7R3d1ZOoLaznVlnC0VUWZkqxspoanNVpMTStlKIF5R0ckzZkffFYlTeUeKPzQlM5Q53k8Y8W7QOhVhSRPS4sTqRmaXXdEacGaXj'
    'xRS7msihXCw5jOgLI3Lgp/FM4y/bzQvkwLUTEEXTIoMZrqsXyPOIR1gk1Vqh/SBeoJY10HJ2eTfNLce3p/cXDGnsYCpW0uKryuzO'
    'zo5iSvuLxQo7rU/11oDijzz+qQ8z+Kk/psjnAQhWWYlXKGP3wCiNFtH46OI6d8itpHdmd3OjpfKSYq0sjC6szT023hvl0+UFRDNI'
    'nRXzh2J0eVrZp1P8Ab0t02OppX26sJOdnI5hQ5kbyt475Q7B4G6sxwgCz3MCw7E06h5/ERDLMjQj0jQrsgNx3urKwvbhlCzHlsrC'
    'WCo/y0wdjC9nBUsYU8TZ1RQ1sZPfG9tYmZ6Y7bDz5zuGd1ry8RQ1ct9hE2keLXVxkF19wZtFZVcMIRZHRvaeu/PcAO/jw6aQ0Pyf'
    'EPvGOUrnbt4o4eZv3fUQYqPeUtE+KOZOinMeuexJMZbbGo3mczuFPDc7WuCk4pZU5NLG3ERykcmx3J6A5vNrUX7CvStGDh1ZpGwg'
    'rN6VYOap/eGtoJXA3p+09yfj/cl6f3Len7z3p+D9KXp/ui/CqedseH/7JoZ8M0OM/4Cxu5Rl69Bb4whN0MGSKe9lG7M26GfcR8g6'
    'pDjPdkyKDtklP/wuhT67ZHp32Z7IO3faLseH32Vs+F22pava2xVGTgHHXGtWPHDnjjYKoChyXm5WDm3keiZLRqZoF3azL1lzyQYr'
    'f+CcxpMabVzncVt9NQUDy1Eqi3gK5L6qJOGHSqs8VmiRSipJmVcoTVM0UaEFcuGAjhWOSTKawmKaF0CpMHpQ346Abs2keW+JeyrO'
    'vTIVuZAtkSRbjnFf+WZkADquVTn92DUi3V3kdKNRPbVehMGufegR8Wrjlsx6acDm5/WLmsjHjVOX3sPnsirni87x0aKdaYtdCcZg'
    '6Fhp03Uzb1NbOUf+3PUGCCRkdadk2fdIZUxLk1TZyBy4F2MfNHYJ1tbuZGvUlm3tqpqIKV81BFIhgsCwBOI/eeCUDwVdzjIMjd1t'
    'wM8upl3Uaz/U9jXFLpLZtmj7tevcn+e5fZliYzDE0YKn04xp7tbLFnKeF+SIpOWuvW4/JVf1mhYYO+SaUMs/w+aJSZgC5arHS673'
    'dSpbuA+VA1g9F7Jl7Es4/de71R97L4OTVfcvq5R08Ok6QgzmopH3nhBOuk9yWrKu2Wcx1bZ7eBoHJB3lbpOnt+CRmzbIwU5TMTPu'
    'Zq4KyGV328Za5Awo7XqNx0jBSKWLRNpkSqpdDMM5yd32kaqaurtwbxNe5OI+UH+mXdczopcymfrFga1yB621SlreMjI24yIt2tzt'
    '8zSx71skXYF7VKwfk7XsW9vAxJAyxUYfdiqTpGWsJiBbdRDI0XDgdA++nbqdEvLDu3HNoattT75q/pOj2k+aNtHVONhdsuSU5q4c'
    'mSYnxdV2aqZagqIMWFI90qf5MmOmDAW+CnzZrGDWufNSzj6Bb2nFYob8b+N90BL8FbnP2QrKvq27CW6Q07a35JWJjbctsUEKqEqW'
    'caj5RYR7ITg8uzvhvIKkAt/bogILniKsHg3TwoarWHajB7sstdS4uZr4D1LbNaDN8qW2HnFdAEumJnk+qdeJ98GyoKXAOix4dHWz'
    'jkQAocJzCXnKKDQf4+DHdPBjJvhx4wY5D+nahTbsAgiuaS7ZdkpLny/bv1MtAvDaMS7/H3g4pRUAEY6wOZrctSryAptc12fwFo/k'
    '0diGkcT6ajGxpBd2pwvFrYlCehHlVndTrmsUXCEV235w3YcXyct24QlfyMHdwqaFo9GWdLB/N4sZRkreiuJsm3yw27eMg32vJZDJ'
    'p2W7WLFP1x/YVOKCLanMnrPVr1wwLIfaG7VmCTl7fEJcf+69vLhLBVpSi8gun1O9fv/R5WvfP3in/q1dyhg+rL3/MfknKRBUfwN+'
    'S720Sf1964HlFAwaXVn9/sHV41e+qn77YvXmNef25VZln/aj/Ccffly99MmjX3/UsAaqH71JHvziE+jNKRXUGt8pAUOGvvqKG38j'
    'ebmYJvWWmmEjO/xijdjXFbfUW+Oxi2hhbrUbNx9+/ZFzhXHCmcWiM0+ylN+/WH3wxvHrnzz85t3Yyqxdf4ncKw1zbFwtfbXe4N61'
    '6m9/U7t+u3rli9p7v3j065vuikQuSHlLSnkg4rUZ0/7TOgEm99HkegotK6Mr8wc4pi5uzsZ2Zw84fZS3OGVhOh0TrO3ZVWttR5ua'
    'j3tDtH0a2S3OCDAuOgVbbPrxrNfuoUFogWWP6E5Vj44mZ+ix0fgsXhkvJJObU8L0wqph4J3lqFoZ1+ITS1n+kEIzZWZjNrl15C7X'
    '3KC+ULpp319KqP0ex2bFjbrd4uN/Ut1Mt6NBufrdCPYabYHfqgeju6896GQPA2B08F9cMMgLEytrFT6bndpMbe7OR7fzKwtbiUyC'
    'pcuqvE8tq/nK2k4+L/CxtaOIv5sWnhtIdFYQZPS5CmU0gcFSLfeUZznfuh1I1qtqN+4+xwzlew82WtazyPrzuqxifI99t2bglpVe'
    '0YgpWq8jBbYCKVvqRru7PnujwJ5LhLpfe0p8tC4TUY163R43QRi55j0bbmvdKcbSLORXJysfiBqxTakVMzay2VKR1OF5xjWhZ/xX'
    'eLdXnG+ZJ8i9aN8FGlZQZKn7ra729Ui2yU/idPuGUxLLfdd2t7Lydpn3rJZNArn3zpb1RP7991AceYNyzds6PJcUaKR2veSQgmdA'
    'RPOsIIo0LfCuy4T9N6xqbYN6668erQUNWtBIyEHLOXUTyV3pabMAdqrafq9581Jv72Xq1HlRZHiW4oE/MCtSfCuOXqdr38So8+7d'
    'MPgVFF+sU7aj9prln5y7Wlxy2N/Arg/l4oxgtelpUDezm+WbgiLKrft06jIdgJGtS84mQ/tdnFZpSLcr3zKF7KJcHVrZUtT1xhuj'
    'IBv6TXJzDPACKTrl9yHshx4B1Zq2rJbBEis0RwhoEjy11vtW9y6ubd1oVHfP66K6PTrfkNQRd7y+0GbPtqUwt4qquUPvdXzac5JI'
    'usR+02VvKu86EUYevfVp9eaV6ZWF+f+6+OLx+58+vPdp7c3LYOSAJemEHqovX2qYbFerr31X+/K+U5rx0et3RoiBXb32wcNvwNK8'
    '5XRVvfvVyV8+BMcbzC3ARtHQrOda1SGv/Q1srOp3l6of/sltSB3/4eulkcnau3+u/fnD6u8+g96rN+7Wfnfx0R+vPvrtS7V33//X'
    'Oik+h2AWj977DSkW+f7Hx/d/dXLn63+Dsas3r8KntTc/mzz+02tklBt3H118hRTnvHft+NNXHt577eG9iyff3CGW4Vu3j1/9onbx'
    'RaeGNiy79vpXTs1K+y6d4r8j57vqjbefv+CepXNnBbkI3pmMVXv77vOGeq7+8wIs/fidl5xqn840j+9fqX362+qrxNCEh7DwRx/e'
    'J8//8DVMOg3YJVr5fMuzAaiD1Vm99AXgAWYMPcIEjm/dq176W31PaASmWr1x7eG379Wu3Xl08Wbi5O5LDx98NlJ75+fHD35FjNs/'
    'fA0vT/7+Jizh5C8vVi9d8xXRLBtmyQKCAbub3EJPhvzrt8cf3gGYOn3B1FRixRXIy2v1caFnUnT00t+c8p/QLTQmk/vD17KjQQDm'
    'je+v1i7ed1aNzp/3ejXuyZzcfbX25qfVG38EXMFqH977Y1aTLbBgiC0Fvdiu+AhRfmDewyhmAXwEhyqhm3FCoqUkUfEjTauT0MK1'
    'NxwihPk+unQN/l398g4BjA3G4z//+eHXV50G0EHtxo2T7z6zqffOo9++DeiBZRy//peTux+ffPd69dZvHl2+AX+PP33dPfHGXSeK'
    'XFBh3X+sXnnr5M6nx/d/4XgK0J2zNMBls1xs/RsCAKets2hC8baXMg7zPvnmcyBGwmhf3qlduXl8/w9Oh8BXtb+9QZ4Dnb/yVe3d'
    'P9be+9jxYtzTahibpEir3SeZ14ef/OQ5TD698XubBz4/vn+79sp3BHV/fKt643fNepE2N9euvFm3FUfALvwZ2IPwKTiAAHjZvuqF'
    'XJziHjNBvKSvr5/c+ejk7ssjDuWNNCgbvo0DkAlXnXftjxGj0AbDtyd3gGkvE8a/eP8nz5Hb0/61evNPBaACMzdycvt3td/cnIqB'
    'I1v96Nq/kTXYguQnz9GYgn8e//n37plU/3IRPExHXozYLPIaoPPkF98AOmuvXARwE1xe/bp65WWC79++XH3//erNu9UbvyQot7kG'
    'WMqGFEHo8bvvA6s5ROPw3MndF2E83UEoIavLLzucM+kIjNqrr1av/ImIgE8+rP7mNXDET/7+2+o3v2p+ChxWe/cVwCGZyKUrjotJ'
    'JAUs8MabZLK2ZAUx9vC7D2sv3iXSynZMCSvffbH2Lsz9i5Ha29+e/PKt2sXbI8ev/RnEHVnx318bOb51pXrlD26AOAkDTkCr+u4n'
    'DpvC0gk6SBVeG17wwaPLl2EeBMOqmXfdR0TwRHxjZ9jqp0CPL4FzXAfACPSakxp70rCK+k0LRHK++oHTeuTRrS+q792ovfr2o7c+'
    'qd2+5Z4dYJzGoFcB3yd///L451+NEPl56fZI9eKvAVcj1Y/+cvL5x9AvKQ5bBOoFWiGzefOz2ptfATcw8JQI7w/uVe/8BkRf9dO3'
    'KeeRw3vkB+im2u1vYFSraOZHWhkxRGkC8OC1je67sKqmmLt1cvul6pX/HIEPwd1/9Nv3mpWMW1N/8zKQH+Dr4b3r4yMOG40ADgCt'
    'hMUuf06k0PX3QWhAA5jdo19fcuZc/eoLoKxmjIGg9cOPodkIcH31xs/J6mtX/giTH4Fxqx+9efLZLwAzIydfvFp77xdkBi570CoW'
    'SgphdzXID7ILqz7bKhZL3MOmcdGSxi3Lg3zg3pNqmHD+a6cidV/HMUhWFrcCQrxKRjayzuhgVBO54bklECSBSaR8/QK9kmM/e9t4'
    'XG17L6wVByRWuWOV5uzbD0mlX7I3IbfauNw5CSZl6nZKp6wXtcIzxWfsHbZnDOuZtnKpEbsiKRi59rZD3faV1R1nU+55sA0uPDPy'
    'jOvBhWeiz7TcbBuILX/c2cPLOTE7O+Lasviw96PGHmSznb/esNPMZZFDDy5b07YMc6bnLsBI3YVxsm5KgFpngzEHQHGQZd9U5Xzl'
    'rh5tRxK/+Q5I79E7rx///j5RP1dugihy5KOj5R2dVI82Xvpz9cEN0B2OZnM4gtD0q5+AjVS9+Xsi9m7cBalWfXARBG5D1N5yWKEh'
    'IF8kDPHF36r/efX4T795+PUroAAeXX7Vttk+IHxvT4Dw/FsfONIORnRkIAhh0EAP792vPvigwSfgPL3w/wMq5krW'
)
OLD_PREFIX = (
    'You are planning controlled evidence research; return only the complete JSON reply. '
    'Follow compact_decision_contract.output_schema; return the compact decision, never the input contract or expanded plan. '
    'Use concise Chinese for prose, preserve exact IDs/versions/enums and state uncertainty. '
    'Do not invent results, fill every slot, or claim causes from correlation.'
)


def _legacy_request():
    raw = zlib.decompress(base64.b64decode(LEGACY_REQUEST_ZLIB_B64))
    assert hashlib.sha256(raw).hexdigest() == LEGACY_REQUEST_SHA256
    return json.loads(raw)


def _contains_keyword(value, keyword):
    if isinstance(value, dict):
        return keyword in value or any(_contains_keyword(child, keyword) for child in value.values())
    if isinstance(value, list):
        return any(_contains_keyword(child, keyword) for child in value)
    return False


def _fake_client(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'bailian')
    monkeypatch.setenv('LLM_MAX_TOKENS', '4096')
    monkeypatch.delenv('LLM_ENABLE_THINKING', raising=False)
    client = llm.OpenAIJsonClient(model='deepseek-v4.1-flash',
        base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
        api_key='LOCAL_FIXTURE_NOT_A_SECRET', enable_thinking=False,
        response_format='json_object', policy=llm.ProviderPolicy(max_http_attempts=1))
    sent = []

    def capture(wire, _remaining):
        sent.append(json.loads(wire))
        return {'status': 200, 'body': {'choices': [
            {'finish_reason': 'stop', 'message': {'content': '{"synthetic_wire_fixture":true}'}}]}}

    monkeypatch.setattr(client, '_one_request', capture)
    return client, sent


def test_small_request_really_has_full_closed_action_shapes_and_explicit_required():
    source = build_case(0, 0, 'small-readable-style')
    before = deepcopy(source)
    prompt = grouped.prepare_current_prompt(source)
    contract = prompt['compact_decision_contract']
    assert contract['schema_style'] == 'full'
    schema = grouped._literal_schema(contract['output_schema'])
    union = schema['properties']['decisions']['items']['properties']['actions']['items']
    assert set(union) == {'oneOf'}
    for branch in union['oneOf']:
        assert branch['type'] == 'object'
        assert branch['additionalProperties'] is False
        assert set(branch['required']) == set(branch['properties'])
        assert {'reason', 'action'} <= set(branch['required'])
    assert not _contains_keyword(schema, 'minProperties')
    assert not _contains_keyword(schema, 'unevaluatedProperties')
    assert 'minProperties' not in ''.join(prompt['rules'])
    assert source == before


@pytest.mark.parametrize('cold', [False, True])
def test_full_shared_validators_accept_and_reject_the_same_unmodified_raw_domain(cold):
    source = cold_source() if cold else build_case(0, 0, 'style-equivalence')
    prompt = grouped.prepare_current_prompt(source)
    restored = grouped.verify_prompt(prompt)
    full = Draft202012Validator(grouped.output_schema(restored, compact=False))
    shared = Draft202012Validator(grouped.output_schema(restored, compact=True))
    for action in _actions(prompt):
        raw = raw_diagnose(prompt)
        if cold:
            raw = declare(raw)
        raw['decisions'][0]['actions'] = [action]
        saved = deepcopy(raw)
        assert full.is_valid(raw) and shared.is_valid(raw)
        variants = []
        for key in action:
            bad = deepcopy(raw)
            bad['decisions'][0]['actions'][0].pop(key)
            variants.append((bad, False))
        bad = deepcopy(raw)
        bad['decisions'][0]['actions'][0]['unknown_note'] = None
        variants.append((bad, False))
        bad = deepcopy(raw)
        bad['decisions'][0]['selected_versions'] = []
        variants.append((bad, action['action'] in {'stop', 'request_review'}))
        bad = deepcopy(raw)
        bad['choice_reason'] = '长' * 321
        variants.append((bad, False))
        for bad, expected in variants:
            assert full.is_valid(bad) is expected
            assert shared.is_valid(bad) is expected
        assert raw == saved


@pytest.mark.parametrize('full_serialized_characters,expected_style', [(64000, 'full'), (64001, 'shared')])
def test_style_selection_uses_the_entire_serialized_packet_unit_boundary_only(
        monkeypatch, full_serialized_characters, expected_style):
    source = build_case(0, 0, 'size-dispatch-only')
    original = llm.serialize_prompt_payload
    seen = []

    def artificial_boundary(packet):
        # No fact is changed: append legal JSON whitespace only for this unit
        # test. This is not a real worker/context capacity assertion.
        actual = original(packet)
        contract = packet.get('compact_decision_contract', {})
        if contract.get('schema_style') == 'full':
            assert {'evidence_research', 'rules', 'task_contract'} <= set(packet)
            assert {'request_hash', 'output_schema', 'schema_style'} <= set(contract)
            assert json.loads(actual) == packet
            assert len(actual) < full_serialized_characters
            seen.append('full')
            return actual + ' ' * (full_serialized_characters - len(actual))
        seen.append(contract.get('schema_style'))
        return actual

    monkeypatch.setattr(llm, 'serialize_prompt_payload', artificial_boundary)
    prompt = grouped.prepare_current_prompt(source)
    assert prompt['compact_decision_contract']['schema_style'] == expected_style
    assert seen[0] == 'full'
    assert ('shared' in seen) is (expected_style == 'shared')
    assert grouped.verify_prompt(prompt)['compact_decision_contract']['schema_style'] == expected_style


@pytest.mark.parametrize('error_type', [PermissionError, ValueError])
@pytest.mark.parametrize('phase', ['schema', 'serialization'])
def test_noncapacity_permission_and_value_errors_are_not_swallowed(monkeypatch, error_type, phase):
    source = build_case(0, 0, 'unrelated-error')
    calls = []
    original = grouped.output_schema

    def schema(packet, *, compact=False):
        calls.append(compact)
        if phase == 'schema':
            raise error_type('not-a-capacity-failure')
        return original(packet, compact=compact)

    def serialize(_packet):
        raise error_type('not-a-capacity-failure')

    monkeypatch.setattr(grouped, 'output_schema', schema)
    if phase == 'serialization':
        monkeypatch.setattr(llm, 'serialize_prompt_payload', serialize)
    with pytest.raises(error_type, match='not-a-capacity-failure'):
        grouped.prepare_current_prompt(source)
    assert calls == [False]


def test_actual_sealed_old_c3_request_keeps_original_schema_hash_and_native_prefix(monkeypatch):
    stored = _legacy_request()
    saved = deepcopy(stored)
    assert 'schema_style' not in stored['compact_decision_contract']
    assert grouped.prepare_current_prompt(stored) == saved
    assert grouped.prepare_prompt(stored) == saved
    client, sent = _fake_client(monkeypatch)
    client.complete_json(prompt_payload=stored, schema_name='local_legacy_request_wire_only')
    assert len(sent) == 1
    prefix, serialized = sent[0]['messages'][0]['content'].split('\n\n', 1)
    assert prefix == OLD_PREFIX
    assert serialized == llm.serialize_prompt_payload(saved)
    assert stored == saved


def test_actual_old_shared_schema_has_a_legal_authored_fixture_not_an_executed_plan(monkeypatch):
    import finance_forecast_agent.focused_research as research

    def forbidden(*_args, **_kwargs):
        raise AssertionError('schema satisfiability fixture must not fit or call a Provider')

    monkeypatch.setattr(research, '_make_model', forbidden)
    monkeypatch.setattr(llm.OpenAIJsonClient, '_one_request', forbidden)
    stored = _legacy_request()
    before = deepcopy(stored)
    authored = grouped.engineering_decision(stored)
    assert Draft202012Validator(stored['compact_decision_contract']['output_schema']).is_valid(authored)
    assert authored['schema_version'] == grouped.WIRE
    assert authored['decisions']
    assert stored == before


def test_new_style_is_request_bound_and_cannot_be_changed_after_freeze():
    prompt = grouped.prepare_current_prompt(build_case(0, 0, 'style-binding-negative'))
    saved = deepcopy(prompt)
    prompt['compact_decision_contract']['schema_style'] = 'shared'
    with pytest.raises(ValueError, match='binding mismatch|hash mismatch'):
        grouped.verify_prompt(prompt)
    with pytest.raises(ValueError, match='binding mismatch|hash mismatch'):
        grouped.prepare_current_prompt(prompt)
    assert grouped.prepare_current_prompt(saved) == saved


@pytest.mark.parametrize('style', ['full', 'shared'])
def test_new_explicit_style_uses_the_new_role_on_the_actual_fake_native_wire(monkeypatch, style):
    # Force shared through the same production dispatch, not by mutating a
    # hashed request after preparation. Only style selection is simulated.
    original = llm.serialize_prompt_payload
    if style == 'shared':
        def boundary(packet):
            actual = original(packet)
            if packet.get('compact_decision_contract', {}).get('schema_style') == 'full':
                return actual + ' ' * max(0, 64001 - len(actual))
            return actual
        with monkeypatch.context() as context:
            context.setattr(llm, 'serialize_prompt_payload', boundary)
            prompt = grouped.prepare_current_prompt(build_case(0, 0, 'new-style-wire'))
    else:
        prompt = grouped.prepare_current_prompt(build_case(0, 0, 'new-style-wire'))
    assert prompt['compact_decision_contract']['schema_style'] == style
    client, sent = _fake_client(monkeypatch)
    before = deepcopy(prompt)
    client.complete_json(prompt_payload=prompt, schema_name='local_new_request_wire_only')
    prefix, serialized = sent[0]['messages'][0]['content'].split('\n\n', 1)
    assert prefix != OLD_PREFIX
    assert 'complete selected action branch' in prefix
    assert 'declared in this reply can be selected immediately' in prefix
    assert 'Do not restate or reconstruct the schema' in prefix
    assert 'Do not optimize for winning this batch' in prefix
    assert 'Once feasible, commit' in prefix
    assert 'smallest intervention that distinguishes the selected hypothesis' in prefix
    assert 'Do not summarize the context before choosing' in prefix
    assert 'Generated features do not replace inherited built-in groups' in prefix
    assert 'minProperties' not in prefix
    assert json.loads(serialized) == before
    assert sent[0]['response_format'] == {'type': 'json_object'}
    assert sent[0]['enable_thinking'] is False
    assert len(sent) == 1 and prompt == before

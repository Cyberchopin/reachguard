"""Live policy additions. Archived English evaluation engine stays unchanged.

Bounded bilingual lexical rules are not a semantic model or fraud probability.
Risk states only tighten within a session; verification is a separate authority.
"""
import re
from .engine import Conversation, RuleExtractor, HIGH_IMPACT
from .models import RiskEvent

SUPPORTED = {'en', 'zh', 'zh-CN', 'zh-TW', 'en-zh'}
ZH_PATTERNS = {
    'authority': r'银行(?:安全中心|工作人员)|移民局|公安|警察|法院|使馆',
    'urgency': r'马上|立即|现在|紧急|被抓|逮捕|出事',
    'secrecy': r'别告诉|不要告诉|不能告诉|保密|别联系|不要联系',
    'money': r'(?:转(?:账|钱|款|[一二三四五六七八九十百千万两\d]+)|汇款|付款|支付|买礼品卡)',
    'credentials': r'(?:告诉|提供|发送|读出|给我|输入)[^。！？；\n]{0,25}(?:验证码|密码|口令)|(?:验证码|密码|口令)[^。！？；\n]{0,15}(?:告诉我|发给我|给我)',
    'remote_access': r'(?:安装|下载|打开)[^。！？；\n]{0,25}(?:远程控制|远程访问|AnyDesk|TeamViewer)',
    'injection': r'忽略[^。！？；\n]{0,15}(?:规则|指令)|(?:标记|设为)[^。！？；\n]{0,10}(?:已验证|可信)|关闭[^。！？；\n]{0,8}(?:提醒|安全)',
}


class BilingualRuleExtractor(RuleExtractor):
    def extract(self, segment):
        if segment.role == 'recipient' or segment.language not in SUPPORTED:
            return []
        # Same English baseline, with mixed-language frames explicitly allowed.
        english = super().extract(segment.model_copy(update={'language': 'en'}))
        examples = [(m.start(), m.end()) for m in re.finditer(
            r'骗子(?:可能|也许|通常)?(?:会)?说[：:][^。！？；\n]*?(?=但是|但现在|然而|[。！？；\n]|$)',
            segment.text)]
        events = list(english)
        for kind, pattern in ZH_PATTERNS.items():
            for match in re.finditer(pattern, segment.text, re.I):
                if any(a <= match.start() and match.end() <= b for a, b in examples):
                    continue
                prefix = segment.text[max(0, match.start()-12):match.start()]
                if kind in HIGH_IMPACT and re.search(r'(?:不要|别|不能|切勿|禁止)(?:把|将)?[^，。！？；]{0,8}$', prefix):
                    continue
                events.append(RiskEvent(
                    event_id=f'{segment.segment_id}:{segment.revision}:{kind}:{match.start()}:zh',
                    segment_id=segment.segment_id, revision=segment.revision, kind=kind,
                    start=match.start(), end=match.end(), confidence=0.7,
                    extractor='rules-bilingual-v1'))
        return events


class SafetyConversation(Conversation):
    def __init__(self, extractor=None):
        self.safety_categories = set()
        super().__init__(extractor or BilingualRuleExtractor())

    def ingest(self, segment):
        previous = self.state
        result = super().ingest(segment)
        if result['status'] != 'accepted':
            return result
        self.safety_categories.update(e.kind for sid, rows in self.events.items()
                                      if self.segments[sid].final for e in rows)
        kinds = self.safety_categories
        candidate = ('BLOCKED' if 'credentials' in kinds else
                     'COOLING_OFF' if 'secrecy' in kinds and HIGH_IMPACT & kinds else
                     'CHALLENGED' if HIGH_IMPACT & kinds else 'UNVERIFIED')
        ranks = {'UNVERIFIED': 0, 'CHALLENGED': 1, 'COOLING_OFF': 2, 'BLOCKED': 3}
        self.state = max((previous, candidate), key=ranks.get)
        self.timeline[-1]['state'] = self.state
        self.intervention_key = self.state
        result = self.snapshot('accepted')
        result['guardian']['emit'] = self.state != previous and self.state != 'UNVERIFIED'
        return result

    def snapshot(self, status='snapshot'):
        result = super().snapshot(status)
        result.update(policy_version='live-ratchet-v1', extractor='rules-bilingual-v1',
                      safety_evidence_categories=sorted(self.safety_categories),
                      policy_note='Current evidence can be corrected; session safety categories and restrictions cannot weaken.')
        result['uncertainty'] = [x for x in result['uncertainty'] if x != 'unsupported_language']
        result['uncertainty'].append('bounded_bilingual_rules_not_semantic_understanding')
        if any(s.language not in SUPPORTED for s in self.segments.values()):
            result['uncertainty'].append('unsupported_language')
        return result

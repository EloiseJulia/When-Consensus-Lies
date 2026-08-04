# -*- coding: utf-8 -*-
"""oTree app: human-reliance study (Phase 8), bilingual (en / zh).

Within-subjects, 3 display conditions (single/fake/dep) x 12 items, balanced Latin square,
per-participant trial-order + option-order randomization. Language is chosen by the session config
('language': 'en' | 'zh'). Exports one row per trial matching ../../analysis/preregistered_analysis.py.
"""
import random
from otree.api import *
from . import stimuli, content

doc = "Do people over-rely on unanimous multi-model AI consensus, and does disclosing dependence help?"


class C(BaseConstants):
    NAME_IN_URL = 'reliance'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 12
    CONDITIONS = ['single', 'fake', 'dep']
    ATTENTION_ROUND = 7            # attention-check screen shown once, after this trial
    COMP_CORRECT = 1              # correct comprehension option index
    MAX_COMP_ATTEMPTS = 2


class Subsession(BaseSubsession):
    pass


def creating_session(subsession: Subsession):
    if subsession.round_number != 1:
        return
    lang = subsession.session.config.get('language', 'en')
    for p in subsession.get_players():
        part = p.participant
        g = (p.id_in_subsession - 1) % 3                     # round-robin Latin-square group
        order = list(range(len(stimuli.ITEMS)))
        random.shuffle(order)                                # per-participant trial order
        trials = []
        for it in order:
            cond = C.CONDITIONS[(it + g) % 3]                # condition(g, i) = CONDITIONS[(i+g)%3]
            perm = [0, 1, 2, 3]
            random.shuffle(perm)                             # option order; 0 = GOLD in canonical list
            trials.append(dict(item=it, cond=cond, perm=perm, gold_pos=perm.index(0)))
        part.vars.update(lang=lang, g=g, trials=trials, comp_attempts=0,
                         passed_comprehension=None, passed_attention=None)


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    # per-trial (rendered manually in templates -> blank=True, validated in error_message)
    accept = models.IntegerField(blank=True)                 # 1 = use as-is, 0 = flag missing
    gap_choice = models.IntegerField(blank=True)             # chosen option position (if flagged)
    gap_correct = models.IntegerField(blank=True)            # 1/0 if flagged, else None
    confidence = models.IntegerField(min=1, max=5, blank=True)   # 1-5 star rating
    rt_ms = models.IntegerField(blank=True)
    comp = models.IntegerField(blank=True)                   # round-1 comprehension answer
    attn = models.IntegerField(blank=True)                   # attention-round answer
    age_group = models.IntegerField(blank=True)              # index into T['age_groups'] (1-based)
    ai_use = models.IntegerField(blank=True)
    lang_choice = models.StringField(blank=True)             # chosen on the first (Language) page


# ----------------------------------------------------------------- helpers
def _lang(player):
    return player.participant.vars.get('lang', 'en')


def _T(player):
    return content.UI[_lang(player)]


def _base(player):
    lang = _lang(player)
    html_lang = 'zh-Hans' if lang == 'zh' else 'en'
    font = ("font-family:'PingFang SC','Microsoft YaHei','Hiragino Sans GB',"
            "'Noto Sans CJK SC','Source Han Sans SC',sans-serif;") if lang == 'zh' else ""
    return dict(T=content.UI[lang], lang=lang,
                wrap_open=f'<div lang="{html_lang}" style="{font}">', wrap_close='</div>')


def _cur(player):
    return player.participant.vars['trials'][player.round_number - 1]


def _cur_item(player):
    lang = _lang(player)
    it = stimuli.ITEMS[_cur(player)['item']]
    return dict(scenario=it['scenario'][lang], task=it['task'][lang], answer=it['answer'][lang])


def _cur_options(player):
    lang = _lang(player)
    t = _cur(player)
    it = stimuli.ITEMS[t['item']]
    canonical = [it['gold'][lang]] + it['distractors'][lang]     # index 0 = GOLD
    return [dict(i=k, text=canonical[t['perm'][k]]) for k in range(4)]


# ----------------------------------------------------------------- pages
class Language(Page):
    """First page: choose English or Simplified Chinese (language-neutral)."""
    form_model = 'player'
    form_fields = ['lang_choice']

    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

    @staticmethod
    def error_message(player, values):
        if values.get('lang_choice') not in ('en', 'zh'):
            return 'Please choose a language / 请选择语言'

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.participant.vars['lang'] = player.lang_choice


class _Round1(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player):
        return _base(player)


class Consent(_Round1):
    pass


class Instructions(_Round1):
    pass


class WorkedExample(_Round1):
    pass


class Comprehension(_Round1):
    form_model = 'player'
    form_fields = ['comp']

    @staticmethod
    def error_message(player, values):
        T = _T(player)
        part = player.participant
        if values.get('comp') is None:
            return T['err_need_choice']
        if values['comp'] == C.COMP_CORRECT:
            part.vars['passed_comprehension'] = 1
            return None
        part.vars['comp_attempts'] += 1
        if part.vars['comp_attempts'] < C.MAX_COMP_ATTEMPTS:
            return T['comp_err']
        part.vars['passed_comprehension'] = 0   # allow through but flag for exclusion


class Trial(Page):
    form_model = 'player'
    form_fields = ['accept', 'gap_choice', 'confidence', 'rt_ms']

    @staticmethod
    def vars_for_template(player):
        t = _cur(player)
        T = _T(player)
        return dict(_base(player), item=_cur_item(player), cond=t['cond'],
                    is_multi=t['cond'] in ('fake', 'dep'), options=_cur_options(player),
                    models=content.MODELS,
                    single_model=content.MODELS[t['item'] % len(content.MODELS)],
                    progress=T['trial_progress'].format(n=player.round_number, total=C.NUM_ROUNDS))

    @staticmethod
    def error_message(player, values):
        T = _T(player)
        if values.get('accept') is None:
            return T['err_need_choice']
        if values['accept'] == 0 and values.get('gap_choice') is None:
            return T['err_need_gap']
        if values.get('confidence') is None:
            return T['err_need_conf']

    @staticmethod
    def before_next_page(player, timeout_happened):
        t = _cur(player)
        if player.accept == 0 and player.field_maybe_none('gap_choice') is not None:
            player.gap_correct = 1 if player.gap_choice == t['gold_pos'] else 0
        else:
            player.gap_correct = None


class AttentionCheck(Page):
    form_model = 'player'
    form_fields = ['attn']

    @staticmethod
    def is_displayed(player):
        return player.round_number == C.ATTENTION_ROUND

    @staticmethod
    def vars_for_template(player):
        return _base(player)

    @staticmethod
    def error_message(player, values):
        if values.get('attn') is None:
            return _T(player)['err_need_choice']

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.participant.vars['passed_attention'] = 1 if player.attn == 0 else 0


class _LastRound(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player):
        return _base(player)


class Demographics(_LastRound):
    form_model = 'player'
    form_fields = ['age_group', 'ai_use']

    @staticmethod
    def vars_for_template(player):
        T = _T(player)
        return dict(_base(player),
                    ages=[dict(i=k + 1, text=t) for k, t in enumerate(T['age_groups'])],
                    ai=[dict(i=k + 1, text=t) for k, t in enumerate(T['demo_ai'])])


class Debrief(_LastRound):
    pass


page_sequence = [Language, Consent, Instructions, WorkedExample, Comprehension, Trial,
                 AttentionCheck, Demographics, Debrief]


# ----------------------------------------------------------------- export (matches analysis schema)
def custom_export(players):
    yield ['participant_id', 'item_id', 'condition', 'accept', 'confidence', 'gap_correct',
           'rt_sec', 'order_index', 'group_g', 'lang', 'passed_comprehension', 'passed_attention',
           'total_time_sec', 'straightline_confidence', 'duplicate_id', 'age_group', 'ai_use']
    from collections import defaultdict
    byp = defaultdict(list)
    for p in players:
        byp[p.participant.code].append(p)
    for code, plist in byp.items():
        plist.sort(key=lambda x: x.round_number)
        part = plist[0].participant
        last = plist[-1]
        age_group = _flag(last.field_maybe_none('age_group'))
        ai_use = _flag(last.field_maybe_none('ai_use'))
        confs = [p.field_maybe_none('confidence') for p in plist]
        confs = [c for c in confs if c is not None]
        straight = 1 if (len(confs) > 1 and len(set(confs)) == 1) else 0
        trials = part.vars.get('trials', [])
        for p in plist:
            idx = p.round_number - 1
            t = trials[idx] if idx < len(trials) else {}
            item_id = stimuli.ITEMS[t['item']]['id'] if t else ''
            gc = p.field_maybe_none('gap_correct')
            rt = p.field_maybe_none('rt_ms')
            yield [part.code, item_id, t.get('cond', ''),
                   p.field_maybe_none('accept'), p.field_maybe_none('confidence'),
                   '' if gc is None else gc,
                   '' if rt is None else round(rt / 1000.0, 1),
                   idx, part.vars.get('g', ''), part.vars.get('lang', ''),
                   _flag(part.vars.get('passed_comprehension')),
                   _flag(part.vars.get('passed_attention')),
                   '', straight, 0, age_group, ai_use]


def _flag(v):
    return '' if v is None else v

"""oTree app: human-reliance study (Phase 8).

Within-subjects, 3 display conditions (single/fake/dep) x 12 items, balanced Latin square,
per-participant trial-order + option-order randomization. Exports one row per trial matching the
schema in ../../analysis/preregistered_analysis.py.
"""
import random
from otree.api import *
from . import stimuli

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
        part.vars.update(g=g, trials=trials, comp_attempts=0,
                         passed_comprehension=None, passed_attention=None)


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    # per-trial (every round)
    accept = models.IntegerField(
        widget=widgets.RadioSelect,
        choices=[[1, 'Use this answer as-is'],
                 [0, 'Flag that key information is missing / ask a clarifying question first']])
    gap_choice = models.IntegerField(blank=True)             # chosen option position (if flagged)
    gap_correct = models.IntegerField(blank=True)            # 1/0 if flagged, else None
    confidence = models.IntegerField(min=0, max=100, blank=True)
    rt_ms = models.IntegerField(blank=True)
    # round 1 only
    comp = models.IntegerField(
        blank=True, widget=widgets.RadioSelect,
        choices=[[0, 'Whether the answer is written politely'],
                 [1, 'Whether the answer can be used as-is, or whether key information is missing'],
                 [2, 'How quickly the AI responded']])
    # attention round only
    attn = models.IntegerField(
        blank=True, widget=widgets.RadioSelect,
        choices=[[1, 'Agree'], [0, 'Disagree'], [2, 'Neutral']])
    # last round only
    age = models.IntegerField(min=18, max=100, blank=True)
    ai_use = models.IntegerField(
        blank=True, widget=widgets.RadioSelect,
        choices=[[1, 'Never'], [2, 'Rarely'], [3, 'Sometimes'], [4, 'Often'], [5, 'Daily']])


# ----------------------------------------------------------------- helpers
def _cur(player: Player):
    return player.participant.vars['trials'][player.round_number - 1]


def _cur_options(player: Player):
    t = _cur(player)
    it = stimuli.ITEMS[t['item']]
    canonical = [it['gold']] + it['distractors']            # index 0 = GOLD
    return [dict(i=k, text=canonical[t['perm'][k]]) for k in range(4)]


# ----------------------------------------------------------------- pages
class Consent(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1


class Instructions(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1


class Comprehension(Page):
    form_model = 'player'
    form_fields = ['comp']

    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

    @staticmethod
    def error_message(player, values):
        part = player.participant
        if values['comp'] == C.COMP_CORRECT:
            part.vars['passed_comprehension'] = 1
            return None
        part.vars['comp_attempts'] += 1
        if part.vars['comp_attempts'] < C.MAX_COMP_ATTEMPTS:
            return 'Not quite - please re-read the instructions and try again.'
        part.vars['passed_comprehension'] = 0   # allow through but flag for exclusion


class Trial(Page):
    form_model = 'player'
    form_fields = ['accept', 'gap_choice', 'confidence', 'rt_ms']

    @staticmethod
    def vars_for_template(player):
        t = _cur(player)
        return dict(item=stimuli.ITEMS[t['item']], cond=t['cond'],
                    options=_cur_options(player), trial_num=player.round_number,
                    total=C.NUM_ROUNDS)

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
    def before_next_page(player, timeout_happened):
        player.participant.vars['passed_attention'] = 1 if player.attn == 0 else 0


class Demographics(Page):
    form_model = 'player'
    form_fields = ['age', 'ai_use']

    @staticmethod
    def is_displayed(player):
        return player.round_number == C.NUM_ROUNDS


class Debrief(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == C.NUM_ROUNDS


page_sequence = [Consent, Instructions, Comprehension, Trial, AttentionCheck, Demographics, Debrief]


# ----------------------------------------------------------------- export (matches analysis schema)
def custom_export(players):
    yield ['participant_id', 'item_id', 'condition', 'accept', 'confidence', 'gap_correct',
           'rt_sec', 'order_index', 'group_g', 'passed_comprehension', 'passed_attention',
           'total_time_sec', 'straightline_confidence', 'duplicate_id']
    from collections import defaultdict
    byp = defaultdict(list)
    for p in players:
        byp[p.participant.code].append(p)
    for code, plist in byp.items():
        plist.sort(key=lambda x: x.round_number)
        part = plist[0].participant
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
                   idx, part.vars.get('g', ''),
                   _flag(part.vars.get('passed_comprehension')),
                   _flag(part.vars.get('passed_attention')),
                   '', straight, 0]


def _flag(v):
    return '' if v is None else v


# ----------------------------------------------------------------- bot lives in reliance/tests.py


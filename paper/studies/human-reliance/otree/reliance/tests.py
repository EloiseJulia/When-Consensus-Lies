"""Bots that play the whole flow headlessly: `otree test reliance 6`."""
import random
from otree.api import Bot
from . import (C, Language, Consent, Instructions, WorkedExample, Comprehension, Trial, Clarification,
               AttentionCheck, Demographics, Debrief)


class PlayerBot(Bot):
    def play_round(self):
        if self.round_number == 1:
            yield Language, dict(lang_choice=random.choice(['en', 'zh']))
            yield Consent, dict(consent=True)
            yield Instructions
            yield WorkedExample
            yield Comprehension, dict(comp=C.COMP_CORRECT)
        accept = random.choice([0, 1])
        yield Trial, dict(accept=accept, confidence=random.randint(1, 5), rt_ms=10000)
        if accept == 0:
            yield Clarification, dict(gap_choice=random.randint(0, 4))
        if self.round_number == C.ATTENTION_ROUND:
            yield AttentionCheck, dict(attn=0)
        if self.round_number == C.NUM_ROUNDS:
            yield Demographics, dict(age_group=3, ai_use=3)
            yield Debrief

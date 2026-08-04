"""Bots that play the whole flow headlessly: `otree test reliance 6`."""
import random
from otree.api import Bot
from . import (C, Language, Consent, Instructions, WorkedExample, Comprehension, Trial,
               AttentionCheck, Demographics, Debrief)


class PlayerBot(Bot):
    def play_round(self):
        if self.round_number == 1:
            yield Language, dict(lang_choice=random.choice(['en', 'zh']))
            yield Consent
            yield Instructions
            yield WorkedExample
            yield Comprehension, dict(comp=C.COMP_CORRECT)
        yield Trial, dict(accept=random.choice([0, 1]), gap_choice=0,
                          confidence=random.randint(1, 5), rt_ms=10000)
        if self.round_number == C.ATTENTION_ROUND:
            yield AttentionCheck, dict(attn=0)
        if self.round_number == C.NUM_ROUNDS:
            yield Demographics, dict(age_group=3, ai_use=3)
            yield Debrief

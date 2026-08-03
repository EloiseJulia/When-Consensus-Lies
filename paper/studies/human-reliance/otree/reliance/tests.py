"""Bots that play the whole flow headlessly: `otree test reliance 6`."""
import random
from otree.api import Bot
from . import (C, Consent, Instructions, Comprehension, Trial,
               AttentionCheck, Demographics, Debrief)


class PlayerBot(Bot):
    def play_round(self):
        if self.round_number == 1:
            yield Consent
            yield Instructions
            yield Comprehension, dict(comp=C.COMP_CORRECT)
        yield Trial, dict(accept=random.choice([0, 1]), gap_choice=0,
                          confidence=random.randint(0, 100), rt_ms=1500)
        if self.round_number == C.ATTENTION_ROUND:
            yield AttentionCheck, dict(attn=0)
        if self.round_number == C.NUM_ROUNDS:
            yield Demographics, dict(age=30, ai_use=3)
            yield Debrief

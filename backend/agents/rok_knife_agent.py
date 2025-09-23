from __future__ import annotations

from typing import List

from schemas.rok_schemas import ROKInput, ROKOutput, Spine, BiasLock, StoryPrimitives, WeirdDir, Taglines


def _tighten(text: str, words: int) -> str:
    # naive trimming helper
    parts = text.strip().split()
    return " ".join(parts[:words])


def generate_big_idea(req: ROKInput) -> ROKOutput:
    # Spine forge (heuristic)
    enemy = _tighten("the boring default everyone tolerates", 6)
    mech = _tighten((req.differentiators[0] if req.differentiators else "unique mechanism that works"), 8)
    trans = _tighten("life after this is faster and calmer", 12)
    intent = "Make people say: 'It solves " + enemy.split()[1] + " by " + mech.split()[0] + ".'"

    spine = Spine(enemy_6w=enemy, mechanism_8w=mech, transformation_12w=trans, commanders_intent=intent)

    locks = [
        BiasLock(lock="loss_aversion", line="No more costly waste from the old way"),
        BiasLock(lock="status_gain", line="Look sharp and in control"),
        BiasLock(lock="curiosity_gap", line="How does it do that live?"),
    ]

    story = StoryPrimitives(
        hook="The villain gets punched on page one",
        turn="Your mechanism shows the cheat code",
        payoff="The after-state lands with proof",
    )

    weird = [
        WeirdDir(level="safe", image="stopwatch stamping tasks while you speak"),
        WeirdDir(level="spicy", image="octopus hands filing tasks as you talk"),
        WeirdDir(level="unhinged", image="court stenographer slamming a sales gong"),
    ]

    big_sentence = f"[Brand] is the {_tighten(mech, 3)} that kills {_tighten(enemy, 3)}, so users get {_tighten(trans, 5)}."

    tags = Taglines(
        benefit_blunt="Faster outcome this week",
        enemy_burn="Kill the chaos for good",
        mechanism_flex=_tighten(mech, 5),
        status_whisper="Always on point",
        curiosity_gap="Who did that already?",
        number_spike="Zero dead weeks",
        rhyme_or_rhythm="Cut. Click. Continue.",
    )

    # naive recall prediction
    score = 4
    return ROKOutput(
        spine=spine,
        bias_locks=locks,
        story_primitives=story,
        weirdness_dial=weird,
        big_idea_sentence=big_sentence,
        taglines=tags,
        retell_score_pred=score,
    )


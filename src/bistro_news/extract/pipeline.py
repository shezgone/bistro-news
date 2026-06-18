"""4-step 추출 파이프라인. (구 eval/run_extraction.py 의 본체)

article dict = {title, write_time, publisher, body}.
cfg dict     = models.json 의 한 설정.
반환         = (core_event|None, parse_status, raw_block)

dry=True 면 모델 호출 없이 렌더링만 출력하고 (None, "dry_run", "") 반환.
"""
from ..io import parse_core
from ..llm.client import call_model
from ..llm.prompts import fill, load_prompt


def _dump_dry(label, system, user):
    print(f"\n{'=' * 70}\n[{label}]\n{'-' * 70}\n[SYSTEM]\n{system[:600]}\n...\n[USER]\n{user[:900]}\n...")


def _vars(art):
    return dict(TITLE=art["title"], WRITE_TIME=art["write_time"],
                PUBLISHER=art["publisher"], ARTICLE_TEXT=art["body"])


def run_legacy(cfg, art, dry=False):
    """기존 단일 프롬프트 1회 호출."""
    system, user = load_prompt(cfg.get("prompt", "legacy_single.md"))
    user = fill(user, **_vars(art))
    if dry:
        _dump_dry("LEGACY", system, user)
        return None, "dry_run", ""
    out = call_model(cfg, system, user)
    core, status = parse_core(out)
    return core, status, out


def run_new4step(cfg, art, dry=False):
    """Step A→B→C→D 체이닝. core_event 는 D(병합 최종본)에서, 실패 시 A 폴백."""
    cand = cfg.get("step_a_candidate", "후보2")
    v = _vars(art)
    sysA, userA = load_prompt("step_a_core.md", user_heading_contains=cand)
    sysB, userB = load_prompt("step_b_background.md")
    sysC, userC = load_prompt("step_c_consequence.md")
    sysD, userD = load_prompt("step_d_critic.md")
    pA = fill(userA, **v)
    if dry:
        _dump_dry(f"STEP A ({cand})", sysA, pA)
        _dump_dry("STEP B", sysB, fill(userB, **v, STEP_A_OUTPUT="<A 출력>"))
        _dump_dry("STEP C", sysC, fill(userC, **v, STEP_A_OUTPUT="<A>", STEP_B_OUTPUT="<B>"))
        _dump_dry("STEP D", sysD, fill(userD, **v, STEP_A_OUTPUT="<A>", STEP_B_OUTPUT="<B>", STEP_C_OUTPUT="<C>"))
        return None, "dry_run", ""
    outA = call_model(cfg, sysA, pA)
    outB = call_model(cfg, sysB, fill(userB, **v, STEP_A_OUTPUT=outA))
    outC = call_model(cfg, sysC, fill(userC, **v, STEP_A_OUTPUT=outA, STEP_B_OUTPUT=outB))
    outD = call_model(cfg, sysD, fill(userD, **v, STEP_A_OUTPUT=outA, STEP_B_OUTPUT=outB, STEP_C_OUTPUT=outC))
    core, status = parse_core(outD)
    if core is None:
        core, status = parse_core(outA)
        status += "+fallbackA"
    raw_block = "\n\n".join([f"# STEP A\n{outA}", f"# STEP B\n{outB}",
                             f"# STEP C\n{outC}", f"# STEP D\n{outD}"])
    return core, status, raw_block

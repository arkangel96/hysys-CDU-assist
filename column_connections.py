"""
Design → Connections structural intelligence (Family F).

READ is always available. WRITE is mechanical and **approval-only**:
  feed stage, stage count, P_cond / P_reb, condenser type review,
  inlet stream attach (manual).

Never auto-saves the .hsc. Never silent structural edits.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from column_models import ColumnState, EngineeringState, ConvergenceLimits


@dataclass(slots=True)
class StructuralMove:
    """One Connections / mechanical proposal for engineer approval."""

    move_id: str
    parameter: str  # feed_stage | stage_count | p_cond | p_reb | condenser_type | inlet_stream
    current: Any
    proposed: Any
    reason: str
    risk: str = "mechanical — changes column topology / hydraulics / thermo path"
    com_writable: bool = True  # False => recommend only (do in HYSYS UI)
    requires_approval: bool = True

    def summary_line(self) -> str:
        write = "COM+approval" if self.com_writable else "MANUAL in HYSYS"
        return (
            f"[{self.move_id}] {self.parameter}: {self.current} -> {self.proposed} "
            f"| {write} | {self.reason}"
        )


def recommend_connections_moves(
    state: ColumnState,
    engineering_state: EngineeringState | str,
    *,
    preferred_family: str = "",
    infeasible_evidence: bool = False,
    limits: ConvergenceLimits | None = None,
) -> list[StructuralMove]:
    """
    PE-style Connections thinking: when operating MVs are weak / State F,
    propose mechanical changes — never execute here.
    """
    eng = (
        engineering_state
        if isinstance(engineering_state, EngineeringState)
        else EngineeringState(str(engineering_state))
    )
    moves: list[StructuralMove] = []
    n = state.number_of_stages
    feed = state.feed_stage
    fam = (preferred_family or "").strip()

    want_structural = (
        eng == EngineeringState.F_INFEASIBLE
        or infeasible_evidence
        or fam == "F_structural"
        or eng
        in (
            EngineeringState.C_OFF_SPEC,
            EngineeringState.D_CONSTRAINT,
        )
        and infeasible_evidence
    )

    # Always surface soft structural awareness on State F / family F
    if eng == EngineeringState.F_INFEASIBLE or fam == "F_structural" or infeasible_evidence:
        want_structural = True

    if not want_structural and eng not in (
        EngineeringState.C_OFF_SPEC,
        EngineeringState.D_CONSTRAINT,
        EngineeringState.B_NUMERICAL,
    ):
        return moves

    # --- Feed stage ---
    if n is not None and feed is not None and n >= 3:
        mid = max(2, min(n - 1, (n + 1) // 2))
        if eng == EngineeringState.F_INFEASIBLE or infeasible_evidence or fam == "F_structural":
            # Prefer moving feed toward mid if at extreme; else ±1 trial suggestions
            if feed <= 1:
                moves.append(
                    StructuralMove(
                        move_id="feed_stage_down_to_mid",
                        parameter="feed_stage",
                        current=feed,
                        proposed=min(feed + 1, mid),
                        reason=(
                            "Feed near top — more rectifying / less stripping length. "
                            "Try one stage lower (approval)."
                        ),
                    )
                )
            elif feed >= n:
                moves.append(
                    StructuralMove(
                        move_id="feed_stage_up_from_bottom",
                        parameter="feed_stage",
                        current=feed,
                        proposed=max(feed - 1, mid),
                        reason=(
                            "Feed at/near bottom — little stripping section. "
                            "Try one stage higher (approval)."
                        ),
                    )
                )
            else:
                # Bidirectional options for engineer choice
                if feed + 1 <= n:
                    moves.append(
                        StructuralMove(
                            move_id="feed_stage_plus_1",
                            parameter="feed_stage",
                            current=feed,
                            proposed=feed + 1,
                            reason=(
                                "Operating families weak / State F evidence — "
                                "test feed one stage lower (more stages above feed)."
                            ),
                        )
                    )
                if feed - 1 >= 1:
                    moves.append(
                        StructuralMove(
                            move_id="feed_stage_minus_1",
                            parameter="feed_stage",
                            current=feed,
                            proposed=feed - 1,
                            reason=(
                                "Operating families weak / State F evidence — "
                                "test feed one stage higher (more stripping below feed)."
                            ),
                        )
                    )

        # Soft hint when off-spec but not yet F: feed extreme only
        elif eng == EngineeringState.C_OFF_SPEC and (feed <= 1 or feed >= n):
            target = mid
            moves.append(
                StructuralMove(
                    move_id="feed_stage_toward_mid",
                    parameter="feed_stage",
                    current=feed,
                    proposed=target,
                    reason=(
                        "Feed at column extreme while product off-spec — "
                        "consider feed toward mid-tray before more energy."
                    ),
                )
            )

    # --- Stage count ---
    if n is not None and (eng == EngineeringState.F_INFEASIBLE or infeasible_evidence or fam == "F_structural"):
        moves.append(
            StructuralMove(
                move_id="stage_count_plus_2",
                parameter="stage_count",
                current=n,
                proposed=n + 2,
                reason=(
                    "Likely under-staged for locked FINAL_TARGET — "
                    "add ~2 stages (mechanical; re-place feed after)."
                ),
                risk="mechanical — changes stage map; feed stage index may shift",
            )
        )

    # --- Pressures ---
    p_cond = state.condenser_pressure_bar
    p_reb = state.reboiler_pressure_bar
    if eng == EngineeringState.F_INFEASIBLE or infeasible_evidence or fam == "F_structural":
        if p_cond is not None:
            moves.append(
                StructuralMove(
                    move_id="p_cond_review",
                    parameter="p_cond",
                    current=round(float(p_cond), 4),
                    proposed=round(float(p_cond) * 0.95, 4),
                    reason=(
                        "Pressure changes relative volatility / stripper driving force. "
                        "Propose mild P_cond decrease for trial — approval only."
                    ),
                    risk="mechanical — thermo/K-values and duties shift",
                )
            )
        if p_reb is not None and p_cond is not None and p_reb < p_cond:
            moves.append(
                StructuralMove(
                    move_id="p_reb_fix_profile",
                    parameter="p_reb",
                    current=round(float(p_reb), 4),
                    proposed=round(float(p_cond) + 0.2, 4),
                    reason="P_reb < P_cond looks nonphysical for top-down column — fix profile.",
                    risk="mechanical — pressure profile / hydraulics",
                )
            )
        elif p_reb is not None:
            moves.append(
                StructuralMove(
                    move_id="p_reb_review",
                    parameter="p_reb",
                    current=round(float(p_reb), 4),
                    proposed=round(float(p_reb) * 1.02, 4),
                    reason=(
                        "Optional mild P_reb increase trial if boiling / strip duty limited "
                        "(approval only)."
                    ),
                )
            )

    # --- Condenser type (manual) ---
    ctype = (state.condenser_type or "").lower()
    if "full reflux" in ctype and (
        eng == EngineeringState.F_INFEASIBLE or infeasible_evidence or fam == "F_structural"
    ):
        moves.append(
            StructuralMove(
                move_id="condenser_type_review",
                parameter="condenser_type",
                current=state.condenser_type or "Full Reflux",
                proposed="Partial / Total (review only)",
                reason=(
                    "Full Reflux fixes vapor product topology. "
                    "Changing condenser type is a major mechanical redesign — do in HYSYS UI."
                ),
                com_writable=False,
                risk="mechanical — product topology / DOF / Active set all change",
            )
        )

    # --- Inlet stream (manual) ---
    if state.feed_streams and (
        eng == EngineeringState.F_INFEASIBLE or fam == "F_structural" or infeasible_evidence
    ):
        feeds = ", ".join(state.feed_streams)
        moves.append(
            StructuralMove(
                move_id="inlet_stream_review",
                parameter="inlet_stream",
                current=feeds,
                proposed="(confirm correct feed stream + stage attach)",
                reason=(
                    "Wrong inlet stream or attach stage is a model-definition error — "
                    "verify Connections Inlet Streams table in HYSYS."
                ),
                com_writable=False,
                risk="mechanical — wrong feed invalidates all operating trials",
            )
        )

    # Deduplicate by move_id
    seen: set[str] = set()
    unique: list[StructuralMove] = []
    for m in moves:
        if m.move_id in seen:
            continue
        seen.add(m.move_id)
        unique.append(m)
    return unique


def format_structural_block(moves: list[StructuralMove]) -> str:
    if not moves:
        return (
            "CONNECTIONS STRUCTURAL [F] — none recommended now\n"
            "  (Operating families still preferred; mechanical moves stay approval-only.)"
        )
    lines = [
        "CONNECTIONS STRUCTURAL [F] — MECHANICAL / APPROVAL REQUIRED",
        "  You must confirm before any write. Assist will not silent-edit Connections.",
    ]
    for m in moves:
        lines.append(f"  -> {m.summary_line()}")
        lines.append(f"     risk: {m.risk}")
    return "\n".join(lines)


def structural_moves_as_lines(moves: list[StructuralMove]) -> list[str]:
    return [m.summary_line() for m in moves]


def pick_primary_structural_action(moves: list[StructuralMove]) -> dict[str, Any] | None:
    """Payload for propose_action — never auto-applied."""
    for m in moves:
        if m.parameter == "feed_stage" and m.com_writable:
            return {
                "kind": "structural_approval",
                "strategy_id": "feed_stage_change",
                "family": "F_structural",
                "requires_approval": True,
                "move_id": m.move_id,
                "parameter": m.parameter,
                "current": m.current,
                "proposed": m.proposed,
                "com_writable": m.com_writable,
                "description": (
                    f"APPROVAL REQUIRED (mechanical): feed stage {m.current} -> {m.proposed}. "
                    f"{m.reason}"
                ),
            }
    for m in moves:
        if m.com_writable:
            return {
                "kind": "structural_approval",
                "strategy_id": {
                    "stage_count": "stage_count_change",
                    "p_cond": "pressure_change",
                    "p_reb": "pressure_change",
                }.get(m.parameter, "feed_stage_change"),
                "family": "F_structural",
                "requires_approval": True,
                "move_id": m.move_id,
                "parameter": m.parameter,
                "current": m.current,
                "proposed": m.proposed,
                "com_writable": m.com_writable,
                "description": (
                    f"APPROVAL REQUIRED (mechanical): {m.parameter} "
                    f"{m.current} -> {m.proposed}. {m.reason}"
                ),
            }
    if moves:
        m = moves[0]
        return {
            "kind": "structural_approval",
            "strategy_id": "feed_or_case_change",
            "family": "F_structural",
            "requires_approval": True,
            "move_id": m.move_id,
            "parameter": m.parameter,
            "current": m.current,
            "proposed": m.proposed,
            "com_writable": False,
            "description": (
                f"MANUAL in HYSYS Connections (mechanical): {m.parameter} — {m.reason}"
            ),
        }
    return None

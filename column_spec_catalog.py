"""
HYSYS Column "Add Specs" catalog + when-to-add intelligence.

Source: Aspen HYSYS dialog "Add Specs - T-100 / COL1" /
"Column Specification Types" (user capture 2026-07-22).
Earlier SW Stripper capture remains as legacy stripper flags only.

Layer policy:
  - Catalog + recommend WHEN to add  → coded now
  - COM Specs.Add create             → not auto-executed until validated
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SpecFamily(str, Enum):
    ENERGY_REFLUX = "energy_reflux"
    DRAWS_FLOWS = "draws_flows"
    COMPOSITION = "composition"
    RECOVERY = "recovery"
    TEMPERATURE = "temperature"
    DUTY = "duty"
    PRESSURE_VP = "pressure_vp"
    PETROLEUM = "petroleum"
    HYDRAULIC_PA = "hydraulic_pa"
    PROPERTY = "property"
    OTHER = "other"


class AddPolicy(str, Enum):
    """How Assist may use this type."""

    EXISTING_ONLY = "existing_only"  # prefer specs already on column
    RECOMMEND_ADD = "recommend_add"  # may suggest user/HYSYS Add Spec
    AUTO_ADD_LATER = "auto_add_later"  # reserved when COM Add is validated
    RARE = "rare"  # uncommon for atmospheric CDU
    NOT_FOR_STRIPPER = "not_for_stripper"  # legacy stripper exclusion (CDU may still use)


@dataclass(frozen=True, slots=True)
class ColumnSpecTypeDef:
    """One row from HYSYS Add Specs dialog (exact type name)."""

    hysys_name: str
    family: SpecFamily
    short_id: str
    when_to_add: str
    pe_notes: str
    policy: AddPolicy = AddPolicy.RECOMMEND_ADD
    typical_for_sw_stripper: bool = False
    typical_for_cdu: bool = False
    # Names often seen after add (partial match) — includes T-100 Monitor tokens
    name_contains: tuple[str, ...] = ()
    # Example from T-100 Monitor / Connections when known
    t100_example: str = ""


# Exact HYSYS "Column Specification Types" list (Add Specs - T-100), order preserved.
HYSYS_ADD_SPEC_TYPES: list[ColumnSpecTypeDef] = [
    ColumnSpecTypeDef(
        "Column Cold Properties Spec",
        SpecFamily.PROPERTY,
        "cold_properties",
        "When naphtha / light product cold props (RVP, pour, freeze, cloud) are FINAL_TARGET.",
        "CDU: use as quality Monitor/Active only when plant buys cold-prop specs — "
        "do not spam-add while draw/PA set already closes DOF.",
        AddPolicy.RECOMMEND_ADD,
        typical_for_cdu=True,
        name_contains=("cold", "rvp", "pour", "freeze", "cloud"),
    ),
    ColumnSpecTypeDef(
        "Column Component Flow",
        SpecFamily.COMPOSITION,
        "comp_flow",
        "When a component molar/mass flow in a product must be fixed.",
        "CDU rare vs cut/draw; stripper may use NH3/H2S rate.",
        AddPolicy.RARE,
        name_contains=("component flow", "comp flow"),
    ),
    ColumnSpecTypeDef(
        "Column Component Fraction",
        SpecFamily.COMPOSITION,
        "comp_frac",
        "When product purity/impurity (mole/mass frac) is the FINAL_TARGET.",
        "Legacy SW Stripper primary (NH3). CDU: prefer petroleum cut/gap unless "
        "composition FINAL_TARGET is configured.",
        AddPolicy.EXISTING_ONLY,
        typical_for_cdu=False,
        name_contains=("mass frac", "mole frac", "comp frac", "nh3", "ammonia"),
    ),
    ColumnSpecTypeDef(
        "Column Component Ratio",
        SpecFamily.COMPOSITION,
        "comp_ratio",
        "When relative amounts of two components must be controlled.",
        "Rare on atmospheric CDU; more for multicomponent fractionation.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Component Recovery",
        SpecFamily.RECOVERY,
        "comp_recovery",
        "When % recovery of a key to a product is the design/contract basis.",
        "Alternative to fraction/cut when recovery is the plant language.",
        AddPolicy.RECOMMEND_ADD,
        name_contains=("recovery",),
    ),
    ColumnSpecTypeDef(
        "Column Cut Point",
        SpecFamily.PETROLEUM,
        "cut_point",
        "When ASTM/TBP cut temperature of a product is FINAL_TARGET or Active quality.",
        "CDU core quality type — prefer after draw/PA traffic is healthy; keep locked "
        "FINAL_TARGET out of free GoalValue spam.",
        AddPolicy.RECOMMEND_ADD,
        typical_for_cdu=True,
        name_contains=("cut point", "cut", "astm", "tbp", "d86"),
    ),
    ColumnSpecTypeDef(
        "Column Draw Rate",
        SpecFamily.DRAWS_FLOWS,
        "draw_rate",
        "When a product / side-stripper draw rate is a DOF (T-100: Kero/Diesel/AGO/Naphtha).",
        "CDU primary C_split family. T-100 already has side-stripper Prod Flow + Naphtha Prod Rate — "
        "prefer GoalValue nudge; Add only if a product draw type is missing.",
        AddPolicy.EXISTING_ONLY,
        typical_for_cdu=True,
        typical_for_sw_stripper=True,
        name_contains=(
            "prod flow",
            "prod rate",
            "draw",
            "ovhd",
            "btms",
            "residue",
            "kero_ss",
            "diesel_ss",
            "ago_ss",
            "naphtha",
        ),
        t100_example="Kero_SS / Diesel_SS / AGO_SS Prod Flow; Naphtha Prod Rate (USGPM)",
    ),
    ColumnSpecTypeDef(
        "Column DT (Heater/Cooler) Spec",
        SpecFamily.TEMPERATURE,
        "dt_heater",
        "When approach ΔT on an attached heater/cooler (incl. PA exchanger) is specified.",
        "Utility/equipment constraint — secondary to PA Rate/Duty on T-100.",
        AddPolicy.RARE,
        name_contains=("dt", "delta t", "approach"),
    ),
    ColumnSpecTypeDef(
        "Column Dt Spec",
        SpecFamily.TEMPERATURE,
        "dt_spec",
        "When a temperature difference between stages/streams is specified.",
        "Advanced; avoid for first-pass CDU convergence.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Duty",
        SpecFamily.DUTY,
        "duty",
        "When condenser, PA, or side-stripper reboiler duty is the energy DOF.",
        "T-100: PA_*_Duty(Pa), Kero Reb Duty, Atmos Cond — Family B_energy. "
        "Prefer existing Active duties before Add.",
        AddPolicy.EXISTING_ONLY,
        typical_for_cdu=True,
        typical_for_sw_stripper=True,
        name_contains=("duty", "cond", "reb", "pa_1_duty", "pa_2_duty", "pa_3_duty"),
        t100_example="PA_1/2/3_Duty(Pa) (Btu/hr); Kero Reb Duty",
    ),
    ColumnSpecTypeDef(
        "Column Duty Ratio",
        SpecFamily.DUTY,
        "duty_ratio",
        "When relative duties (e.g. PA / condenser) are fixed.",
        "Optional on multi-PA CDUs; T-100 uses absolute PA duties instead.",
        AddPolicy.RARE,
        typical_for_cdu=True,
    ),
    ColumnSpecTypeDef(
        "Column Feed Ratio",
        SpecFamily.DRAWS_FLOWS,
        "feed_ratio",
        "When product or reflux is specified as ratio to feed (capacity-flexible).",
        "Useful when crude rate swings; T-100 uses absolute USGPM draws today.",
        AddPolicy.RECOMMEND_ADD,
        name_contains=("feed ratio",),
    ),
    ColumnSpecTypeDef(
        "Column Gap Cut Point",
        SpecFamily.PETROLEUM,
        "gap_cut",
        "When gap between adjacent product cuts is FINAL_TARGET / quality Active.",
        "CDU neighbor-product control (D6) — Add if gap missing and plant buys gap.",
        AddPolicy.RECOMMEND_ADD,
        typical_for_cdu=True,
        name_contains=("gap",),
    ),
    ColumnSpecTypeDef(
        "Column Liquid Flow",
        SpecFamily.DRAWS_FLOWS,
        "liquid_flow",
        "When an internal / reflux / liquid circulation rate is specified.",
        "T-100 has Active 'Liquid Flow' (USGPM) — often internal traffic; "
        "distinguish from PA Rate and product Draw Rate.",
        AddPolicy.EXISTING_ONLY,
        typical_for_cdu=True,
        typical_for_sw_stripper=True,
        name_contains=("liquid flow", "reflux rate", "liquid"),
        t100_example="Liquid Flow = 102.1 USGPM (Active)",
    ),
    ColumnSpecTypeDef(
        "Column Physical Properties Spec",
        SpecFamily.PROPERTY,
        "phys_props",
        "When density / MW / other phys prop is the product target.",
        "Secondary to cut/draw on atmospheric CDU.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Pump Around",
        SpecFamily.HYDRAULIC_PA,
        "pump_around",
        "When PA circulation rate and/or duty (or ΔT) is a section-energy DOF.",
        "CDU primary B_energy. T-100: PA_1/2/3_Rate + Duty pairs already Active — "
        "Add only if a PA circuit has no spec type yet.",
        AddPolicy.EXISTING_ONLY,
        typical_for_cdu=True,
        name_contains=(
            "pump around",
            "pumparound",
            "pa_1",
            "pa_2",
            "pa_3",
            "pa rate",
            "pa duty",
            "pa circ",
        ),
        t100_example="PA_1_Rate(Pa)=1458 USGPM; PA_1_Duty(Pa)=-5.5e7 Btu/hr (+ PA_2/3)",
    ),
    ColumnSpecTypeDef(
        "Column Reboil Ratio Spec",
        SpecFamily.ENERGY_REFLUX,
        "reboil_ratio",
        "When boilup/reboil ratio is the stripping-side energy DOF.",
        "T-100 uses Kero Reb Duty rather than ratio; stripper may prefer this.",
        AddPolicy.RECOMMEND_ADD,
        typical_for_cdu=True,
        name_contains=("reboil", "boilup"),
    ),
    ColumnSpecTypeDef(
        "Column Recovery",
        SpecFamily.RECOVERY,
        "recovery",
        "Overall recovery-type specification.",
        "Prefer Component Recovery or Cut Point when key is clear.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Reflux Feed Ratio Spec",
        SpecFamily.ENERGY_REFLUX,
        "reflux_feed_ratio",
        "When reflux is specified as R/F (scale-friendly).",
        "Optional top-section energy; T-100 holds Reflux Ratio as Estimate only.",
        AddPolicy.RECOMMEND_ADD,
        name_contains=("reflux feed", "r/f"),
    ),
    ColumnSpecTypeDef(
        "Column Reflux Fraction Spec",
        SpecFamily.ENERGY_REFLUX,
        "reflux_fraction",
        "When reflux fraction (partial condenser) is specified.",
        "Check condenser type; T-100 condenser products Off Gas / Waste Water / Naphtha.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Reflux Ratio",
        SpecFamily.ENERGY_REFLUX,
        "reflux_ratio",
        "Top rectification energy DOF — often Estimate on CDU while draws/PAs are Active.",
        "T-100: Reflux Ratio Estimate (spec 1.0, current ~0.706) — prefer draw/PA/steam "
        "families before activating RR as primary MV.",
        AddPolicy.EXISTING_ONLY,
        typical_for_cdu=True,
        typical_for_sw_stripper=True,
        name_contains=("reflux ratio",),
        t100_example="Reflux Ratio = 1.0 Estimate / Current ~0.706 (not Active)",
    ),
    ColumnSpecTypeDef(
        "Column Stream Property Spec",
        SpecFamily.PROPERTY,
        "stream_property",
        "When an arbitrary stream property is the target.",
        "Flexible but opaque — prefer Draw / PA / Cut / Duty types.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Tee Split Spec",
        SpecFamily.OTHER,
        "tee_split",
        "When an associated tee split fraction is column-tied.",
        "Uncommon on atmospheric CDU main column.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Temperature",
        SpecFamily.TEMPERATURE,
        "temperature",
        "When a stage or product temperature is a DOF/constraint.",
        "Use for condenser/flash-zone / PA return T limits — not first for cut control.",
        AddPolicy.RECOMMEND_ADD,
        typical_for_cdu=True,
        name_contains=("temp", "temperature", "return t"),
    ),
    ColumnSpecTypeDef(
        "Column Transport Properties Spec",
        SpecFamily.PROPERTY,
        "transport_props",
        "Viscosity/conductivity-type targets.",
        "Not first-pass CDU convergence.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column User Property Spec",
        SpecFamily.PROPERTY,
        "user_property",
        "User-defined property target.",
        "Only if plant defines a custom HYSYS user property.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Vapour Flow",
        SpecFamily.DRAWS_FLOWS,
        "vapour_flow",
        "When vapour product / internal vapour rate is specified.",
        "T-100: Vap Prod Flow Active = 0 lbmole/hr (Off Gas held off) — "
        "related to overhead vapor product; do not confuse with liquid Naphtha Prod Rate.",
        AddPolicy.EXISTING_ONLY,
        typical_for_cdu=True,
        typical_for_sw_stripper=True,
        name_contains=("vap prod", "vapour flow", "vapor flow", "vap rate", "ovhd"),
        t100_example="Vap Prod Flow = 0 lbmole/hr (Active)",
    ),
    ColumnSpecTypeDef(
        "Column Vapour Fraction Spec",
        SpecFamily.PROPERTY,
        "vap_frac",
        "When vapour fraction of a product/stage is specified.",
        "Phase condition control — secondary on CDU.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Vapour Pressure Spec",
        SpecFamily.PRESSURE_VP,
        "vap_pressure",
        "When product Reid VP / vapour pressure is the target (naphtha RVP).",
        "CDU naphtha quality alternative to Cold Properties — Add if plant buys RVP.",
        AddPolicy.RECOMMEND_ADD,
        typical_for_cdu=True,
        name_contains=("vapour pressure", "vapor pressure", "rvp", "reid"),
    ),
    ColumnSpecTypeDef(
        "End Point Based Column Cut Point Spec",
        SpecFamily.PETROLEUM,
        "ep_cut",
        "When endpoint-based cut (EP / TBP end) is the product quality spec.",
        "CDU petroleum FINAL_TARGET family — prefer after traffic (draws/PAs) healthy.",
        AddPolicy.RECOMMEND_ADD,
        typical_for_cdu=True,
        name_contains=("end point", "endpoint", "ep cut"),
    ),
    ColumnSpecTypeDef(
        "End Point Based Column Gap Spec",
        SpecFamily.PETROLEUM,
        "ep_gap",
        "When endpoint-based gap between products is the quality spec.",
        "Neighbor-cut control — Add if gap missing and plant buys EP gap.",
        AddPolicy.RECOMMEND_ADD,
        typical_for_cdu=True,
        name_contains=("ep gap", "endpoint gap"),
    ),
    ColumnSpecTypeDef(
        "Stream Specification",
        SpecFamily.OTHER,
        "stream_spec",
        "Generic stream specification attached via column.",
        "Prefer explicit column types (Draw Rate, Pump Around, Cut Point, Duty).",
        AddPolicy.RARE,
    ),
]


def list_add_spec_names() -> list[str]:
    return [s.hysys_name for s in HYSYS_ADD_SPEC_TYPES]


def get_spec_type_by_name(hysys_name: str) -> ColumnSpecTypeDef | None:
    want = (hysys_name or "").strip().lower()
    for item in HYSYS_ADD_SPEC_TYPES:
        if item.hysys_name.lower() == want:
            return item
    return None


def format_add_spec_hysys_steps(hysys_type_name: str, *, column_hint: str = "T-100") -> str:
    """Exact HYSYS UI click path matching Design → Specs → Add… dialog."""
    item = get_spec_type_by_name(hysys_type_name)
    when = item.when_to_add if item else ""
    pe = item.pe_notes if item else ""
    lines = [
        f"ADD SPEC in HYSYS — {column_hint}",
        f"  Type: {hysys_type_name}",
        "  1. Open column → Design → Specs (or Monitor).",
        "  2. Click Add… (opens 'Add Specs' / Column Specification Types).",
        f"  3. Select: {hysys_type_name}",
        "  4. Click Add Spec(s)…",
        "  5. On Specs detail pane: set Spec Name, Specification Value, Active/Estimate,",
        "     Fixed/Ranged, attach stage/stream as HYSYS prompts.",
        "  6. If DOF was already 0: deactivate one other Active (1-for-1) before Activate.",
        "  7. Run → Inspect in Assist.",
    ]
    if when:
        lines.append(f"  When: {when}")
    if pe:
        lines.append(f"  PE: {pe}")
    return "\n".join(lines)


def get_spec_type(short_id: str) -> ColumnSpecTypeDef | None:
    for item in HYSYS_ADD_SPEC_TYPES:
        if item.short_id == short_id:
            return item
    return None


def match_existing_spec_to_type(spec_name: str) -> ColumnSpecTypeDef | None:
    lower = spec_name.lower()
    # Prefer more specific matches: longest name_contains token wins
    best: ColumnSpecTypeDef | None = None
    best_len = -1
    for item in HYSYS_ADD_SPEC_TYPES:
        for token in item.name_contains:
            if token in lower and len(token) > best_len:
                best = item
                best_len = len(token)
    return best


@dataclass(slots=True)
class AddSpecRecommendation:
    """Intelligence output: whether/which Add Spec to consider."""

    needed: bool
    hysys_type_name: str = ""
    short_id: str = ""
    reason: str = ""
    action: str = "none"  # none | use_existing | recommend_user_add | future_auto_add
    existing_spec_name: str | None = None


def recommend_add_spec(
    *,
    existing_spec_names: list[str],
    engineering_state: str,
    has_reflux_ratio: bool,
    has_composition_final_target: bool,
    physical_solution: bool,
    final_target_met: bool,
    weak_operating_response: bool = False,
    product_line: str = "cdu",
    has_petroleum_final_target: bool = False,
) -> list[AddSpecRecommendation]:
    """
    Decide if a missing HYSYS spec TYPE should be added.

    CDU (default): prefer existing draw / PA / reflux / cut set; recommend PA or
    Draw Rate when missing; never auto-Add when DOF tools already exist.

    Legacy stripper: RR + composition FINAL_TARGET; not petroleum/PA.
    """
    if product_line in {"sw_stripper", "simple_column", "legacy_stripper"}:
        return _recommend_add_spec_stripper(
            existing_spec_names=existing_spec_names,
            engineering_state=engineering_state,
            has_reflux_ratio=has_reflux_ratio,
            has_composition_final_target=has_composition_final_target,
            physical_solution=physical_solution,
            final_target_met=final_target_met,
            weak_operating_response=weak_operating_response,
        )
    return _recommend_add_spec_cdu(
        existing_spec_names=existing_spec_names,
        engineering_state=engineering_state,
        has_reflux_ratio=has_reflux_ratio,
        has_petroleum_final_target=has_petroleum_final_target,
        physical_solution=physical_solution,
        final_target_met=final_target_met,
        weak_operating_response=weak_operating_response,
    )


def _recommend_add_spec_cdu(
    *,
    existing_spec_names: list[str],
    engineering_state: str,
    has_reflux_ratio: bool,
    has_petroleum_final_target: bool,
    physical_solution: bool,
    final_target_met: bool,
    weak_operating_response: bool = False,
) -> list[AddSpecRecommendation]:
    recs: list[AddSpecRecommendation] = []
    names_l = [n.lower() for n in existing_spec_names]

    def has_token(*tokens: str) -> bool:
        return any(any(t in n for t in tokens) for n in names_l)

    has_draw = has_token(
        "draw",
        "ovhd",
        "btms",
        "bottoms",
        "residue",
        "kero",
        "diesel",
        "ago",
        "naphtha",
        "prod flow",
        "prod rate",
    )
    has_pa = has_token(
        "pump around",
        "pumparound",
        "pa duty",
        "pa circ",
        "pa_1",
        "pa_2",
        "pa_3",
        "pa rate",
    )

    if has_draw and (has_reflux_ratio or has_pa or has_petroleum_final_target):
        recs.append(
            AddSpecRecommendation(
                needed=False,
                reason=(
                    "CDU Active set present (draw and/or PA/reflux/cut) — "
                    "do not Add Spec; adjust Active/Goal or recover numerically."
                ),
                action="use_existing",
            )
        )

    if engineering_state.startswith("B") or not physical_solution:
        if has_draw or has_pa or has_token("reflux"):
            recs.append(
                AddSpecRecommendation(
                    needed=False,
                    hysys_type_name="Column Draw Rate / Column Pump Around",
                    short_id="draw_rate",
                    reason=(
                        "State B — use existing draw/PA/reflux as baseline Active "
                        "(1-for-1 swap). Do not add new specs until physical."
                    ),
                    action="use_existing",
                )
            )
        else:
            recs.append(
                AddSpecRecommendation(
                    needed=True,
                    hysys_type_name="Column Draw Rate",
                    short_id="draw_rate",
                    reason=(
                        "No draw-rate spec found — recommend Add Spec: Column Draw Rate "
                        "for a product draw (then pair with PA or reflux)."
                    ),
                    action="recommend_user_add",
                )
            )
        return recs

    if weak_operating_response and not final_target_met:
        if not has_pa:
            recs.append(
                AddSpecRecommendation(
                    needed=True,
                    hysys_type_name="Column Pump Around",
                    short_id="pump_around",
                    reason=(
                        "Weak response on current MVs / mid-cut miss — consider Add Spec: "
                        "Column Pump Around (duty/circ), then 1-for-1 Active. "
                        "COM auto-add not enabled."
                    ),
                    action="recommend_user_add",
                )
            )
        if not has_draw:
            recs.append(
                AddSpecRecommendation(
                    needed=True,
                    hysys_type_name="Column Draw Rate",
                    short_id="draw_rate",
                    reason="Missing side-draw rate — recommend Add Spec: Column Draw Rate.",
                    action="recommend_user_add",
                )
            )

    if not has_petroleum_final_target and not has_token("cut", "gap", "astm", "d86", "tbp"):
        recs.append(
            AddSpecRecommendation(
                needed=True,
                hysys_type_name="Column Cut Point / Gap Cut Point",
                short_id="cut_point",
                reason=(
                    "No petroleum cut/gap spec visible — recommend Add Spec for cut/gap "
                    "as Monitor (FINAL_TARGET stays external/locked; do not GoalValue-spam)."
                ),
                action="recommend_user_add",
            )
        )

    if not has_reflux_ratio and not has_token("reflux ratio"):
        recs.append(
            AddSpecRecommendation(
                needed=True,
                hysys_type_name="Column Reflux Ratio",
                short_id="reflux_ratio",
                reason="Missing Reflux Ratio — recommend Add Spec: Column Reflux Ratio (top section).",
                action="recommend_user_add",
            )
        )

    if not recs:
        recs.append(
            AddSpecRecommendation(
                needed=False,
                reason="No Add Spec recommended — work with existing specification set.",
                action="none",
            )
        )
    return recs


def _recommend_add_spec_stripper(
    *,
    existing_spec_names: list[str],
    engineering_state: str,
    has_reflux_ratio: bool,
    has_composition_final_target: bool,
    physical_solution: bool,
    final_target_met: bool,
    weak_operating_response: bool = False,
) -> list[AddSpecRecommendation]:
    """Legacy SW Stripper when-to-add (COM shell validation)."""
    recs: list[AddSpecRecommendation] = []
    names_l = [n.lower() for n in existing_spec_names]

    def has_token(*tokens: str) -> bool:
        return any(any(t in n for t in tokens) for n in names_l)

    if has_reflux_ratio and has_composition_final_target:
        recs.append(
            AddSpecRecommendation(
                needed=False,
                reason=(
                    "Reflux Ratio + composition FINAL_TARGET already present — "
                    "do not Add Spec; adjust Active/Goal or recover numerically."
                ),
                action="use_existing",
            )
        )

    if engineering_state.startswith("B") or not physical_solution:
        if has_token("ovhd", "vap rate", "btms", "reflux rate"):
            recs.append(
                AddSpecRecommendation(
                    needed=False,
                    hysys_type_name="Column Draw Rate / Column Liquid Flow",
                    short_id="draw_rate",
                    reason=(
                        "State B — use existing Ovhd/Btms/Reflux Rate as baseline Active "
                        "(1-for-1 swap). Do not add new specs until physical."
                    ),
                    action="use_existing",
                    existing_spec_name="Ovhd Vap Rate",
                )
            )
        else:
            recs.append(
                AddSpecRecommendation(
                    needed=True,
                    hysys_type_name="Column Draw Rate",
                    short_id="draw_rate",
                    reason=(
                        "No draw-rate spec found — recommend Add Spec: Column Draw Rate "
                        "(overhead or bottoms) for baseline DOF pair with reflux."
                    ),
                    action="recommend_user_add",
                )
            )
        return recs

    if weak_operating_response and not final_target_met:
        if not has_token("reboil", "boilup"):
            recs.append(
                AddSpecRecommendation(
                    needed=True,
                    hysys_type_name="Column Reboil Ratio Spec",
                    short_id="reboil_ratio",
                    reason=(
                        "Operating RR changes show weak effect on FINAL_TARGET — "
                        "consider Add Spec: Column Reboil Ratio (stripping energy), "
                        "then 1-for-1 Active with permission. COM auto-add not enabled."
                    ),
                    action="recommend_user_add",
                )
            )
        if not has_token("duty") or not has_token("reb"):
            recs.append(
                AddSpecRecommendation(
                    needed=True,
                    hysys_type_name="Column Duty",
                    short_id="duty",
                    reason=(
                        "Alternative Category-1 MV: Add Spec Column Duty (reboiler) "
                        "if plant handle is steam/duty rather than reflux."
                    ),
                    action="recommend_user_add",
                )
            )

    if not has_composition_final_target and not has_token("frac", "nh3", "ammonia"):
        recs.append(
            AddSpecRecommendation(
                needed=True,
                hysys_type_name="Column Component Fraction",
                short_id="comp_frac",
                reason=(
                    "No composition fraction spec — recommend Add Spec: "
                    "Column Component Fraction (e.g. NH3 in reboiler) as FINAL_TARGET."
                ),
                action="recommend_user_add",
            )
        )

    if not has_reflux_ratio and not has_token("reflux ratio"):
        recs.append(
            AddSpecRecommendation(
                needed=True,
                hysys_type_name="Column Reflux Ratio",
                short_id="reflux_ratio",
                reason="Missing Reflux Ratio — recommend Add Spec: Column Reflux Ratio.",
                action="recommend_user_add",
            )
        )

    if not recs:
        recs.append(
            AddSpecRecommendation(
                needed=False,
                reason="No Add Spec recommended — work with existing specification set.",
                action="none",
            )
        )
    return recs


def stripper_priority_add_types() -> list[ColumnSpecTypeDef]:
    """Legacy stripper priority order (COM shell)."""
    order = (
        "draw_rate",
        "pump_around",
        "cut_point",
        "gap_cut",
        "ep_cut",
        "ep_gap",
        "liquid_flow",
        "vapour_flow",
        "duty",
        "reflux_ratio",
        "vap_pressure",
        "temperature",
        "comp_recovery",
        "comp_frac",
        "reboil_ratio",
        "feed_ratio",
    )
    by_id = {s.short_id: s for s in HYSYS_ADD_SPEC_TYPES}
    return [by_id[i] for i in order if i in by_id]


def cdu_priority_add_types() -> list[ColumnSpecTypeDef]:
    """Atmospheric CDU Add Spec priority order (T-100 lesson)."""
    order = (
        "draw_rate",
        "pump_around",
        "duty",
        "liquid_flow",
        "vapour_flow",
        "reflux_ratio",
        "cut_point",
        "gap_cut",
        "ep_cut",
        "ep_gap",
        "cold_properties",
        "vap_pressure",
        "temperature",
        "reboil_ratio",
    )
    by_id = {s.short_id: s for s in HYSYS_ADD_SPEC_TYPES}
    return [by_id[i] for i in order if i in by_id]


@dataclass(slots=True)
class SpecsSummaryClick:
    """One HYSYS Specs Summary checkbox / value action for the PE."""

    spec_name: str
    set_active: bool | None = None
    set_estimate: bool | None = None
    sync_goal_from_current: bool = False
    reason: str = ""


def recommend_specs_summary_clicks(
    *,
    spec_rows: list[dict],
    engineering_state: str,
    bottoms_flow_kgmole_h: float | None,
    min_bottoms_flow_kgmole_h: float = 1.0,
    final_target_monitor_only: bool = True,
    nh3_is_final_target: bool | None = None,
) -> list[SpecsSummaryClick]:
    """
    Map State → Specs Summary clicks (Active / Estimate / Sync Current→Goal).

    Keep locked FINAL_TARGET specs as monitor/estimate (not Active DOF drivers)
    unless the user explicitly allows otherwise.
    """
    if nh3_is_final_target is not None:
        final_target_monitor_only = nh3_is_final_target

    clicks: list[SpecsSummaryClick] = []
    by_l = {str(r["name"]).lower(): r for r in spec_rows}

    def find(*tokens: str) -> dict | None:
        for name, row in by_l.items():
            if all(t in name for t in tokens):
                return row
        for name, row in by_l.items():
            if any(t in name for t in tokens):
                return row
        return None

    # CDU Specs Summary (T-100): keep RR Active OFF when draws/PAs already Active
    rr = find("reflux ratio")
    has_cdu_actives = any(
        any(t in n for t in ("pa_", "kero", "diesel", "ago", "naphtha", "prod flow", "prod rate"))
        and bool(r.get("is_active"))
        for n, r in by_l.items()
    )
    if rr and rr.get("is_active") and has_cdu_actives:
        clicks.append(
            SpecsSummaryClick(
                spec_name=str(rr["name"]),
                set_active=False,
                reason=(
                    "Specs Summary (T-100): uncheck Active on Reflux Ratio — "
                    "draws/PAs already hold DOF; prefer draw/PA GoalValue."
                ),
            )
        )

    ovhd = find("ovhd") or find("vap rate")
    btms = find("btms") or find("bottoms")
    nh3 = find("nh3") or find("ammonia")
    if rr is None:
        rr = find("reflux ratio")

    tiny_btms = (
        bottoms_flow_kgmole_h is not None
        and bottoms_flow_kgmole_h < min_bottoms_flow_kgmole_h
    )
    state_d = "D_" in engineering_state or engineering_state.endswith("constraint")
    state_b = "B_" in engineering_state or "numerical" in engineering_state.lower()

    if (state_d or tiny_btms) and ovhd and ovhd.get("is_active"):
        clicks.append(
            SpecsSummaryClick(
                spec_name=str(ovhd["name"]),
                set_active=False,
                reason="Uncheck Active on Ovhd Vap Rate — frees DOF; huge Ovhd drives dry bottoms.",
            )
        )
        if btms:
            clicks.append(
                SpecsSummaryClick(
                    spec_name=str(btms["name"]),
                    sync_goal_from_current=False,
                    set_active=True,
                    set_estimate=True,
                    reason=(
                        "Set Btms/residue Goal to a plant rate (≥ min flow), then check Active — "
                        "do not sync from tiny Current."
                    ),
                )
            )
        if rr and not rr.get("is_active") and not has_cdu_actives:
            clicks.append(
                SpecsSummaryClick(
                    spec_name=str(rr["name"]),
                    set_active=False,
                    set_estimate=True,
                    reason=(
                        "T-100/CDU: keep Reflux Ratio Active OFF on Specs Summary — "
                        "monitor/estimate only (not a DOF)."
                    ),
                )
            )

    # T-100 / CDU: Reflux Ratio monitor-only on Specs Summary
    if rr and final_target_monitor_only:
        if rr.get("is_active"):
            clicks.append(
                SpecsSummaryClick(
                    spec_name=str(rr["name"]),
                    set_active=False,
                    set_estimate=True,
                    reason=(
                        "Uncheck Active on Reflux Ratio — T-100 Specs Summary "
                        "pattern (monitor/estimate only)."
                    ),
                )
            )
        else:
            clicks.append(
                SpecsSummaryClick(
                    spec_name=str(rr["name"]),
                    set_active=False,
                    set_estimate=True,
                    reason=(
                        "Keep Reflux Ratio Active OFF — monitor/estimate only per "
                        "T-100 Specs Summary."
                    ),
                )
            )

    if quality and final_target_monitor_only and quality.get("is_active"):
        clicks.append(
            SpecsSummaryClick(
                spec_name=str(quality["name"]),
                set_active=False,
                set_estimate=True,
                reason=(
                    "Uncheck Active on quality/FINAL_TARGET spec — "
                    "monitor/estimate only, not DOF driver."
                ),
            )
        )
    elif quality and final_target_monitor_only and not quality.get("is_active"):
        clicks.append(
            SpecsSummaryClick(
                spec_name=str(quality["name"]),
                set_active=False,
                set_estimate=True,
                reason="Leave FINAL_TARGET quality Active OFF; Estimate ON — product check only.",
            )
        )

    if state_b:
        for row in spec_rows:
            if row.get("is_active"):
                continue
            name = str(row["name"])
            if any(t in name.lower() for t in ("ovhd", "btms", "reflux rate", "liquid")):
                clicks.append(
                    SpecsSummaryClick(
                        spec_name=name,
                        sync_goal_from_current=True,
                        set_estimate=True,
                        reason=f"State B: sync Current→Goal on '{name}' then Update Inactive / Estimate.",
                    )
                )
                break

    # Deduplicate by spec_name keeping first rich instruction
    seen: set[str] = set()
    unique: list[SpecsSummaryClick] = []
    for click in clicks:
        key = f"{click.spec_name}|{click.set_active}|{click.sync_goal_from_current}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(click)
    return unique


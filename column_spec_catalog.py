"""
HYSYS Column "Add Specs" catalog + when-to-add intelligence.

Source: Aspen HYSYS dialog "Add Specs - SW Stripper (COL1)" /
"Column Specification Types" (user capture 2026-07-21).

Layer policy:
  - Catalog + recommend WHEN to add  → coded now
  - COM Specs.Add create             → not auto-executed until validated
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
    RARE = "rare"  # almost never for SW Stripper
    NOT_FOR_STRIPPER = "not_for_stripper"


@dataclass(frozen=True, slots=True)
class ColumnSpecTypeDef:
    """One row from HYSYS Add Specs dialog."""

    hysys_name: str
    family: SpecFamily
    short_id: str
    when_to_add: str
    pe_notes: str
    policy: AddPolicy = AddPolicy.RECOMMEND_ADD
    typical_for_sw_stripper: bool = False
    # Names often seen after add (partial match)
    name_contains: tuple[str, ...] = ()


# Exact list from user's Add Specs screenshot (order preserved where visible).
HYSYS_ADD_SPEC_TYPES: list[ColumnSpecTypeDef] = [
    ColumnSpecTypeDef(
        "Column Cold Properties Spec",
        SpecFamily.PROPERTY,
        "cold_properties",
        "When cold properties (e.g. RVP-related cold props) are the product control.",
        "Uncommon for sour-water stripper NH3 duty.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Component Flow",
        SpecFamily.COMPOSITION,
        "comp_flow",
        "When a component molar/mass flow in a product must be fixed.",
        "Use if plant controls NH3 or H2S rate rather than fraction.",
        AddPolicy.RECOMMEND_ADD,
        name_contains=("component flow", "comp flow"),
    ),
    ColumnSpecTypeDef(
        "Column Component Fraction",
        SpecFamily.COMPOSITION,
        "comp_frac",
        "When product purity/impurity (mole/mass frac) is the FINAL_TARGET.",
        "SW Stripper primary product spec family — e.g. NH3 Mass Frac (Reboiler).",
        AddPolicy.EXISTING_ONLY,
        typical_for_sw_stripper=True,
        name_contains=("mass frac", "mole frac", "comp frac", "nh3", "ammonia"),
    ),
    ColumnSpecTypeDef(
        "Column Component Ratio",
        SpecFamily.COMPOSITION,
        "comp_ratio",
        "When relative amounts of two components must be controlled.",
        "Rare for simple stripper; more for multicomponent fractionation.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Component Recovery",
        SpecFamily.RECOVERY,
        "comp_recovery",
        "When % recovery of a key to overhead or bottoms is the design target.",
        "Alternative to fraction specs when recovery is the contract basis.",
        AddPolicy.RECOMMEND_ADD,
        name_contains=("recovery",),
    ),
    ColumnSpecTypeDef(
        "Column Cut Point",
        SpecFamily.PETROLEUM,
        "cut_point",
        "Petroleum TBP/cut-point product specs.",
        "Not typical for sour-water stripper.",
        AddPolicy.NOT_FOR_STRIPPER,
    ),
    ColumnSpecTypeDef(
        "Column Draw Rate",
        SpecFamily.DRAWS_FLOWS,
        "draw_rate",
        "When a product/side draw molar or mass rate is a DOF (Ovhd/Btms rate).",
        "SW Stripper uses Ovhd Vap Rate / Btms Prod Rate — baseline or split control.",
        AddPolicy.EXISTING_ONLY,
        typical_for_sw_stripper=True,
        name_contains=("ovhd", "btms", "draw", "prod rate", "vap rate"),
    ),
    ColumnSpecTypeDef(
        "Column DT (Heater/Cooler) Spec",
        SpecFamily.TEMPERATURE,
        "dt_heater",
        "When approach ΔT on an attached heater/cooler is specified.",
        "Utility/equipment constraint — not first purity lever.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Dt Spec",
        SpecFamily.TEMPERATURE,
        "dt_spec",
        "When a temperature difference between stages/streams is specified.",
        "Advanced; avoid for first-pass stripper convergence.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Duty",
        SpecFamily.DUTY,
        "duty",
        "When condenser or reboiler duty is the energy-side DOF.",
        "Category-1 MV alternative to reflux/boilup when duty is the plant handle.",
        AddPolicy.RECOMMEND_ADD,
        typical_for_sw_stripper=True,
        name_contains=("duty", "cond", "reb"),
    ),
    ColumnSpecTypeDef(
        "Column Duty Ratio",
        SpecFamily.DUTY,
        "duty_ratio",
        "When relative duties (e.g. PA / reboiler) are fixed.",
        "More for complex columns with pump-arounds.",
        AddPolicy.NOT_FOR_STRIPPER,
    ),
    ColumnSpecTypeDef(
        "Column Feed Ratio",
        SpecFamily.DRAWS_FLOWS,
        "feed_ratio",
        "When product or reflux is specified as ratio to feed.",
        "Useful for capacity-flexible cases; optional for stripper.",
        AddPolicy.RECOMMEND_ADD,
        name_contains=("feed ratio",),
    ),
    ColumnSpecTypeDef(
        "Column Gap Cut Point",
        SpecFamily.PETROLEUM,
        "gap_cut",
        "Petroleum gap/cut specifications.",
        "Not for sour-water stripper.",
        AddPolicy.NOT_FOR_STRIPPER,
    ),
    ColumnSpecTypeDef(
        "Column Liquid Flow",
        SpecFamily.DRAWS_FLOWS,
        "liquid_flow",
        "When an internal or draw liquid rate is specified (e.g. reflux rate).",
        "SW Stripper has Reflux Rate estimate — can be Active for baseline.",
        AddPolicy.EXISTING_ONLY,
        typical_for_sw_stripper=True,
        name_contains=("reflux rate", "liquid flow", "liquid"),
    ),
    ColumnSpecTypeDef(
        "Column Physical Properties Spec",
        SpecFamily.PROPERTY,
        "phys_props",
        "When a physical property (density, MW, etc.) is the target.",
        "Rare for NH3 stripping.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Pump Around",
        SpecFamily.HYDRAULIC_PA,
        "pump_around",
        "When pump-around rate/duty/ΔT is a DOF.",
        "Not applicable to simple SW Stripper without PA.",
        AddPolicy.NOT_FOR_STRIPPER,
    ),
    ColumnSpecTypeDef(
        "Column Reboil Ratio Spec",
        SpecFamily.ENERGY_REFLUX,
        "reboil_ratio",
        "When boilup/reboil ratio is the stripping-side energy DOF.",
        "Strong Category-1 alternative to reboiler duty for bottoms stripping.",
        AddPolicy.RECOMMEND_ADD,
        typical_for_sw_stripper=True,
        name_contains=("reboil", "boilup"),
    ),
    ColumnSpecTypeDef(
        "Column Recovery",
        SpecFamily.RECOVERY,
        "recovery",
        "Overall recovery-type specification.",
        "Prefer Component Recovery when key is clear.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Reflux Feed Ratio Spec",
        SpecFamily.ENERGY_REFLUX,
        "reflux_feed_ratio",
        "When reflux is specified as R/F.",
        "Scale-friendly energy spec; optional stripper baseline.",
        AddPolicy.RECOMMEND_ADD,
        name_contains=("reflux feed", "r/f"),
    ),
    ColumnSpecTypeDef(
        "Column Reflux Fraction Spec",
        SpecFamily.ENERGY_REFLUX,
        "reflux_fraction",
        "When reflux fraction (partial condenser related) is specified.",
        "Check condenser type; full-reflux stripper may not need it.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Reflux Ratio",
        SpecFamily.ENERGY_REFLUX,
        "reflux_ratio",
        "Default rectification/energy DOF for many columns including strippers.",
        "SW Stripper primary Category-1 MV — already present.",
        AddPolicy.EXISTING_ONLY,
        typical_for_sw_stripper=True,
        name_contains=("reflux ratio",),
    ),
    ColumnSpecTypeDef(
        "Column Stream Property Spec",
        SpecFamily.PROPERTY,
        "stream_property",
        "When an arbitrary stream property is the target.",
        "Flexible but opaque — prefer standard frac/duty/rate specs.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Tee Split Spec",
        SpecFamily.OTHER,
        "tee_split",
        "When an associated tee split fraction is column-tied.",
        "Not typical for standalone SW Stripper.",
        AddPolicy.NOT_FOR_STRIPPER,
    ),
    ColumnSpecTypeDef(
        "Column Temperature",
        SpecFamily.TEMPERATURE,
        "temperature",
        "When a stage or product temperature is a DOF/constraint.",
        "Use for condenser/reboiler T limits — not first for NH3 purity.",
        AddPolicy.RECOMMEND_ADD,
        name_contains=("temp", "temperature"),
    ),
    ColumnSpecTypeDef(
        "Column Transport Properties Spec",
        SpecFamily.PROPERTY,
        "transport_props",
        "Viscosity/conductivity-type targets.",
        "Not for stripper NH3 convergence.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column User Property Spec",
        SpecFamily.PROPERTY,
        "user_property",
        "User-defined property target.",
        "Only if plant defines a custom property.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Vapour Flow",
        SpecFamily.DRAWS_FLOWS,
        "vapour_flow",
        "When vapour draw/internal vapour rate is specified.",
        "Related to Ovhd Vap Rate family.",
        AddPolicy.EXISTING_ONLY,
        typical_for_sw_stripper=True,
        name_contains=("vap", "vapour", "vapor", "ovhd"),
    ),
    ColumnSpecTypeDef(
        "Column Vapour Fraction Spec",
        SpecFamily.PROPERTY,
        "vap_frac",
        "When vapour fraction of a product/stage is specified.",
        "Phase condition control — secondary for stripper.",
        AddPolicy.RARE,
    ),
    ColumnSpecTypeDef(
        "Column Vapour Pressure Spec",
        SpecFamily.PRESSURE_VP,
        "vap_pressure",
        "When product Reid VP / vapour pressure is the target.",
        "Stabilizer/debutanizer style — not NH3 stripper primary.",
        AddPolicy.NOT_FOR_STRIPPER,
    ),
    ColumnSpecTypeDef(
        "End Point Based Column Cut Point Spec",
        SpecFamily.PETROLEUM,
        "ep_cut",
        "Petroleum endpoint cut-point specs.",
        "Not for sour-water stripper.",
        AddPolicy.NOT_FOR_STRIPPER,
    ),
    ColumnSpecTypeDef(
        "End Point Based Column Gap Spec",
        SpecFamily.PETROLEUM,
        "ep_gap",
        "Petroleum endpoint gap specs.",
        "Not for sour-water stripper.",
        AddPolicy.NOT_FOR_STRIPPER,
    ),
    ColumnSpecTypeDef(
        "Stream Specification",
        SpecFamily.OTHER,
        "stream_spec",
        "Generic stream specification attached via column.",
        "Prefer explicit column spec types for clarity.",
        AddPolicy.RARE,
    ),
]


def list_add_spec_names() -> list[str]:
    return [s.hysys_name for s in HYSYS_ADD_SPEC_TYPES]


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
) -> list[AddSpecRecommendation]:
    """
    Decide if a missing HYSYS spec TYPE should be added.

    PE order for SW Stripper:
      1. Prefer existing Reflux Ratio + composition FINAL_TARGET
      2. If State B — prefer existing draw/liquid rate as baseline Active
      3. If weak RR response on stripping — recommend Reboil Ratio or Duty (user add)
      4. Never recommend petroleum/PA types for this stripper
    """
    recs: list[AddSpecRecommendation] = []
    names_l = [n.lower() for n in existing_spec_names]

    def has_token(*tokens: str) -> bool:
        return any(any(t in n for t in tokens) for n in names_l)

    # Already have the usual stripper set
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

    # State B: recommend using existing draw/liquid, not new exotic specs
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

    # Weak energy response while purity missed → recommend reboil/duty type if missing
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

    # Missing composition FINAL_TARGET entirely
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
    """Types most relevant to SW Stripper, in PE priority order."""
    order = (
        "reflux_ratio",
        "comp_frac",
        "draw_rate",
        "liquid_flow",
        "vapour_flow",
        "reboil_ratio",
        "duty",
        "comp_recovery",
        "temperature",
        "feed_ratio",
    )
    by_id = {s.short_id: s for s in HYSYS_ADD_SPEC_TYPES}
    return [by_id[i] for i in order if i in by_id]

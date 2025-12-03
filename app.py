from flask import Flask, render_template, request
from dc_access import DiabetesCostComparator
import pandas as pd
import math
import json

app = Flask(__name__)
# small secret for session usage if needed in future
app.secret_key = "dev-key-change-me"

# Set up the comparison engine using your CSV files
comparator = DiabetesCostComparator()


def format_money(value):
    """Format money: drop decimals when .00, otherwise show two decimals."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value if value is not None else ""
    # handle NaN (float('nan')) which cannot be converted to int
    if math.isnan(v):
        return ""
    if abs(v - int(v)) < 1e-9:
        return str(int(v))
    return f"{v:.2f}"


def build_pairings(selected_medicine, selected_insurance):
    """Build a list of pairings to show according to the user's selection.

    - both empty: return all pairings
    - only medicine: return that medicine paired with all insurances
    - only insurance: return that insurance paired with all medicines
    - both provided: return the single pairing
    """
    med_list = comparator.medicines_df["medicine_name"].tolist()
    ins_list = comparator.insurance_df["insurance_name"].tolist()

    pairings = []

    # helper to add a pairing
    def add_pair(med_name, ins_name):
        med_info = comparator.get_medicine_info(med_name)
        ins_info = comparator.get_insurance_info(ins_name)
        cov_info = comparator.get_coverage_info(ins_name, med_name)

        # calculate cost; pass dicts to be safe
        annual_cost = comparator.calculate_total_cost(
            med_info, ins_info, cov_info, months=12
        )
        monthly_cost = annual_cost / 12

        # full (uninsured) costs: prefer GoodRx price for cash if no insurance selected
        try:
            full_monthly = float(med_info.get("average_cost_per_month", 0))
        except Exception:
            full_monthly = 0.0

        # GoodRx explicit price (may be None)
        goodrx_price = None
        try:
            gr = med_info.get("goodrx_price")
            if gr is not None and gr != "" and not pd.isna(gr):
                goodrx_price = float(gr)
        except Exception:
            goodrx_price = None

        # if no insurance selected, prefer showing GoodRx as the full monthly
        if (not selected_insurance) and (goodrx_price is not None):
            full_monthly = goodrx_price
        full_annual = full_monthly * 12

        # copay if coverage exists
        copay_amount = None
        if (
            cov_info
            and ("copay_amount" in cov_info)
            and (cov_info.get("copay_amount") is not None)
        ):
            try:
                copay_amount = float(cov_info.get("copay_amount"))
            except Exception:
                copay_amount = None

        # savings = full - actual
        monthly_savings = None
        if copay_amount is not None:
            monthly_savings = full_monthly - copay_amount

        annual_savings = full_annual - annual_cost

        pairings.append(
            {
                "medicine_name": med_name,
                "insurance_name": ins_name,
                "medicine": med_info,
                "insurance": ins_info,
                "coverage": cov_info,
                "annual_cost": annual_cost,
                "monthly_cost": monthly_cost,
                "full_monthly": full_monthly,
                "full_annual": full_annual,
                "goodrx_price": goodrx_price,
                "goodrx_eligible": True if goodrx_price is not None else False,
                # unauthorized (no-prior-auth) annual price if configured; else None
                "unauth_annual": None,
                "copay_amount": copay_amount,
                "monthly_savings": monthly_savings,
                "annual_savings": annual_savings,
            }
        )

    if (not selected_medicine) and (not selected_insurance):
        # no filters → all combinations
        for m in med_list:
            for i in ins_list:
                add_pair(m, i)
    elif selected_medicine and (not selected_insurance):
        # one medicine → all insurances
        for i in ins_list:
            add_pair(selected_medicine, i)
    elif (not selected_medicine) and selected_insurance:
        # one insurance → all medicines
        for m in med_list:
            add_pair(m, selected_insurance)
    else:
        # both provided → single pairing
        add_pair(selected_medicine, selected_insurance)

    return pairings


def tier_num(tier_str):
    """Return numeric tier if possible, else None."""
    try:
        if not tier_str:
            return None
        # expect 'Tier 1', 'Tier 2', etc.
        return int(str(tier_str).strip().lower().replace('tier', '').strip())
    except Exception:
        return None


def build_coverage_map():
    """Return nested dict: coverage_map[medicine_name][insurance_name] = coverage dict or None."""
    coverage_map = {}
    for _, row in comparator.coverage_df.iterrows():
        med = row["medicine_name"]
        ins = row["insurance_name"]
        coverage_map.setdefault(med, {})[ins] = {
            "covered": row.get("covered"),
            "copay_amount": row.get("copay_amount"),
            "tier_level": row.get("tier_level"),
        }
    return coverage_map


@app.template_filter("money")
def money_filter(value):
    return format_money(value)


@app.route("/", methods=["GET", "POST"])
def index():
    # Get unique lists from your CSVs
    med_list = comparator.medicines_df["medicine_name"].tolist()
    ins_list = comparator.insurance_df["insurance_name"].tolist()

    selected_medicine = None
    selected_insurance = None
    current = None
    pairings = []
    tried_flag = False
    sort_by = request.args.get("sort_by") or None
    sort_order = request.args.get("order") or None
    # trial UI state exposed to template
    trial_question = None
    trial_index = 0
    # Trial sequence (medicine order to ask about)
    # Trial question order (updated per user request)
    TRIAL_SEQUENCE = [
        "Metformin",
        "Glipizide",
        "Invokana",
        "Januvia",
        "Tirzepatide",
        "Semaglutide",
        "Jardiance",
    ]
    # Map of (insurance_name, medicine_name) -> unauthorized (no prior auth) annual price when available
    UNAUTHORIZED_COSTS = {
        ("Cigna", "Empagliflozin"): 811.0,
        ("Cigna", "Januvia"): 721.0,
    }

    if request.method == "POST":
        # distinguish the trial-flow POST from other POSTs (View / compare forms)
        trial_action = request.form.get("trial_action")
        skip_build_results = False
        show_all_after_trial = False
        # only read trial fields when the trial form was submitted
        if trial_action == "trial":
            trial_answer = request.form.get("trial_answer")
            try:
                trial_index = int(request.form.get("trial_index") or 0)
            except Exception:
                trial_index = 0

            # If the user answered a trial question, use that to set the selected medicine or advance
            if trial_answer is not None:
                if str(trial_answer).strip().lower() == "no":
                    # user hasn't tried this med -> show pairings for this med
                    if trial_index < len(TRIAL_SEQUENCE):
                        selected_medicine = TRIAL_SEQUENCE[trial_index]
                    else:
                        selected_medicine = None
                else:
                    # user has tried -> advance to next question
                    trial_index += 1
                    if trial_index < len(TRIAL_SEQUENCE):
                        trial_question = TRIAL_SEQUENCE[trial_index]
                        # don't build results yet; wait for a 'No' or the sequence to finish
                        skip_build_results = True
                    else:
                        # user tried all medicines -> show all options
                        selected_medicine = None
                        show_all_after_trial = True
        else:
            # Not a trial action — ensure we don't accidentally read trial_index from unrelated forms
            trial_index = 0

        # regular form fields (only use if not set by trial flow)
        selected_medicine = selected_medicine or request.form.get("medicine") or None
        selected_insurance = request.form.get("insurance") or None
        tried_flag = True if request.form.get("tried") == "on" else False
        # sorting choices from the form
        sort_by = request.form.get("sort_by") or "annual"
        sort_order = request.form.get("order") or "asc"

        # If we should skip building results (user answered Yes and we advanced), don't build pairings
        if skip_build_results and (not show_all_after_trial):
            # leave pairings empty and surface the next trial question
            pairings = []
        else:
            # Case 1: both selected -> show that exact combo on top,
            # and show ALL OTHER insurance options for that medicine below (no filter).
            if selected_medicine and selected_insurance:
                # current (top card)
                med_info = comparator.get_medicine_info(selected_medicine)
                ins_info = comparator.get_insurance_info(selected_insurance)
                cov_info = comparator.get_coverage_info(
                    selected_insurance, selected_medicine
                )

                if med_info and ins_info:
                    annual_cost = comparator.calculate_total_cost(
                        med_info, ins_info, cov_info, months=12
                    )
                    current = {
                        "medicine": med_info,
                        "insurance": ins_info,
                        "coverage": cov_info,
                        "annual_cost": annual_cost,
                        "monthly_cost": annual_cost / 12,
                    }

                # build all pairings for THIS medicine with ALL insurances
                all_for_med = build_pairings(selected_medicine, None)

                # show all options except the exact current selection
                pairings = [
                    p
                    for p in all_for_med
                    if not (
                        p["medicine_name"] == selected_medicine
                        and p["insurance_name"] == selected_insurance
                    )
                ]

                # populate unauthorized annual prices where configured
                for p in pairings:
                    try:
                        unauth = UNAUTHORIZED_COSTS.get((p.get('insurance_name'), p.get('medicine_name')))
                        p['unauth_annual'] = float(unauth) if unauth is not None else p.get('full_annual')
                    except Exception:
                        p['unauth_annual'] = p.get('full_annual')

                # If user marked 'tried', flag pairings that are higher tier than the selected med
                if tried_flag:
                    for p in pairings:
                        try:
                            sel_cov = comparator.get_coverage_info(p["insurance_name"], selected_medicine)
                            sel_t = tier_num(sel_cov.get("tier_level") if sel_cov else None)
                            p_cov = p.get("coverage")
                            p_t = tier_num(p_cov.get("tier_level") if p_cov else None)
                            p["is_higher_tier"] = (
                                (p_t is not None and sel_t is not None and p_t > sel_t)
                            )
                        except Exception:
                            p["is_higher_tier"] = False

                # Note: GoodRx cash option is handled in the broad-query branch where insurance is blank

                # sort pairings according to chosen criteria
                def _key(p):
                    if sort_by == "medicine":
                        return (p.get("medicine_name") or "").lower()
                    if sort_by == "insurance":
                        return (p.get("insurance_name") or "").lower()
                    if sort_by == "monthly":
                        return p.get("monthly_cost") if p.get("monthly_cost") is not None else float('inf')
                    if sort_by == "savings":
                        # sort by annual savings (higher savings first by default)
                        return p.get("annual_savings") if p.get("annual_savings") is not None else -float('inf')
                    # default: annual
                    return p.get("annual_cost") if p.get("annual_cost") is not None else float('inf')

                reverse = True if sort_order == "desc" else False
                pairings.sort(key=_key, reverse=reverse)

            # Case 2: broad query (one or both fields left blank)
            # Keep showing all combinations (the UI defaults to showing all insurances);
            # if a specific medicine was selected, narrow to that medicine (but keep all insurances)
            else:
                # if the trial flow finished and user tried all meds, show all pairs
                if show_all_after_trial:
                    all_pairs = build_pairings(None, None)
                    pairings = all_pairs
                else:
                    all_pairs = build_pairings(selected_medicine, selected_insurance)
                    pairings = all_pairs
                # If the user selected a medicine but left insurance blank, offer a GoodRx cash row
                if selected_medicine and (not selected_insurance):
                    med_info = comparator.get_medicine_info(selected_medicine)
                    if med_info and med_info.get("goodrx_price") and not pd.isna(med_info.get("goodrx_price")):
                        try:
                            gr_annual = comparator.calculate_total_cost(med_info, None, None, months=12)
                            pairings.insert(0, {
                                "medicine_name": selected_medicine,
                                "insurance_name": "GoodRx (CVS - DC)",
                                "medicine": med_info,
                                "insurance": None,
                                "coverage": None,
                                "annual_cost": gr_annual,
                                "monthly_cost": gr_annual / 12,
                                "full_monthly": float(med_info.get("goodrx_price")),
                                "full_annual": float(med_info.get("goodrx_price")) * 12,
                                "copay_amount": None,
                                "monthly_savings": None,
                                "annual_savings": None,
                                "is_cash": True,
                            })
                        except Exception:
                            pass
                # if user selected a medicine and marked 'tried', flag higher-tier suggestions
                if tried_flag and selected_medicine:
                    for p in pairings:
                        try:
                            sel_cov = comparator.get_coverage_info(p["insurance_name"], selected_medicine)
                            sel_t = tier_num(sel_cov.get("tier_level") if sel_cov else None)
                            p_cov = p.get("coverage")
                            p_t = tier_num(p_cov.get("tier_level") if p_cov else None)
                            p["is_higher_tier"] = (
                                (p_t is not None and sel_t is not None and p_t > sel_t)
                            )
                        except Exception:
                            p["is_higher_tier"] = False
                # populate unauthorized (no-prior-auth) prices for broad results
                for p in pairings:
                    try:
                        unauth = UNAUTHORIZED_COSTS.get((p.get('insurance_name'), p.get('medicine_name')))
                        p['unauth_annual'] = float(unauth) if unauth is not None else p.get('full_annual')
                    except Exception:
                        p['unauth_annual'] = p.get('full_annual')

                def _key(p):
                    if sort_by == "medicine":
                        return (p.get("medicine_name") or "").lower()
                    if sort_by == "insurance":
                        return (p.get("insurance_name") or "").lower()
                    if sort_by == "monthly":
                        return p.get("monthly_cost") if p.get("monthly_cost") is not None else float('inf')
                    if sort_by == "savings":
                        return p.get("annual_savings") if p.get("annual_savings") is not None else -float('inf')
                    return p.get("annual_cost") if p.get("annual_cost") is not None else float('inf')

                reverse = True if sort_order == "desc" else False
                pairings.sort(key=_key, reverse=reverse)

    # coverage map for client-side dropdown annotations
    coverage_map = build_coverage_map()

    return render_template(
        "index.html",
        medicines=med_list,
        insurances=ins_list,
        selected_medicine=selected_medicine,
        selected_insurance=selected_insurance,
        current=current,
        pairings=pairings,
        coverage_map=json.dumps(coverage_map),
        trial_question=trial_question,
        trial_index=trial_index,
        trial_sequence=TRIAL_SEQUENCE,
    )


if __name__ == "__main__":
    # this only runs on your own computer (localhost)
    app.run(debug=True)

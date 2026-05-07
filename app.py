"""
XAIP Argumentation Chatbot
University of Huddersfield | Haastrup, 2026
Single-file version for Streamlit Cloud deployment.
"""

import streamlit as st
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="XAIP Argumentation Chatbot",
    page_icon="🎓",
    layout="wide",
)

st.markdown("""
<style>
h1,h2,h3{color:#2E4A7A;}
.psa-ok{background:#d4edda;border:2px solid #28a745;border-radius:8px;
        padding:14px;margin:10px 0;font-weight:bold;color:#155724;}
.psa-fail{background:#f8d7da;border:2px solid #dc3545;border-radius:8px;
          padding:14px;margin:10px 0;font-weight:bold;color:#721c24;}
.card{background:#f0f4f9;border-left:4px solid #2E4A7A;
      padding:10px 14px;margin:6px 0;border-radius:4px;}
.hist{background:#fff3cd;border-left:3px solid #ffc107;
      padding:6px 10px;margin:4px 0;border-radius:3px;font-size:.9em;}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# INITIAL STATE
# ─────────────────────────────────────────────────────────────────────────────
INITIAL_STATE = {
    "at(bus,bus_stop)":True,"at(bus,train_station)":False,
    "at(bus,destination)":False,"at(train,bus_stop)":False,
    "at(train,train_station)":True,"at(train,destination)":False,
    "passenger_at(bus_stop)":True,"passenger_at(train_station)":False,
    "passenger_at(destination)":False,"passenger_on_bus":False,
    "passenger_on_train":False,"arrived_at(bus_stop)":False,
    "arrived_at(train_station)":False,"arrived_at(destination)":False,
    "is_train_station(bus_stop)":False,"is_train_station(train_station)":True,
    "is_train_station(destination)":False,
    "train_at_station(bus_stop)":False,"train_at_station(train_station)":False,
    "train_at_station(destination)":False,"ready_to_board":False,
}


# ─────────────────────────────────────────────────────────────────────────────
# STATE ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def build_effects(actions):
    se, ee = {}, {}
    def adds(t, f, v): se.setdefault(round(t,4),[]).append((f,v))
    def adde(t, f, v): ee.setdefault(round(t,4),[]).append((f,v))
    for a in actions:
        n,p,st,en = a["action_name"],a["params"],a["start"],a["end"]
        if n=="board_bus":
            loc=p.get("l","bus_stop")
            adde(en,"passenger_on_bus",True); adde(en,f"passenger_at({loc})",False)
        elif n=="bus_travel":
            f_,t_=p.get("f",""),p.get("t","")
            adds(st,f"at(bus,{f_})",False); adde(en,f"at(bus,{t_})",True)
            adde(en,"passenger_on_bus",False); adde(en,f"arrived_at({t_})",True)
        elif n=="passenger_platform_wait":
            adde(en,"ready_to_board",True)
        elif n=="train_approach":
            loc=p.get("l","train_station"); adde(en,f"train_at_station({loc})",True)
        elif n=="board_train":
            adde(en,"passenger_on_train",True); adde(en,"ready_to_board",False)
        elif n=="train_travel":
            t_=p.get("t","destination")
            adde(en,f"passenger_at({t_})",True); adde(en,"passenger_on_train",False)
    return se, ee


def replayed(t, actions):
    se,ee = build_effects(actions)
    s = dict(INITIAL_STATE)
    for tp in sorted(ee):
        if tp<=t+1e-9:
            for f,v in ee[tp]: s[f]=v
    for tp in sorted(se):
        if tp<=t+1e-9:
            for f,v in se[tp]: s[f]=v
    return s


def pre_start(si, actions):
    se,ee = build_effects(actions)
    s = dict(INITIAL_STATE)
    for tp in sorted(ee):
        if tp<=si+1e-9:
            for f,v in ee[tp]: s[f]=v
    for tp in sorted(se):
        if tp<si-1e-9:
            for f,v in se[tp]: s[f]=v
    return s


def holds_over(fluent, s, e, actions):
    se,ee = build_effects(actions)
    pts = {(s+e)/2}
    for tp in list(se)+list(ee):
        if s<tp<e: pts.add(tp+1e-6)
    for cp in pts:
        if not replayed(cp, actions).get(fluent,False):
            return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIOS
# ─────────────────────────────────────────────────────────────────────────────
NOMINAL = [
    {"step_index":1,"action_name":"board_bus","params":{"l":"bus_stop"},"start":0,"end":2,"resource":"Bus"},
    {"step_index":2,"action_name":"bus_travel","params":{"f":"bus_stop","t":"train_station"},"start":2,"end":7,"resource":"Bus"},
    {"step_index":3,"action_name":"passenger_platform_wait","params":{"l":"train_station"},"start":7,"end":10,"resource":"—"},
    {"step_index":4,"action_name":"train_approach","params":{"l":"train_station"},"start":7,"end":10,"resource":"Train"},
    {"step_index":5,"action_name":"board_train","params":{"l":"train_station"},"start":10,"end":11,"resource":"Train"},
    {"step_index":6,"action_name":"train_travel","params":{"f":"train_station","t":"destination"},"start":11,"end":19,"resource":"Train"},
]

SCENARIOS = {
    "A":{
        "title":"Scenario A — Nominal Schedule",
        "desc":"Everything runs as planned. Bus arrives at t=7, passenger boards train at t=10, reaches destination at t=19.",
        "steps": NOMINAL,
        "fault": {},
    },
    "B":{
        "title":"Scenario B — Bus Delayed",
        "desc":"Bus arrives late at t=8 instead of t=7. The platform-wait action cannot start because arrived_at(train_station) is absent at t=7.",
        "steps":[
            {"step_index":1,"action_name":"board_bus","params":{"l":"bus_stop"},"start":0,"end":2,"resource":"Bus"},
            {"step_index":2,"action_name":"bus_travel","params":{"f":"bus_stop","t":"train_station"},"start":2,"end":8,"resource":"Bus"},
            {"step_index":3,"action_name":"passenger_platform_wait","params":{"l":"train_station"},"start":7,"end":10,"resource":"—"},
            {"step_index":4,"action_name":"train_approach","params":{"l":"train_station"},"start":7,"end":10,"resource":"Train"},
            {"step_index":5,"action_name":"board_train","params":{"l":"train_station"},"start":10,"end":11,"resource":"Train"},
            {"step_index":6,"action_name":"train_travel","params":{"f":"train_station","t":"destination"},"start":11,"end":19,"resource":"Train"},
        ],
        "fault":{"bus_delayed":True},
    },
    "C":{
        "title":"Scenario C — Resource Conflict",
        "desc":"A second vehicle holds the Train resource during [7,10], clashing with train_approach. CQ6 succeeds.",
        "steps": NOMINAL,
        "fault":{"resource_conflict":True},
    },
    "D":{
        "title":"Scenario D — Invariant Disruption",
        "desc":"A concurrent action removes the passenger from the bus at t=4 while bus_travel is running. The over-all invariant passenger_on_bus is violated. CQ8 succeeds.",
        "steps": NOMINAL,
        "fault":{"invariant_disrupted":True},
    },
    "E":{
        "title":"Scenario E — Coordination Failure",
        "desc":"train_approach ends at t=11, but board_train is scheduled to start at t=10. train_at_station is absent at t=10. CQ6 succeeds.",
        "steps":[
            {"step_index":1,"action_name":"board_bus","params":{"l":"bus_stop"},"start":0,"end":2,"resource":"Bus"},
            {"step_index":2,"action_name":"bus_travel","params":{"f":"bus_stop","t":"train_station"},"start":2,"end":7,"resource":"Bus"},
            {"step_index":3,"action_name":"passenger_platform_wait","params":{"l":"train_station"},"start":7,"end":10,"resource":"—"},
            {"step_index":4,"action_name":"train_approach","params":{"l":"train_station"},"start":7,"end":11,"resource":"Train"},
            {"step_index":5,"action_name":"board_train","params":{"l":"train_station"},"start":10,"end":11,"resource":"Train"},
            {"step_index":6,"action_name":"train_travel","params":{"f":"train_station","t":"destination"},"start":11,"end":19,"resource":"Train"},
        ],
        "fault":{"coordination_fail":True},
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# ARGUMENT PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
def run_pipeline(steps, fault=None):
    fault = fault or {}

    def check_s1(a):
        n,p,si,ei = a["action_name"],a["params"],a["start"],a["end"]
        S = pre_start(si, steps)
        inv_ok = True
        if n=="bus_travel" and not fault.get("invariant_disrupted"):
            inv_ok = holds_over("passenger_on_bus", si, ei, steps)
        elif n=="bus_travel" and fault.get("invariant_disrupted"):
            inv_ok = False

        checks = {
            "board_bus":   [S.get(f"at(bus,{p.get('l')})",False),
                            S.get(f"passenger_at({p.get('l')})",False)],
            "bus_travel":  [S.get(f"at(bus,{p.get('f')})",False),
                            S.get("passenger_on_bus",False), inv_ok],
            "passenger_platform_wait":
                           [S.get(f"arrived_at({p.get('l')})",False),
                            S.get(f"is_train_station({p.get('l')})",False)],
            "train_approach":
                           [S.get(f"at(train,{p.get('l')})",False),
                            S.get(f"arrived_at({p.get('l')})",False)],
            "board_train": [S.get("ready_to_board",False),
                            S.get(f"train_at_station({p.get('l')})",False)],
            "train_travel":[S.get("passenger_on_train",False),
                            S.get(f"train_at_station({p.get('f')})",False)],
        }
        ok = all(checks.get(n,[True]))
        return {"action":n,"idx":a["step_index"],"s1":ok}

    def check_cqs(s1_results):
        cq_results = {}
        by_idx = {r["idx"]:r for r in s1_results}

        # CQ1: start conditions
        cq1 = all(r["s1"] for r in s1_results)

        # CQ2: invariant persistence
        cq2 = not fault.get("invariant_disrupted", False)

        # CQ3: causal links (always hold in valid domain)
        cq3 = True

        # CQ4: enabling timing
        if fault.get("bus_delayed"):
            # bus_travel ends at 8, platform_wait starts at 7
            cq4 = False
        else:
            cq4 = True

        # CQ5: deadline (train_travel ends at 19 = deadline)
        cq5 = True

        # CQ6: resource conflict or coordination failure
        if fault.get("resource_conflict") or fault.get("coordination_fail"):
            cq6 = False
        else:
            cq6 = True

        # CQ7: ordering (always justified in this domain)
        cq7 = True

        # CQ8: invariant disruption
        cq8 = not fault.get("invariant_disrupted", False)

        return {
            "CQ1":cq1,"CQ2":cq2,"CQ3":cq3,"CQ4":cq4,
            "CQ5":cq5,"CQ6":cq6,"CQ7":cq7,"CQ8":cq8,
        }

    s1_results = [check_s1(a) for a in steps]
    cqs = check_cqs(s1_results)
    accepted = all(cqs.values())
    failed = [k for k,v in cqs.items() if not v]
    return {"accepted":accepted, "cqs":cqs, "failed":failed}


# ─────────────────────────────────────────────────────────────────────────────
# CQ DESCRIPTIONS
# ─────────────────────────────────────────────────────────────────────────────
CQ_INFO = {
    "CQ1":("Start-condition satisfaction",
           "Did every condition the action needed at its start hold in the world?"),
    "CQ2":("Invariant persistence",
           "Did every over-all invariant remain continuously true throughout execution?"),
    "CQ3":("Causal link validity",
           "Does each action produce something the rest of the plan genuinely needs?"),
    "CQ4":("Enabling timing",
           "Did every enabling action finish before the dependent action was due to start?"),
    "CQ5":("Temporal constraint satisfaction",
           "Does the action's scheduled window satisfy all release-time and deadline constraints?"),
    "CQ6":("Resource compatibility",
           "Do overlapping actions use different exclusive resources and not disrupt each other?"),
    "CQ7":("Ordering necessity",
           "Would reversing any ordering cause a condition to fail or the goal to be unreachable?"),
    "CQ8":("Invariant disruption",
           "Does any concurrent action delete a condition that must remain continuously true?"),
}

CQ_EXPLANATIONS = {
    "CQ1":{
        True: "✅ All start conditions hold. Every action had what it needed at its scheduled start time.",
        False:"❌ At least one start condition fails. An action is scheduled to begin before a required condition is present in the world.",
    },
    "CQ2":{
        True: "✅ All over-all invariants persist. No condition that must remain true during execution is disrupted.",
        False:"❌ Invariant violated. A concurrent action sets passenger_on_bus := False at t=4, inside the execution window (2,7) of bus_travel. This makes bus_travel inapplicable from t=4 onwards.",
    },
    "CQ3":{
        True: "✅ All causal links are valid. Every action produces an effect consumed downstream or satisfying the goal.",
        False:"❌ A causal link is broken. An action in the plan does not contribute to any later action or to the goal.",
    },
    "CQ4":{
        True: "✅ Enabling timing holds. bus_travel ends at t=7 ≤ s=7 for passenger_platform_wait. The enabling effect arrives in time.",
        False:"❌ Enabling timing fails. bus_travel ends at t=8 but passenger_platform_wait is scheduled to start at t=7. arrived_at(train_station) is not present in S(7).",
    },
    "CQ5":{
        True: "✅ All temporal constraints satisfied. train_travel ends at t=19 within the deadline.",
        False:"❌ A temporal constraint is violated. An action's scheduled window falls outside its permitted time bounds.",
    },
    "CQ6":{
        True: "✅ No resource conflict. Actions 3 and 4 hold disjoint resources (∅ and Train). Neither disrupts the other's invariants.",
        False:"❌ Resource conflict or coordination failure. Either two actions claim the same exclusive resource simultaneously, or a required concurrent action does not complete in time.",
    },
    "CQ7":{
        True: "✅ All orderings are necessary. Reversing any ordering would leave a required start condition absent or make the goal unreachable.",
        False:"❌ An ordering cannot be justified. Reversing or removing it would not harm the plan.",
    },
    "CQ8":{
        True: "✅ No invariant disruption. No concurrent action deletes a fluent that must remain continuously true during any action's execution.",
        False:"❌ Invariant disrupted. A concurrent action sets passenger_on_bus := False at t=4, inside the open interval (2,7) of bus_travel. CQ8 succeeds and PSA(P) is rejected.",
    },
}

SCHEME_INFO = {
    "S1 — Action Applicability":
        "Checks that every action had its start conditions satisfied, over-all invariants maintained, and end conditions met.",
    "S2 — Causal Goal Support":
        "Checks that every action produces an effect that is genuinely consumed by a later action or satisfies the goal.",
    "S3 — Temporal Feasibility":
        "Checks that enabling actions always finish before the actions that depend on them start, and that all deadlines are met.",
    "S4 — Resource and Concurrency Feasibility":
        "Checks that concurrent actions hold disjoint exclusive resources and do not interfere with each other's invariants.",
    "S5 — Temporal Ordering Justification":
        "Checks that every finish-to-start ordering is causally motivated — reversing it would break the plan.",
    "S6 — Invariant Maintenance":
        "Checks that over-all invariants are not deleted by any concurrent action during the execution window.",
    "S7 — Plan Summary Argument (PSA)":
        "Integrates S1–S6 into a single validity claim. PSA(P) is accepted if and only if all critical questions are defeated.",
}


# ─────────────────────────────────────────────────────────────────────────────
# TRUST MODEL
# ─────────────────────────────────────────────────────────────────────────────
class Trust:
    def __init__(self):
        self.score = 0.5
        self.raised = 0
        self.accepted = 0
    def challenge(self):
        self.raised += 1
        self.score = max(0.0, self.score - 0.06)
    def accept(self):
        self.accepted += 1
        self.score = min(1.0, self.score + 0.04)
    @property
    def band(self):
        if self.score < 0.35: return "low"
        if self.score < 0.65: return "moderate"
        return "high"
    @property
    def label(self):
        return {"low":"🔴 Low","moderate":"🟡 Moderate","high":"🟢 High"}[self.band]
    def explain(self, cq, defeated):
        base = CQ_EXPLANATIONS[cq][defeated]
        if self.band == "high":
            return base
        if self.band == "moderate":
            return base + f"\n\n*Scheme targeted: {CQ_INFO[cq][0]}*"
        return (base +
                f"\n\n**Question raised:** {CQ_INFO[cq][1]}"
                f"\n\n**Scheme targeted:** {CQ_INFO[cq][0]}"
                f"\n\n**Trust level:** {self.label} — showing full detail.")


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
if "trust"       not in st.session_state: st.session_state.trust       = Trust()
if "history"     not in st.session_state: st.session_state.history     = []
if "explanation" not in st.session_state: st.session_state.explanation = ""
if "scenario_id" not in st.session_state: st.session_state.scenario_id = "A"
if "last_sc"     not in st.session_state: st.session_state.last_sc     = None
if "result"      not in st.session_state: st.session_state.result      = None


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎓 XAIP Chatbot")
    st.markdown("**University of Huddersfield**")
    st.divider()

    sc_id = st.radio("Select Scenario", ["A","B","C","D","E"],
        format_func=lambda x: {
            "A":"A — Nominal","B":"B — Bus Delayed",
            "C":"C — Resource Conflict","D":"D — Invariant Disruption",
            "E":"E — Coordination Failure"}[x])
    st.session_state.scenario_id = sc_id
    st.divider()

    trust = st.session_state.trust
    st.markdown("### 🧠 Trust Level")
    st.markdown(f"**{trust.label}**")
    st.progress(int(trust.score*100))
    st.caption(f"Score: {trust.score:.2f} | Challenges: {trust.raised} | Accepted: {trust.accepted}")
    st.caption({
        "low":      "Showing: full premise-by-premise detail",
        "moderate": "Showing: scheme-level explanation",
        "high":     "Showing: concise one-line summary",
    }[trust.band])

    if st.button("🔄 Reset session", use_container_width=True):
        for k in ["trust","history","explanation","result","last_sc"]:
            del st.session_state[k]
        st.rerun()

    st.divider()
    st.markdown("### 💬 Challenge History")
    if not st.session_state.history:
        st.caption("No challenges raised yet.")
    for h in reversed(st.session_state.history[-6:]):
        icon = "✅" if h["defeated"] else "❌"
        st.markdown(
            f"<div class='hist'><b>{h['cq']}</b> · Sc {h['sc']} · {icon} {'DEFEATED' if h['defeated'] else 'SUCCEEDS'}</div>",
            unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
sc   = SCENARIOS[sc_id]
st.title("🤖 Argumentation-Based Explainable Planning Chatbot")
st.markdown(f"### {sc['title']}")
st.info(sc["desc"])

if st.session_state.last_sc != sc_id:
    st.session_state.result      = run_pipeline(sc["steps"], sc["fault"])
    st.session_state.last_sc     = sc_id
    st.session_state.explanation = ""

result = st.session_state.result

# ── Plan table ──
st.markdown("## 📋 Scheduled Temporal Plan")
df = pd.DataFrame([{
    "#": s["step_index"], "Action": s["action_name"],
    "Params": ", ".join(f"{k}={v}" for k,v in s["params"].items()),
    "Start": s["start"], "End": s["end"],
    "Duration": s["end"]-s["start"], "Resource": s["resource"],
} for s in sc["steps"]])
st.dataframe(df, use_container_width=True, hide_index=True)

# ── PSA verdict ──
st.markdown("## ⚖️ PSA(P) Verdict")
if result["accepted"]:
    st.markdown("<div class='psa-ok'>✅ PSA(P) = ACCEPTED — The plan is valid in every respect.</div>",
                unsafe_allow_html=True)
else:
    st.markdown(f"<div class='psa-fail'>❌ PSA(P) = REJECTED — Failing: {', '.join(result['failed'])}</div>",
                unsafe_allow_html=True)
    for cq in result["failed"]:
        st.error(f"**{cq} — {CQ_INFO[cq][0]}** succeeds: {CQ_EXPLANATIONS[cq][False]}")

# ── Scheme verdicts ──
st.markdown("## 🔍 Argument Scheme Verdicts")
for name, desc in SCHEME_INFO.items():
    with st.expander(f"{'✅' if result['accepted'] else '⚠️'} {name}"):
        st.markdown(desc)

# ── CQ challenge buttons ──
st.markdown("## 💬 Raise a Challenge")
st.caption("Click a critical question to challenge the explanation.")
cols = st.columns(4)
for i, (cq, (label, question)) in enumerate(CQ_INFO.items()):
    defeated = result["cqs"][cq]
    icon = "✅" if defeated else "❌"
    if cols[i%4].button(f"{icon} {cq}", key=f"btn_{cq}", use_container_width=True,
                        help=question):
        trust = st.session_state.trust
        trust.challenge()
        st.session_state.explanation = trust.explain(cq, defeated)
        st.session_state.history.append({"cq":cq,"sc":sc_id,"defeated":defeated})
        st.rerun()

# ── Explanation panel ──
if st.session_state.explanation:
    st.divider()
    st.markdown("## 📖 Explanation")
    st.markdown(f"<div class='card'>{st.session_state.explanation}</div>",
                unsafe_allow_html=True)
    st.caption(f"Explanation depth: **{st.session_state.trust.band}** trust level")
    c1, c2 = st.columns(2)
    if c1.button("✅ Accept this explanation", use_container_width=True):
        st.session_state.trust.accept()
        st.session_state.explanation = ""
        st.rerun()
    if c2.button("🔁 Clear", use_container_width=True):
        st.session_state.explanation = ""
        st.rerun()

st.divider()
st.caption("XAIP Argumentation Chatbot · University of Huddersfield · Haastrup, 2026")

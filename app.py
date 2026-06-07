"""Timetable Scheduling App — Streamlit UI."""

import json
import streamlit as st
import pandas as pd
from models import Teacher, Subject, Section, Assignment, TimetableData, Grade, Cluster
from sample_data import create_sample_cluster_data
from solver import solve, DAY_NAMES
from llm import generate_constraint_code, build_data_summary
import db
import auth

st.set_page_config(page_title="Timetable Scheduler", page_icon="📅", layout="wide")

# ── Initialize Database ──────────────────────────────────────────────────────

db.init_db()

# ── Authentication Gate ──────────────────────────────────────────────────────

user = auth.require_auth()

# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"**Logged in as:** {user['username']} ({user['role']})")
    if st.button("Logout"):
        auth.logout()

    st.divider()
    st.header("Settings")
    api_key = st.secrets.get("OPENROUTER_API_KEY", "")
    if not api_key:
        st.warning("Set OPENROUTER_API_KEY in secrets.")
    llm_model = st.text_input("LLM Model", value="minimax/minimax-m3")

    # ── Admin: User Management ───────────────────────────────────────────────
    if auth.is_admin():
        st.divider()
        with st.expander("Manage Users"):
            users = db.list_users()
            for u in users:
                col1, col2 = st.columns([3, 1])
                col1.write(f"{u['username']} ({u['role']})")
                if u["username"] != "admin":
                    if col2.button("Delete", key=f"del_user_{u['id']}"):
                        db.delete_user(u["username"])
                        st.rerun()

            st.markdown("**Add User**")
            with st.form("add_user_form"):
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                new_role = st.selectbox("Role", ["user", "admin"])
                if st.form_submit_button("Add"):
                    if new_username and new_password:
                        if db.create_user(new_username, new_password, new_role):
                            st.success(f"User '{new_username}' created.")
                            st.rerun()
                        else:
                            st.error("Username already exists.")

# ── Project Selector ─────────────────────────────────────────────────────────

st.title("School Timetable Scheduler")

# Initialize project state
if "current_project_id" not in st.session_state:
    st.session_state.current_project_id = None
if "cluster" not in st.session_state:
    st.session_state.cluster = None
if "data" not in st.session_state:
    st.session_state.data = None
if "constraints" not in st.session_state:
    st.session_state.constraints = []
if "solutions" not in st.session_state:
    st.session_state.solutions = None
if "solve_status" not in st.session_state:
    st.session_state.solve_status = None
if "solve_error" not in st.session_state:
    st.session_state.solve_error = None
if "pending_code" not in st.session_state:
    st.session_state.pending_code = None
if "pending_text" not in st.session_state:
    st.session_state.pending_text = None

# List projects for this user (admin sees all)
if auth.is_admin():
    projects = db.list_projects()
else:
    projects = db.list_projects(owner=user["username"])

proj_options = {p["id"]: f"{p['name']} (by {p['owner_username']})" for p in projects}

col_proj, col_new = st.columns([3, 1])
with col_proj:
    if proj_options:
        selected_id = st.selectbox(
            "Select Project",
            options=list(proj_options.keys()),
            format_func=lambda x: proj_options[x],
            index=list(proj_options.keys()).index(st.session_state.current_project_id) if st.session_state.current_project_id in proj_options else 0,
        )
        if selected_id != st.session_state.current_project_id:
            # Load project
            proj = db.get_project(selected_id)
            st.session_state.current_project_id = selected_id
            if proj["data_json"]:
                st.session_state.cluster = Cluster.from_json(proj["data_json"])
                st.session_state.data = st.session_state.cluster.to_timetable_data()
                st.session_state.grade_names = [g.name for g in st.session_state.cluster.grades]
            else:
                st.session_state.cluster = None
                st.session_state.data = None
                st.session_state.grade_names = ["Class 9"]
            st.session_state.constraints = json.loads(proj["constraints_json"]) if proj["constraints_json"] else []
            st.session_state.solutions = None
            # Clear editor keys
            for key in list(st.session_state.keys()):
                if key.endswith("_editor"):
                    del st.session_state[key]
            st.rerun()
    else:
        st.info("No projects yet. Create one to get started.")
        selected_id = None

with col_new:
    st.markdown("&nbsp;")  # spacer
    with st.popover("New Project"):
        new_name = st.text_input("Project name", key="new_proj_name")
        if st.button("Create", key="create_proj_btn"):
            if new_name:
                pid = db.create_project(new_name, user["username"])
                st.session_state.current_project_id = pid
                st.session_state.cluster = None
                st.session_state.data = None
                st.session_state.constraints = []
                st.session_state.solutions = None
                st.rerun()

if st.session_state.current_project_id is None:
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_setup, tab_constraints, tab_results = st.tabs(["📋 Setup", "🔧 Constraints", "📊 Results"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: SETUP
# ══════════════════════════════════════════════════════════════════════════════

with tab_setup:
    st.header("Cluster & School Data Setup")

    if st.button("Load Sample Data (Grades 8-9)", type="secondary"):
        st.session_state.cluster = create_sample_cluster_data()
        st.session_state.data = st.session_state.cluster.to_timetable_data()
        st.session_state.grade_names = [g.name for g in st.session_state.cluster.grades]
        st.session_state.solutions = None
        st.session_state.constraints = []
        for key in list(st.session_state.keys()):
            if key.endswith("_editor"):
                del st.session_state[key]
        st.rerun()

    st.divider()

    # ── Cluster config ────────────────────────────────────────────────────────

    cluster = st.session_state.cluster

    col1, col2, col3 = st.columns(3)
    with col1:
        cluster_name = st.text_input("Cluster Name",
                                     value=cluster.name if cluster else "My Cluster")
    with col2:
        num_days = st.number_input("Working days/week", min_value=5, max_value=7,
                                   value=cluster.num_days if cluster else 6)
    with col3:
        num_periods = st.number_input("Periods/day", min_value=4, max_value=10,
                                      value=cluster.num_periods if cluster else 8)

    total_slots = num_days * num_periods
    st.info(f"Total slots per section per week: **{total_slots}**")

    st.divider()

    # ── Teachers (cluster-wide) ───────────────────────────────────────────────

    st.subheader("Teachers (shared across all grades)")

    if cluster:
        default_teachers = [{"Name": t.name} for t in cluster.teachers]
    else:
        default_teachers = [{"Name": "Teacher 1"}]

    teachers_df = st.data_editor(
        pd.DataFrame(default_teachers),
        num_rows="dynamic",
        key="teachers_editor",
        use_container_width=True,
    )

    st.divider()

    # ── Grade Management ──────────────────────────────────────────────────────

    st.subheader("Grades")

    if "grade_names" not in st.session_state:
        if cluster and cluster.grades:
            st.session_state.grade_names = [g.name for g in cluster.grades]
        else:
            st.session_state.grade_names = ["Class 9"]

    # Add/remove grade controls
    col_add, col_rem = st.columns(2)
    with col_add:
        with st.popover("Add Grade"):
            new_grade_name = st.text_input("Grade name", key="new_grade_input")
            if st.button("Add", key="add_grade_btn"):
                if new_grade_name and new_grade_name not in st.session_state.grade_names:
                    st.session_state.grade_names.append(new_grade_name)
                    st.rerun()
    with col_rem:
        if len(st.session_state.grade_names) > 1:
            grade_to_remove = st.selectbox("Remove grade", st.session_state.grade_names, key="remove_grade_select")
            if st.button("Remove", key="remove_grade_btn"):
                st.session_state.grade_names.remove(grade_to_remove)
                # Clean up editor keys for this grade
                for key in list(st.session_state.keys()):
                    if key.startswith(f"sections_{grade_to_remove}") or key.startswith(f"subjects_{grade_to_remove}") or key.startswith(f"assignments_{grade_to_remove}"):
                        del st.session_state[key]
                st.rerun()

    # ── Per-grade editing ─────────────────────────────────────────────────────

    # Build teacher name list for assignment dropdowns
    teacher_names_list = [str(row["Name"]).strip() for _, row in teachers_df.iterrows() if str(row["Name"]).strip()]

    # Store DataFrames returned by data_editor for use in Save handler
    grade_dataframes = {}

    for grade_idx, grade_name in enumerate(st.session_state.grade_names):
        with st.expander(f"**{grade_name}**", expanded=(grade_idx == 0)):
            # Find existing grade data
            existing_grade = None
            if cluster:
                for g in cluster.grades:
                    if g.name == grade_name:
                        existing_grade = g
                        break

            # Sections
            st.markdown("**Sections**")
            if existing_grade:
                default_secs = [{"Name": s.name} for s in existing_grade.sections]
            else:
                default_secs = [{"Name": f"{grade_name[-1]}A"}, {"Name": f"{grade_name[-1]}B"},
                                {"Name": f"{grade_name[-1]}C"}, {"Name": f"{grade_name[-1]}D"}]

            sec_df = st.data_editor(
                pd.DataFrame(default_secs),
                num_rows="dynamic",
                key=f"sections_{grade_name}_editor",
                use_container_width=True,
            )

            # Subjects
            st.markdown(f"**Subjects** (periods must sum to {total_slots})")
            if existing_grade:
                default_subjs = [{"Name": s.name, "Periods/Week": s.periods_per_week}
                                 for s in existing_grade.subjects]
            else:
                default_subjs = [
                    {"Name": "Mathematics", "Periods/Week": 7},
                    {"Name": "Science", "Periods/Week": 7},
                    {"Name": "English", "Periods/Week": 6},
                    {"Name": "Hindi", "Periods/Week": 5},
                ]

            subj_df = st.data_editor(
                pd.DataFrame(default_subjs),
                num_rows="dynamic",
                key=f"subjects_{grade_name}_editor",
                use_container_width=True,
            )

            if not subj_df.empty and "Periods/Week" in subj_df.columns:
                period_sum = int(subj_df["Periods/Week"].sum())
                if period_sum == total_slots:
                    st.success(f"Total: {period_sum} = {total_slots} ✓")
                else:
                    st.warning(f"Total: {period_sum} ≠ {total_slots}")

            # Assignments
            st.markdown("**Assignments** (who teaches what to whom)")
            st.caption("Enter teacher name and subject for each section assignment.")

            section_names_for_grade = [str(row["Name"]).strip() for _, row in sec_df.iterrows() if str(row["Name"]).strip()]
            subject_names_for_grade = [str(row["Name"]).strip() for _, row in subj_df.iterrows() if str(row["Name"]).strip()]

            if existing_grade and cluster:
                default_assigns = []
                for a in existing_grade.assignments:
                    t_name = next((t.name for t in cluster.teachers if t.id == a.teacher_id), "")
                    s_name = next((s.name for s in existing_grade.subjects if s.id == a.subject_id), "")
                    sec_name = next((s.name for s in existing_grade.sections if s.id == a.section_id), "")
                    default_assigns.append({"Teacher": t_name, "Subject": s_name, "Section": sec_name})
            else:
                default_assigns = [{"Teacher": "", "Subject": "", "Section": ""}]

            assign_df = st.data_editor(
                pd.DataFrame(default_assigns),
                num_rows="dynamic",
                key=f"assignments_{grade_name}_editor",
                use_container_width=True,
            )

            # Store for Save handler
            grade_dataframes[grade_name] = {
                "sections": sec_df,
                "subjects": subj_df,
                "assignments": assign_df,
            }

    st.divider()

    # ── Save & Build ──────────────────────────────────────────────────────────

    if st.button("Save & Build Timetable Data", type="primary"):
        try:
            # Build teachers (cluster-wide)
            teachers = []
            teacher_name_to_id = {}
            for i, row in teachers_df.iterrows():
                name = str(row["Name"]).strip()
                if name:
                    teachers.append(Teacher(id=i, name=name, subject_ids=[]))
                    teacher_name_to_id[name.lower()] = i

            # Build grades
            grades = []
            next_section_id = 0
            next_subject_id = 0

            for grade_idx, grade_name in enumerate(st.session_state.grade_names):
                gdf = grade_dataframes.get(grade_name, {})
                grade_sec_df = gdf.get("sections", pd.DataFrame())
                grade_subj_df = gdf.get("subjects", pd.DataFrame())
                grade_assign_df = gdf.get("assignments", pd.DataFrame())

                # Build sections
                sections = []
                section_name_to_id = {}
                for _, row in grade_sec_df.iterrows():
                    name = str(row["Name"]).strip()
                    if name:
                        sections.append(Section(id=next_section_id, name=name, grade_id=grade_idx))
                        section_name_to_id[name.lower()] = next_section_id
                        next_section_id += 1

                # Build subjects
                subjects = []
                subject_name_to_id_grade = {}
                for _, row in grade_subj_df.iterrows():
                    name = str(row["Name"]).strip()
                    periods = int(row["Periods/Week"])
                    if name:
                        subjects.append(Subject(id=next_subject_id, name=name, periods_per_week=periods))
                        subject_name_to_id_grade[name.lower()] = next_subject_id
                        next_subject_id += 1

                # Build assignments
                assignments = []
                for _, row in grade_assign_df.iterrows():
                    t_name = str(row.get("Teacher", "")).strip()
                    s_name = str(row.get("Subject", "")).strip()
                    sec_name = str(row.get("Section", "")).strip()
                    if not (t_name and s_name and sec_name):
                        continue

                    tid = teacher_name_to_id.get(t_name.lower())
                    sid = subject_name_to_id_grade.get(s_name.lower())
                    secid = section_name_to_id.get(sec_name.lower())

                    if tid is None:
                        st.warning(f"Teacher '{t_name}' not found in teacher list.")
                        continue
                    if sid is None:
                        st.warning(f"Subject '{s_name}' not found in {grade_name} subjects.")
                        continue
                    if secid is None:
                        st.warning(f"Section '{sec_name}' not found in {grade_name} sections.")
                        continue

                    assignments.append(Assignment(teacher_id=tid, subject_id=sid, section_id=secid))

                    # Update teacher's subject_ids
                    for t in teachers:
                        if t.id == tid and sid not in t.subject_ids:
                            t.subject_ids.append(sid)

                grades.append(Grade(
                    id=grade_idx,
                    name=grade_name,
                    subjects=subjects,
                    sections=sections,
                    assignments=assignments,
                ))

            # Build cluster
            new_cluster = Cluster(
                name=cluster_name,
                num_days=num_days,
                num_periods=num_periods,
                grades=grades,
                teachers=teachers,
            )

            # Validate each grade
            td = new_cluster.to_timetable_data()
            for grade in grades:
                for sec in grade.sections:
                    total = td.total_periods_for_section(sec.id)
                    if total != total_slots:
                        st.error(f"{grade.name} / {sec.name}: {total} periods assigned but needs {total_slots}.")
                        st.stop()

            st.session_state.cluster = new_cluster
            st.session_state.data = td
            st.session_state.solutions = None

            # Persist to DB
            db.save_project(
                st.session_state.current_project_id,
                data_json=new_cluster.to_json(),
                constraints_json=json.dumps(st.session_state.constraints),
            )

            total_secs = sum(len(g.sections) for g in grades)
            total_assigns = sum(len(g.assignments) for g in grades)
            st.success(f"Saved: {len(grades)} grade(s), {len(teachers)} teachers, "
                       f"{total_secs} sections, {total_assigns} assignments.")

        except Exception as e:
            st.error(f"Error building data: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: CONSTRAINTS
# ══════════════════════════════════════════════════════════════════════════════

with tab_constraints:
    st.header("Constraints")

    if st.session_state.data is None:
        st.warning("Please set up your school data in the Setup tab first.")
        st.stop()

    # Show hard constraints
    st.subheader("Built-in Constraints (always active)")
    st.markdown("""
    1. **One teacher per section per slot** — each section has exactly one teacher at any time
    2. **No teacher clashes** — a teacher cannot be in two sections at the same time (across all grades)
    3. **Subject hours met** — each subject gets exactly the required periods per week
    """)

    st.divider()

    # ── Custom Constraints ────────────────────────────────────────────────────

    st.subheader("Custom Constraints")
    st.caption("Type a constraint in plain English. The AI will generate the solver code.")

    constraint_text = st.text_area(
        "Describe your constraint",
        placeholder="e.g., Mrs. Sharma should not teach in the first period",
        key="constraint_input",
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        generate_btn = st.button("Generate Code", type="primary",
                                 disabled=not constraint_text or not api_key)
    with col2:
        if not api_key:
            st.caption("Set OPENROUTER_API_KEY in your Streamlit secrets")

    # Generate constraint code
    if generate_btn and constraint_text and api_key:
        with st.spinner("Generating constraint code..."):
            data_summary = build_data_summary(st.session_state.data, st.session_state.cluster)
            result = generate_constraint_code(
                constraint_text=constraint_text,
                data_summary=data_summary,
                api_key=api_key,
                model_name=llm_model,
            )
            if result["error"]:
                st.error(result["error"])
            else:
                st.session_state.pending_code = result["code"]
                st.session_state.pending_text = constraint_text

    # Show pending generated code
    if st.session_state.pending_code:
        st.markdown("**Generated Code:**")
        st.code(st.session_state.pending_code, language="python")

        col_accept, col_reject, col_regen = st.columns(3)
        with col_accept:
            if st.button("Accept", type="primary"):
                st.session_state.constraints.append({
                    "text": st.session_state.pending_text,
                    "code": st.session_state.pending_code,
                })
                st.session_state.pending_code = None
                st.session_state.pending_text = None
                st.session_state.solutions = None
                # Persist constraints
                db.save_project(
                    st.session_state.current_project_id,
                    constraints_json=json.dumps(st.session_state.constraints),
                )
                st.rerun()
        with col_reject:
            if st.button("Reject"):
                st.session_state.pending_code = None
                st.session_state.pending_text = None
                st.rerun()
        with col_regen:
            if st.button("Regenerate") and api_key:
                with st.spinner("Regenerating..."):
                    data_summary = build_data_summary(st.session_state.data, st.session_state.cluster)
                    result = generate_constraint_code(
                        constraint_text=st.session_state.pending_text,
                        data_summary=data_summary,
                        api_key=api_key,
                        model_name=llm_model,
                    )
                    if result["error"]:
                        st.error(result["error"])
                    else:
                        st.session_state.pending_code = result["code"]
                        st.rerun()

    st.divider()

    # ── Accepted Constraints ──────────────────────────────────────────────────

    st.subheader(f"Accepted Constraints ({len(st.session_state.constraints)})")

    if not st.session_state.constraints:
        st.caption("No custom constraints added yet. The solver will use only the built-in constraints.")
    else:
        for i, c in enumerate(st.session_state.constraints):
            with st.expander(f"#{i+1}: {c['text']}"):
                st.code(c["code"], language="python")
                if st.button("Delete", key=f"del_{i}"):
                    st.session_state.constraints.pop(i)
                    st.session_state.solutions = None
                    db.save_project(
                        st.session_state.current_project_id,
                        constraints_json=json.dumps(st.session_state.constraints),
                    )
                    st.rerun()

    st.divider()

    # ── Solve Button ──────────────────────────────────────────────────────────

    if st.button("Solve Timetable", type="primary", use_container_width=True):
        with st.spinner("Solving..."):
            constraint_codes = [c["code"] for c in st.session_state.constraints]
            result = solve(
                st.session_state.data,
                extra_constraints_code=constraint_codes if constraint_codes else None,
                max_solutions=5,
            )
            st.session_state.solutions = result["solutions"]
            st.session_state.solve_status = result["status"]
            st.session_state.solve_error = result["error"]

        if result["status"] in ("OPTIMAL", "FEASIBLE"):
            st.success(f"Found {len(result['solutions'])} solution(s)! Go to the Results tab.")
        elif result["status"] == "ERROR":
            st.error(f"Error: {result['error']}")
        else:
            st.error(f"Status: {result['status']}. {result['error'] or ''}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: RESULTS
# ══════════════════════════════════════════════════════════════════════════════

with tab_results:
    st.header("Timetable Results")

    if st.session_state.data is None:
        st.warning("Please set up your school data first.")
        st.stop()

    if st.session_state.solutions is None:
        st.info("No solutions yet. Go to the Constraints tab and click 'Solve Timetable'.")
        st.stop()

    if not st.session_state.solutions:
        st.error(f"Status: {st.session_state.solve_status}. {st.session_state.solve_error or ''}")
        st.stop()

    data = st.session_state.data
    cluster = st.session_state.cluster
    solutions = st.session_state.solutions

    st.success(f"Status: {st.session_state.solve_status} — {len(solutions)} solution(s) found")

    # ── Solution Selector ─────────────────────────────────────────────────────

    solution_idx = st.selectbox(
        "Select solution",
        range(len(solutions)),
        format_func=lambda i: f"Solution {i + 1}",
    )
    timetable = solutions[solution_idx]

    # ── View Mode ─────────────────────────────────────────────────────────────

    view_mode = st.radio("View by", ["Section", "Teacher"], horizontal=True)

    if view_mode == "Section":
        # Grade filter
        if cluster and len(cluster.grades) > 1:
            grade_names = [g.name for g in cluster.grades]
            selected_grade_name = st.selectbox("Select grade", grade_names)
            selected_grade = next(g for g in cluster.grades if g.name == selected_grade_name)
            section_list = selected_grade.sections
        else:
            section_list = data.sections

        section_names = [s.name for s in section_list]
        selected_section = st.selectbox("Select section", section_names)
        section_id = data.get_section_id(selected_section)

        # Build grid
        day_names = DAY_NAMES[:data.num_days]
        rows = []
        for p in range(data.num_periods):
            row = {"Period": f"P{p + 1}"}
            for d, day_name in enumerate(day_names):
                entry = timetable.get((section_id, d, p))
                if entry:
                    teacher_name, subject_name = entry
                    short_teacher = teacher_name.split()[-1]
                    row[day_name] = f"{subject_name}\n({short_teacher})"
                else:
                    row[day_name] = "—"
            rows.append(row)

        df = pd.DataFrame(rows).set_index("Period")
        st.dataframe(df, use_container_width=True, height=350)

    else:
        # Teacher view
        teacher_names = [t.name for t in data.teachers]
        selected_teacher = st.selectbox("Select teacher", teacher_names)
        teacher_id = data.get_teacher_id(selected_teacher)

        day_names = DAY_NAMES[:data.num_days]
        rows = []
        for p in range(data.num_periods):
            row = {"Period": f"P{p + 1}"}
            for d, day_name in enumerate(day_names):
                found = False
                for sec in data.sections:
                    entry = timetable.get((sec.id, d, p))
                    if entry and entry[0] == selected_teacher:
                        _, subject_name = entry
                        row[day_name] = f"{subject_name}\n({sec.name})"
                        found = True
                        break
                if not found:
                    row[day_name] = "Free"
            rows.append(row)

        df = pd.DataFrame(rows).set_index("Period")
        st.dataframe(df, use_container_width=True, height=350)

    st.divider()

    # ── CSV Export ────────────────────────────────────────────────────────────

    st.subheader("Export")

    all_rows = []
    if cluster:
        for grade in cluster.grades:
            for sec in grade.sections:
                for p in range(data.num_periods):
                    row = {"Grade": grade.name, "Section": sec.name, "Period": f"P{p + 1}"}
                    for d in range(data.num_days):
                        day_name = DAY_NAMES[d] if d < len(DAY_NAMES) else f"Day{d}"
                        entry = timetable.get((sec.id, d, p))
                        if entry:
                            teacher_name, subject_name = entry
                            row[day_name] = f"{subject_name} ({teacher_name})"
                        else:
                            row[day_name] = ""
                    all_rows.append(row)
    else:
        for sec in data.sections:
            for p in range(data.num_periods):
                row = {"Section": sec.name, "Period": f"P{p + 1}"}
                for d in range(data.num_days):
                    day_name = DAY_NAMES[d] if d < len(DAY_NAMES) else f"Day{d}"
                    entry = timetable.get((sec.id, d, p))
                    if entry:
                        teacher_name, subject_name = entry
                        row[day_name] = f"{subject_name} ({teacher_name})"
                    else:
                        row[day_name] = ""
                all_rows.append(row)

    export_df = pd.DataFrame(all_rows)
    csv = export_df.to_csv(index=False)

    st.download_button(
        "Download as CSV",
        csv,
        file_name="timetable.csv",
        mime="text/csv",
    )

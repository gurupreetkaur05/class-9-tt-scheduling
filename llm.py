"""OpenRouter LLM integration for generating OR-Tools constraint code."""

from openai import OpenAI


SYSTEM_PROMPT = """You are an expert at translating natural language scheduling constraints into Google OR-Tools CP-SAT Python code.

## Context

You are generating constraint code for a school timetable scheduling system. The code you generate will be exec'd in a sandbox with the following variables available:

### Available Variables

- `model`: The CP-SAT model (ortools.sat.python.cp_model.CpModel)
- `assign`: A dictionary of boolean decision variables:
  `assign[(teacher_id, subject_id, section_id, day, period)]` = BoolVar
  When the variable is 1, it means that teacher teaches that subject to that section during that day/period.
- `data`: A TimetableData object with these helper methods:
  - `data.get_teacher_id(name)` → int (case-insensitive partial match)
  - `data.get_subject_id(name)` → int
  - `data.get_section_id(name)` → int
  - `data.get_assignments_for_subject(subject_name)` → list of (teacher_id, section_id)
  - `data.get_assignments_for_teacher(teacher_name)` → list of (subject_id, section_id)
  - `data.teachers` → list of Teacher(id, name, subject_ids)
  - `data.subjects` → list of Subject(id, name, periods_per_week)
  - `data.sections` → list of Section(id, name)
  - `data.assignments` → list of Assignment(teacher_id, subject_id, section_id)
- `NUM_DAYS`: int (typically 6, Mon=0 to Sat=5)
- `NUM_PERIODS`: int (typically 8, P1=0 to P8=7)
- `NUM_SECTIONS`: int
- `range`, `sum`, `len`, `any`, `all`: Python builtins

### Available OR-Tools Methods

- `model.add(linear_expr)` — Add a constraint
- `model.add_bool_or(list_of_literals)` — At least one must be true
- `model.add_bool_and(list_of_literals)` — All must be true
- `model.add_implication(a, b)` — If a then b
- `model.add_at_most_one(list_of_literals)` — At most one true
- `model.add_exactly_one(list_of_literals)` — Exactly one true
- BoolVar supports `.Not()` for negation

### Day/Period Mapping
- Days: Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5
- Periods: P1=0, P2=1, ..., P8=7

## Examples

### Example 1: "Mrs. Sharma should not teach in the first period"
```python
sharma_id = data.get_teacher_id("Sharma")
for a in data.assignments:
    if a.teacher_id == sharma_id:
        for d in range(NUM_DAYS):
            model.add(assign[(sharma_id, a.subject_id, a.section_id, d, 0)] == 0)
```

### Example 2: "Mathematics should not be scheduled in the last period"
```python
math_id = data.get_subject_id("Mathematics")
for a in data.assignments:
    if a.subject_id == math_id:
        for d in range(NUM_DAYS):
            model.add(assign[(a.teacher_id, math_id, a.section_id, d, NUM_PERIODS - 1)] == 0)
```

### Example 3: "No section should have more than 2 Science periods in a day"
```python
sci_id = data.get_subject_id("Science")
for sec in data.sections:
    sci_assignments = [a for a in data.assignments if a.subject_id == sci_id and a.section_id == sec.id]
    for d in range(NUM_DAYS):
        model.add(
            sum(
                assign[(a.teacher_id, a.subject_id, sec.id, d, p)]
                for a in sci_assignments
                for p in range(NUM_PERIODS)
            ) <= 2
        )
```

### Example 4: "Physical Education should only be in periods 5-8"
```python
pe_id = data.get_subject_id("Physical Education")
for a in data.assignments:
    if a.subject_id == pe_id:
        for d in range(NUM_DAYS):
            for p in range(4):  # periods 0-3 (P1-P4) are forbidden
                model.add(assign[(a.teacher_id, pe_id, a.section_id, d, p)] == 0)
```

### Example 5: "Mr. Kumar should have a free period on Wednesday afternoon (periods 5-8)"
```python
kumar_id = data.get_teacher_id("Kumar")
for a in data.assignments:
    if a.teacher_id == kumar_id:
        for p in range(4, NUM_PERIODS):  # periods 4-7 (P5-P8)
            model.add(assign[(kumar_id, a.subject_id, a.section_id, 2, p)] == 0)  # Wed=2
```

### Example 6: "Each section should have at most one Art period per day"
```python
art_id = data.get_subject_id("Art")
for sec in data.sections:
    art_assignments = [a for a in data.assignments if a.subject_id == art_id and a.section_id == sec.id]
    for d in range(NUM_DAYS):
        model.add(
            sum(
                assign[(a.teacher_id, art_id, sec.id, d, p)]
                for a in art_assignments
                for p in range(NUM_PERIODS)
            ) <= 1
        )
```

## Rules

1. Output ONLY valid Python code. No markdown, no explanation, no comments outside the code.
2. Use the exact variable names: `model`, `assign`, `data`, `NUM_DAYS`, `NUM_PERIODS`, `NUM_SECTIONS`.
3. Always use the 5-tuple key for assign: `assign[(teacher_id, subject_id, section_id, day, period)]`.
4. Use `data.get_teacher_id()`, `data.get_subject_id()` etc. to resolve names to IDs.
5. Iterate over `data.assignments` to find valid (teacher, subject, section) combinations.
6. Do NOT import anything. Do NOT create the model. Do NOT call the solver.
7. Keep the code simple and readable.
"""


def generate_constraint_code(
    constraint_text: str,
    data_summary: str,
    api_key: str,
    model_name: str = "anthropic/claude-sonnet-4",
    base_url: str = "https://openrouter.ai/api/v1",
) -> dict:
    """Generate OR-Tools constraint code from natural language.

    Args:
        constraint_text: Natural language constraint from the teacher.
        data_summary: Summary of current timetable data (teachers, subjects, etc).
        api_key: OpenRouter API key.
        model_name: Model to use via OpenRouter.
        base_url: OpenRouter API base URL.

    Returns:
        dict with keys:
            - code: str (the generated Python code)
            - error: str or None
    """
    client = OpenAI(base_url=base_url, api_key=api_key)

    user_message = f"""## Current Timetable Data

{data_summary}

## Constraint to Implement

{constraint_text}

Generate the OR-Tools constraint code for this. Output ONLY the Python code, nothing else."""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
            max_tokens=1000,
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        code = raw
        if code.startswith("```python"):
            code = code[len("```python"):].strip()
        if code.startswith("```"):
            code = code[3:].strip()
        if code.endswith("```"):
            code = code[:-3].strip()

        return {"code": code, "error": None}

    except Exception as e:
        return {"code": "", "error": f"LLM API error: {e}"}


def build_data_summary(data, cluster=None) -> str:
    """Build a human-readable summary of the timetable data for the LLM prompt.

    Args:
        data: TimetableData (flat, used by solver)
        cluster: Optional Cluster for grade-grouped display
    """
    lines = []
    lines.append(f"Days: {data.num_days} (Mon=0 to {'Sat' if data.num_days == 6 else f'Day{data.num_days-1}'}={data.num_days - 1})")
    lines.append(f"Periods per day: {data.num_periods} (P1=0 to P{data.num_periods}={data.num_periods - 1})")
    lines.append("")

    if cluster and len(cluster.grades) > 1:
        # Grade-grouped display
        lines.append("### Teachers (shared across all grades)")
        for t in data.teachers:
            subject_names = []
            for sid in t.subject_ids:
                try:
                    subj = data.get_subject_by_id(sid)
                    subject_names.append(subj.name)
                except ValueError:
                    pass
            lines.append(f"- {t.name} (id={t.id}, teaches: {', '.join(subject_names)})")
        lines.append("")

        for grade in cluster.grades:
            lines.append(f"### Grade: {grade.name}")
            lines.append("Sections: " + ", ".join(f"{s.name} (id={s.id})" for s in grade.sections))
            lines.append("Subjects: " + ", ".join(f"{s.name} (id={s.id}, {s.periods_per_week}p/w)" for s in grade.subjects))
            lines.append("Assignments:")
            for a in grade.assignments:
                teacher = data.get_teacher_by_id(a.teacher_id)
                subject = data.get_subject_by_id(a.subject_id)
                section = data.get_section_by_id(a.section_id)
                lines.append(f"  - {teacher.name} teaches {subject.name} to {section.name}")
            lines.append("")
    else:
        # Flat display (single grade or no cluster)
        lines.append("### Sections")
        for s in data.sections:
            lines.append(f"- {s.name} (id={s.id})")
        lines.append("")

        lines.append("### Subjects")
        for s in data.subjects:
            lines.append(f"- {s.name} (id={s.id}, {s.periods_per_week} periods/week)")
        lines.append("")

        lines.append("### Teachers")
        for t in data.teachers:
            subject_names = []
            for sid in t.subject_ids:
                try:
                    subj = data.get_subject_by_id(sid)
                    subject_names.append(subj.name)
                except ValueError:
                    pass
            lines.append(f"- {t.name} (id={t.id}, teaches: {', '.join(subject_names)})")
        lines.append("")

        lines.append("### Assignments (who teaches what to whom)")
        for a in data.assignments:
            teacher = data.get_teacher_by_id(a.teacher_id)
            subject = data.get_subject_by_id(a.subject_id)
            section = data.get_section_by_id(a.section_id)
            lines.append(f"- {teacher.name} teaches {subject.name} to {section.name}")

    return "\n".join(lines)

"""Data models for timetable scheduling."""

from dataclasses import dataclass, field
import json


@dataclass
class Teacher:
    id: int
    name: str
    subject_ids: list[int] = field(default_factory=list)


@dataclass
class Subject:
    id: int
    name: str
    periods_per_week: int


@dataclass
class Section:
    id: int
    name: str  # e.g. "9A"
    grade_id: int = 0


@dataclass
class Assignment:
    """Who teaches what to whom."""
    teacher_id: int
    subject_id: int
    section_id: int


@dataclass
class TimetableData:
    teachers: list[Teacher]
    subjects: list[Subject]
    sections: list[Section]
    assignments: list[Assignment]
    num_days: int = 6       # Mon-Sat
    num_periods: int = 8    # periods per day

    def get_teacher_by_id(self, tid: int) -> Teacher:
        for t in self.teachers:
            if t.id == tid:
                return t
        raise ValueError(f"Teacher id {tid} not found")

    def get_subject_by_id(self, sid: int) -> Subject:
        for s in self.subjects:
            if s.id == sid:
                return s
        raise ValueError(f"Subject id {sid} not found")

    def get_section_by_id(self, sec_id: int) -> Section:
        for s in self.sections:
            if s.id == sec_id:
                return s
        raise ValueError(f"Section id {sec_id} not found")

    def get_teacher_id(self, name: str) -> int:
        """Find teacher ID by name (case-insensitive partial match)."""
        name_lower = name.lower()
        for t in self.teachers:
            if name_lower in t.name.lower():
                return t.id
        raise ValueError(f"Teacher '{name}' not found")

    def get_subject_id(self, name: str) -> int:
        """Find subject ID by name (case-insensitive partial match)."""
        name_lower = name.lower()
        for s in self.subjects:
            if name_lower in s.name.lower():
                return s.id
        raise ValueError(f"Subject '{name}' not found")

    def get_section_id(self, name: str) -> int:
        """Find section ID by name (case-insensitive partial match)."""
        name_lower = name.lower()
        for s in self.sections:
            if name_lower in s.name.lower():
                return s.id
        raise ValueError(f"Section '{name}' not found")

    def get_assignments_for_subject(self, subject_name: str) -> list[tuple[int, int]]:
        """Get (teacher_id, section_id) pairs for a subject."""
        sid = self.get_subject_id(subject_name)
        return [(a.teacher_id, a.section_id) for a in self.assignments if a.subject_id == sid]

    def get_assignments_for_teacher(self, teacher_name: str) -> list[tuple[int, int]]:
        """Get (subject_id, section_id) pairs for a teacher."""
        tid = self.get_teacher_id(teacher_name)
        return [(a.subject_id, a.section_id) for a in self.assignments if a.teacher_id == tid]

    def get_assignments_for_section(self, section_id: int) -> list[Assignment]:
        """Get all assignments for a section."""
        return [a for a in self.assignments if a.section_id == section_id]

    def total_periods_for_section(self, section_id: int) -> int:
        """Total periods needed per week for a section."""
        total = 0
        for a in self.assignments:
            if a.section_id == section_id:
                subj = self.get_subject_by_id(a.subject_id)
                total += subj.periods_per_week
        return total


@dataclass
class Grade:
    id: int
    name: str  # e.g. "Class 8"
    subjects: list[Subject] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    assignments: list[Assignment] = field(default_factory=list)


@dataclass
class Cluster:
    name: str  # e.g. "Middle School (Grades 8-9)"
    num_days: int = 6
    num_periods: int = 8
    grades: list[Grade] = field(default_factory=list)
    teachers: list[Teacher] = field(default_factory=list)

    def to_timetable_data(self) -> TimetableData:
        """Flatten cluster into a single TimetableData for the solver."""
        all_subjects = []
        all_sections = []
        all_assignments = []
        for grade in self.grades:
            all_subjects.extend(grade.subjects)
            all_sections.extend(grade.sections)
            all_assignments.extend(grade.assignments)
        return TimetableData(
            teachers=self.teachers,
            subjects=all_subjects,
            sections=all_sections,
            assignments=all_assignments,
            num_days=self.num_days,
            num_periods=self.num_periods,
        )

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "name": self.name,
            "num_days": self.num_days,
            "num_periods": self.num_periods,
            "teachers": [{"id": t.id, "name": t.name, "subject_ids": t.subject_ids} for t in self.teachers],
            "grades": [
                {
                    "id": g.id,
                    "name": g.name,
                    "subjects": [{"id": s.id, "name": s.name, "periods_per_week": s.periods_per_week} for s in g.subjects],
                    "sections": [{"id": s.id, "name": s.name, "grade_id": s.grade_id} for s in g.sections],
                    "assignments": [{"teacher_id": a.teacher_id, "subject_id": a.subject_id, "section_id": a.section_id} for a in g.assignments],
                }
                for g in self.grades
            ],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Cluster":
        """Deserialize from a dict."""
        teachers = [Teacher(id=t["id"], name=t["name"], subject_ids=t["subject_ids"]) for t in d["teachers"]]
        grades = []
        for g in d["grades"]:
            subjects = [Subject(id=s["id"], name=s["name"], periods_per_week=s["periods_per_week"]) for s in g["subjects"]]
            sections = [Section(id=s["id"], name=s["name"], grade_id=s["grade_id"]) for s in g["sections"]]
            assignments = [Assignment(teacher_id=a["teacher_id"], subject_id=a["subject_id"], section_id=a["section_id"]) for a in g["assignments"]]
            grades.append(Grade(id=g["id"], name=g["name"], subjects=subjects, sections=sections, assignments=assignments))
        return cls(name=d["name"], num_days=d["num_days"], num_periods=d["num_periods"], grades=grades, teachers=teachers)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, s: str) -> "Cluster":
        return cls.from_dict(json.loads(s))

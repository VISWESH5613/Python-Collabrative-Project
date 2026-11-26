# OptiSchedule - Conflict-Free Campus Timetable Generator
# Course: Computational Thinking and Programming (2026CSAE100)

import csv
import os

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
OUTPUT_DIR = "output"

DEFAULT_SLOTS = ["09:00-10:00", "10:00-11:00", "11:00-12:00", "01:00-02:00", "02:00-03:00"]
DEFAULT_ROOMS = ["Room-101", "Room-102", "CS-Lab"]
DEFAULT_CLASSES = ["CSE-Section-A", "CSE-Section-B"]
DEFAULT_SUBJECTS = [
    {"name": "Python Programming", "teacher": "Dr. Sharma", "type": "Theory", "hours_per_week": 3},
    {"name": "Python Lab", "teacher": "Dr. Sharma", "type": "Lab", "hours_per_week": 2},
    {"name": "Calculus", "teacher": "Prof. Verma", "type": "Theory", "hours_per_week": 3},
    {"name": "Digital Logic", "teacher": "Dr. Rao", "type": "Theory", "hours_per_week": 2},
]


# --- 1. DATA MODEL CLASSES ---
class Room:
    """Represents a classroom or laboratory."""

    def __init__(self, name):
        self.name = name

    def is_lab(self):
        return "lab" in self.name.lower()

    def __str__(self):
        return self.name


class Subject:
    """Represents a course subject with its assigned teacher and weekly hours."""

    def __init__(self, name, teacher, subject_type="Theory", hours_per_week=2):
        self.name = name
        self.teacher = teacher
        self.type = subject_type
        self.hours_per_week = hours_per_week

    def is_lab(self):
        return self.type.lower() == "lab"

    def __str__(self):
        return f"{self.name} ({self.teacher}, {self.type}, {self.hours_per_week}h)"


class Session:
    """Represents a single scheduled class session in a room."""

    def __init__(self, subject, room):
        self.subject = subject
        self.room = room

    def __str__(self):
        return f"{self.subject.name} [{self.room.name}]"


# --- 2. OPTISCHEDULE CLASS (CORE ENGINE & FEATURES) ---
class OptiSchedule:
    """Manages conflict-free timetable generation, queries, analytics, and export."""

    def __init__(self, slots, rooms, classes, subjects):
        self.slots = slots
        self.rooms = [r if isinstance(r, Room) else Room(r) for r in rooms]
        self.classes = classes
        self.subjects = [
            s if isinstance(s, Subject) else Subject(s["name"], s["teacher"], s["type"], s["hours_per_week"])
            for s in subjects
        ]
        self.timetable = {}
        self.unscheduled = []

    def generate(self):
        """Allocates classes without room or teacher clashes using set tracking."""
        self.timetable = {c: {d: {s: None for s in self.slots} for d in DAYS} for c in self.classes}
        booked_rooms, booked_teachers = set(), set()
        self.unscheduled = []

        for c_name in self.classes:
            for sub in self.subjects:
                needed = sub.hours_per_week
                for session_idx in range(needed):
                    day_order = [(session_idx + offset) % len(DAYS) for offset in range(len(DAYS))]
                    placed = False

                    for day_idx in day_order:
                        day = DAYS[day_idx]
                        if needed <= len(DAYS) and any(
                            self.timetable[c_name][day][s] and self.timetable[c_name][day][s].subject.name == sub.name
                            for s in self.slots
                        ):
                            continue

                        for slot in self.slots:
                            if self.timetable[c_name][day][slot] is not None or (day, slot, sub.teacher) in booked_teachers:
                                continue

                            free_rooms = [r for r in self.rooms if (day, slot, r.name) not in booked_rooms]
                            lab_rooms = [r for r in free_rooms if r.is_lab()]
                            room = lab_rooms[0] if (sub.is_lab() and lab_rooms) else (free_rooms[0] if free_rooms else None)

                            if room:
                                self.timetable[c_name][day][slot] = Session(sub, room)
                                booked_rooms.add((day, slot, room.name))
                                booked_teachers.add((day, slot, sub.teacher))
                                placed = True
                                break
                        if placed:
                            break

                    if not placed:
                        self.unscheduled.append((c_name, sub.name))

    def print_grid(self, title, rows):
        """Prints a compact weekly table for either a class or a teacher."""
        width = 16 + len(self.slots) * 20
        print("\n" + "=" * width)
        print(title.center(width))
        print("=" * width)
        print(f"{'Day':<11} | " + " | ".join(f"{s:<17}" for s in self.slots))
        print("-" * width)
        for day in DAYS:
            cells = [str(rows[day][s]) if rows[day][s] is not None else "FREE" for s in self.slots]
            print(f"{day:<11} | " + " | ".join(f"{cell:<17}" for cell in cells))
        print("=" * width)

    def view_teacher_schedule(self, teacher):
        """Builds and prints the weekly schedule for a selected teacher."""
        rows = {d: {s: "FREE" for s in self.slots} for d in DAYS}
        for d in DAYS:
            for s in self.slots:
                for c_name in self.classes:
                    entry = self.timetable[c_name][d][s]
                    if entry and entry.subject.teacher == teacher:
                        rows[d][s] = f"{c_name} [{entry.room.name}]"
                        break
        self.print_grid(f"TEACHER SCHEDULE: {teacher}", rows)

    def find_free_rooms(self, day, slot):
        """Finds unoccupied rooms for a chosen day and time slot."""
        occupied = {
            self.timetable[c][day][slot].room.name
            for c in self.classes if self.timetable[c][day][slot] is not None
        }
        free = [r.name for r in self.rooms if r.name not in occupied]
        print(f"\n[{day} | {slot}]")
        print(f"  Occupied : {', '.join(sorted(occupied)) or 'None'}")
        print(f"  Free     : {', '.join(free) or 'None available'}")

    def build_report(self):
        """Calculates slot/room utilization and returns a formatted summary string."""
        total_slots = len(self.classes) * len(DAYS) * len(self.slots)
        room_cap = len(self.rooms) * len(DAYS) * len(self.slots)
        filled, day_counts, room_usage = 0, {d: 0 for d in DAYS}, {r.name: 0 for r in self.rooms}

        for c in self.classes:
            for d in DAYS:
                for s in self.slots:
                    entry = self.timetable[c][d][s]
                    if entry is not None:
                        filled += 1
                        day_counts[d] += 1
                        if entry.room.name in room_usage:
                            room_usage[entry.room.name] += 1

        busiest = max(day_counts, key=day_counts.get)
        lines = [
            "=== TIMETABLE ANALYTICS REPORT ===",
            f"Scheduled Slots  : {filled}/{total_slots} ({(filled / total_slots * 100) if total_slots else 0:.1f}%)",
            f"Room Utilization : {(filled / room_cap * 100) if room_cap else 0:.1f}%",
            f"Busiest Day      : {busiest} ({day_counts[busiest]} sessions)",
            f"Unscheduled      : {len(self.unscheduled)}",
            "Room Usage       : " + ", ".join(f"{r} ({cnt}h)" for r, cnt in room_usage.items()),
        ]
        return "\n".join(lines)

    def export_files(self):
        """Exports timetable to CSV and analytics report to TXT."""
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        csv_path = os.path.join(OUTPUT_DIR, "master_timetable.csv")
        txt_path = os.path.join(OUTPUT_DIR, "schedule_report.txt")

        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Class", "Day", "Time_Slot", "Subject_And_Room"])
            for c in self.classes:
                for d in DAYS:
                    for s in self.slots:
                        entry = self.timetable[c][d][s]
                        writer.writerow([c, d, s, str(entry) if entry is not None else "FREE"])

        with open(txt_path, "w") as f:
            f.write(self.build_report() + "\n")
        return csv_path, txt_path


# --- 3. CLI APPLICATION CLASS ---
class TimetableApp:
    """Handles user interaction, setup prompts, and the main menu loop."""

    def __init__(self):
        self.scheduler = None

    @staticmethod
    def get_positive_int(prompt, default):
        """Reads a positive integer safely, returning default on invalid input."""
        raw = input(prompt).strip()
        if not raw:
            return default
        try:
            val = int(raw)
            return val if val > 0 else default
        except ValueError:
            print(f"[!] Invalid number '{raw}'. Using default ({default}).")
            return default

    @staticmethod
    def ask_list(label, defaults):
        """Lets the user keep default items or enter a comma-separated custom list."""
        print(f"\n{label} (Default: {', '.join(defaults)})")
        raw = input("  Enter comma-separated values or press Enter for default: ").strip()
        return [x.strip() for x in raw.split(",") if x.strip()] or list(defaults)

    @staticmethod
    def pick_item(title, items):
        """Displays a numbered list and returns the chosen item, or None if invalid."""
        print(f"\n{title}:")
        for idx, item in enumerate(items, 1):
            print(f"  {idx}. {item}")
        choice = input(f"Enter number (1-{len(items)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(items):
            return items[int(choice) - 1]
        print("[!] Invalid selection.")
        return None

    def get_user_inputs(self):
        """Collects time slots, rooms, classes, and subjects from the user."""
        print("\n=== TIMETABLE SETUP ===")
        if input("1. Quick Setup (Defaults)  2. Custom Setup [Default: 1]: ").strip() != "2":
            print("-> Sample defaults loaded!")
            rooms = [Room(r) for r in DEFAULT_ROOMS]
            subjects = [
                Subject(s["name"], s["teacher"], s["type"], s["hours_per_week"])
                for s in DEFAULT_SUBJECTS
            ]
            return list(DEFAULT_SLOTS), rooms, list(DEFAULT_CLASSES), subjects

        slots = self.ask_list("Time Slots", DEFAULT_SLOTS)
        rooms = [Room(r) for r in self.ask_list("Rooms & Labs", DEFAULT_ROOMS)]
        classes = self.ask_list("Classes / Sections", DEFAULT_CLASSES)

        if input("\nUse default 1st Year subjects? (y/n) [Default: y]: ").strip().lower() == "n":
            subjects = []
            count = self.get_positive_int("Number of subjects [Default: 2]: ", 2)
            for i in range(count):
                print(f"\nSubject {i + 1}:")
                name = input("  Name: ").strip() or f"Subject-{i + 1}"
                teacher = input("  Teacher: ").strip() or f"Teacher-{i + 1}"
                is_lab = input("  Is Lab? (y/n) [Default: n]: ").strip().lower() == "y"
                hours = self.get_positive_int("  Hours per week [Default: 2]: ", 2)
                subjects.append(Subject(name, teacher, "Lab" if is_lab else "Theory", hours))
        else:
            subjects = [
                Subject(s["name"], s["teacher"], s["type"], s["hours_per_week"])
                for s in DEFAULT_SUBJECTS
            ]

        return slots, rooms, classes, subjects

    def run(self):
        """Starts the interactive timetable generator menu."""
        print("OptiSchedule | Computational Thinking & Programming (2026CSAE100)")
        self.scheduler = OptiSchedule(*self.get_user_inputs())
        self.scheduler.generate()
        print(f"\n[+] Timetable ready! Unscheduled sessions: {len(self.scheduler.unscheduled)}")

        while True:
            print("\n1. View Class Timetable   2. View All Classes   3. Teacher Schedule")
            print("4. Find Free Rooms        5. Analytics Report   6. Export CSV & TXT")
            print("7. Change Inputs          8. Exit")
            choice = input("Choice (1-8): ").strip()

            if choice == "1":
                c = self.pick_item("Select Class", self.scheduler.classes)
                if c:
                    self.scheduler.print_grid(f"TIMETABLE: {c}", self.scheduler.timetable[c])
            elif choice == "2":
                for c in self.scheduler.classes:
                    self.scheduler.print_grid(f"TIMETABLE: {c}", self.scheduler.timetable[c])
            elif choice == "3":
                teachers = sorted({sub.teacher for sub in self.scheduler.subjects})
                teacher = self.pick_item("Select Teacher", teachers)
                if teacher:
                    self.scheduler.view_teacher_schedule(teacher)
            elif choice == "4":
                day = self.pick_item("Select Day", DAYS)
                slot = self.pick_item("Select Time Slot", self.scheduler.slots) if day else None
                if slot:
                    self.scheduler.find_free_rooms(day, slot)
            elif choice == "5":
                print("\n" + self.scheduler.build_report())
            elif choice == "6":
                c_path, t_path = self.scheduler.export_files()
                print(f"[+] Saved: {c_path} & {t_path}")
                
            elif choice == "7":
                self.scheduler = OptiSchedule(*self.get_user_inputs())
                self.scheduler.generate()
                print(f"[+] Regenerated! Unscheduled sessions: {len(self.scheduler.unscheduled)}")
            elif choice == "8":
                print("Goodbye!")
                break
            else:
                print("[!] Enter a valid option (1-8).")


if __name__ == "__main__":
    TimetableApp().run()

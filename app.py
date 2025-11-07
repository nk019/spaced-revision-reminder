import streamlit as st
from datetime import datetime, timedelta, time
from sqlalchemy.orm import Session
from models import Base, Task, Reminder
from db import engine, SessionLocal
from utils import parse_offsets_csv, build_series_datetimes, human_readable_status, split_series_change
from scheduler import start_scheduler
import pytz

Base.metadata.create_all(bind=engine)
start_scheduler()
st.set_page_config(page_title="Spaced Reminder", page_icon="⏰", layout="wide")
st.title("⏰ Spaced Reminder + To‑Do")
st.caption("Google Calendar‑like tasks with automatic spaced revisions")
def now_ist():
    tz = pytz.timezone("Asia/Kolkata")
    return datetime.now(tz)
with st.sidebar:
    st.header("Create / Edit Task")
    with st.form("task_form", clear_on_submit=False):
        mode = st.radio("Mode", ["Create new", "Edit existing"], horizontal=True)
        db = SessionLocal()
        try:
            task_options = {f"{t.id} — {t.title}": t.id for t in db.query(Task).order_by(Task.created_at.desc()).all()}
        finally:
            db.close()
        selected_task_id = None
        if mode == "Edit existing" and task_options:
            selected_label = st.selectbox("Choose a task", list(task_options.keys()))
            selected_task_id = task_options[selected_label]
        title = st.text_input("Title *", value="" if not selected_task_id else "")
        notes = st.text_area("Notes", value="" if not selected_task_id else "")
        date_input = st.date_input("Base Date *", value=now_ist().date())
        time_input = st.time_input("Base Time", value=time(9,0))
        offsets_csv = st.text_input("Spaced Offsets (days)", "1,3,7,21")
        notify_before = st.number_input("Notify minutes before", min_value=0, max_value=1440, value=0, step=5)
        apply_series_change = st.selectbox("If editing, apply to:", ["—", "This occurrence only", "Entire series"])
        submitted = st.form_submit_button("Save")
    if submitted:
        base_dt = datetime.combine(date_input, time_input).replace(second=0, microsecond=0)
        offsets = parse_offsets_csv(offsets_csv)
        if 0 not in offsets: offsets = [0] + offsets
        db = SessionLocal()
        try:
            if mode == "Create new":
                if not title.strip():
                    st.error("Title is required.")
                else:
                    task = Task(title=title.strip(), notes=notes.strip(), base_datetime=base_dt, offsets_csv=",".join(map(str, offsets[1:])))
                    db.add(task); db.commit(); db.refresh(task)
                    for dt in build_series_datetimes(base_dt, offsets):
                        db.add(Reminder(task_id=task.id, due_datetime=dt, notify_minutes_before=int(notify_before)))
                    db.commit(); st.success(f"Created task '{task.title}' with {len(offsets)} reminders.")
            else:
                if not selected_task_id: st.error("Choose a task to edit.")
                else:
                    task = db.get(Task, selected_task_id)
                    if not task: st.error("Task not found.")
                    else:
                        existing_offsets = [0] + parse_offsets_csv(task.offsets_csv)
                        new_offsets      = [0] + offsets
                        if apply_series_change == "Entire series":
                            task.title = title.strip() or task.title
                            task.notes = notes if notes is not None else task.notes
                            task.base_datetime = base_dt
                            task.offsets_csv = ",".join(map(str, new_offsets[1:]))
                            db.add(task)
                            db.query(Reminder).filter(Reminder.task_id==task.id).delete()
                            for dt in build_series_datetimes(task.base_datetime, new_offsets):
                                db.add(Reminder(task_id=task.id, due_datetime=dt, notify_minutes_before=int(notify_before)))
                            db.commit(); st.success(f"Updated entire series for '{task.title}'.")
                        elif apply_series_change == "This occurrence only":
                            task.title = title.strip() or task.title
                            task.notes = notes if notes is not None else task.notes
                            db.add(task)
                            db.add(Reminder(task_id=task.id, due_datetime=base_dt, notify_minutes_before=int(notify_before)))
                            db.commit(); st.success("Added/updated this single occurrence without changing the series.")
                        else:
                            st.info("Choose how to apply changes (this occurrence or entire series).")
        finally:
            db.close()
    st.divider()
    st.header("Filters")
    with st.form("filter_form"):
        f_status = st.multiselect("Status", ["pending", "done", "skipped"], default=["pending"])
        f_date = st.date_input("Show reminders on date", value=None)
        f_search = st.text_input("Search in title/notes")
        f_submit = st.form_submit_button("Apply")
db = SessionLocal()
try:
    st.subheader("Reminders")
    query = db.query(Reminder).join(Task).order_by(Reminder.due_datetime.asc())
    if 'f_submit' in locals() and f_submit:
        if f_status: query = query.filter(Reminder.status.in_(f_status))
        if f_date:
            start = datetime.combine(f_date, datetime.min.time())
            end   = datetime.combine(f_date, datetime.max.time())
            query = query.filter(Reminder.due_datetime >= start, Reminder.due_datetime <= end)
        if f_search:
            like = f"%{f_search}%"
            from sqlalchemy import or_
            query = query.filter(or_(Task.title.ilike(like), Task.notes.ilike(like)))
    reminders = query.all()
    cols = st.columns([2, 3, 2, 2, 2])
    cols[0].markdown("**Task**"); cols[1].markdown("**Notes**"); cols[2].markdown("**When**"); cols[3].markdown("**Status**"); cols[4].markdown("**Actions**")
    for rem in reminders:
        c = st.columns([2, 3, 2, 2, 2])
        c[0].write(rem.task.title)
        c[1].write(rem.task.notes or "—")
        c[2].write(rem.due_datetime.strftime("%Y-%m-%d %H:%M"))
        c[3].write(human_readable_status(rem))
        with c[4]:
            a1, a2, a3 = st.columns(3)
            if a1.button("✅", key=f"done-{rem.id}", help="Mark as done"):
                rem.status="done"; db.add(rem); db.commit(); st.experimental_rerun()
            if a2.button("⏭️", key=f"skip-{rem.id}", help="Mark as skipped"):
                rem.status="skipped"; db.add(rem); db.commit(); st.experimental_rerun()
            if a3.button("🗑️", key=f"del-{rem.id}", help="Delete this reminder"):
                db.delete(rem); db.commit(); st.experimental_rerun()
    st.divider()
    st.subheader("Task Series")
    tasks = db.query(Task).order_by(Task.created_at.desc()).all()
    for t in tasks:
        with st.expander(f"{t.title} — base {t.base_datetime.strftime('%Y-%m-%d %H:%M')} — offsets [{t.offsets_csv or '—'}]"):
            st.write(t.notes or "—")
            s1, s2, s3 = st.columns(3)
            if s1.button("Add next revision (+1 day)", key=f"addnext-{t.id}"):
                current_offsets = [0] + parse_offsets_csv(t.offsets_csv)
                next_off = (max(current_offsets) + 1) if current_offsets else 1
                new_offsets = [0] + sorted(set(current_offsets + [next_off]))
                t.offsets_csv = ",".join(map(str, new_offsets[1:]))
                next_dt = t.base_datetime + timedelta(days=next_off)
                db.add(Reminder(task_id=t.id, due_datetime=next_dt)); db.add(t); db.commit(); st.experimental_rerun()
            if s2.button("Regenerate series (keep done/skip)", key=f"regen-{t.id}"):
                offs = [0] + parse_offsets_csv(t.offsets_csv)
                existing_times = {r.due_datetime for r in t.reminders}
                for o in offs:
                    dt = t.base_datetime + timedelta(days=o)
                    if dt not in existing_times:
                        db.add(Reminder(task_id=t.id, due_datetime=dt))
                db.commit(); st.experimental_rerun()
            if s3.button("Delete entire series", key=f"deltask-{t.id}"):
                db.delete(t); db.commit(); st.experimental_rerun()
finally:
    db.close()
st.caption("Tip: For spaced repetition, a common pattern is 1,3,7,21,60,120 days. Adjust as needed.")

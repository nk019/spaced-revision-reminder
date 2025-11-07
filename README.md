# Spaced Reminder App (Streamlit + APScheduler + SQLite)

## Setup
```bash
pip install -r requirements.txt
streamlit run app.py
```
Optional email notifications: copy `.env.example` to `.env` and fill SMTP values.

## Spaced scheduling
- Create a task with your *base date/time* (day 0).
- Enter day offsets like: `1,3,7,21` — the app also ensures there's a day-0 reminder.
- Edit a single occurrence or the entire series later.
- Mark reminders as Done/Skipped. Delete individual reminders or entire series.

## Notes
- Desktop notifications via `plyer` (needs a notification daemon on Linux).
- The app checks due reminders every 60 seconds in the background.

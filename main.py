from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import requests
import json
from datetime import timedelta, date, datetime
from dotenv import load_dotenv
import os

load_dotenv()

endpoint = os.getenv('endpoint')
groupname = os.getenv('groupname')

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


class ScheduleRequest(BaseModel):
    gruppa: str
    beginweek: int
    endweek: int
    combine_subgroups: bool

def get_current_week(start_date=date(2024, 9, 2)):
    current_date = datetime.now().date()
    delta = current_date - start_date
    current_week = delta.days // 7 + 1
    return current_week

def get_schedule(gruppa, beginweek, endweek):
    url = endpoint
    payload = {
        "gruppa": gruppa,
        "beginweek": beginweek,
        "endweek": endweek
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        print(f"Запрос отправлен на {url} с данными: {payload}")
        print(f"Ответ от сервера: {response.status_code}, {response.text}")

        if response.status_code == 504:
            raise HTTPException(status_code=504, detail="Ошибка: Gateway Timeout (504)")

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Ошибка при получении данных: {response.status_code}")

        return response.json()

    except Exception as e:
        print(f"Ошибка в get_schedule: {e}")
        raise e


def get_dates_by_week_day_and_pair(beginweek, endweek, dayweek, para):
    start_date = date(2024, 9, 2)
    dates = []

    lesson_time = {
        1: "08:45-10:20",
        2: "10:30-12:05",
        3: "12:15-13:50",
        4: "14:35-16:10",
        5: "16:20-17:55",
        6: "18:05-19:40",
        7: "19:50-21:15"
    }

    for week in range(beginweek, endweek + 1):
        days_offset = (week - 1) * 7 + (dayweek - 1)
        lesson_date = start_date + timedelta(days=days_offset)
        date_str = lesson_date.strftime("%d.%m")
        time_str = lesson_time.get(para, "Неизвестное время")
        dates.append((date_str, time_str, week))

    return dates


def sort_lessons_by_date(lessons):
    return sorted(lessons, key=lambda lesson: (
        lesson["BEGINWEEK"], lesson["DAYWEEK"], lesson["PARA"]
    ))


def generate_markdown_table(schedule, combine_subgroups):
    subjects = {}

    for lesson in schedule:
        subject = lesson["NDISC"]
        podgruppa = lesson["PODGRUPPA"] or "Общая"

        if combine_subgroups:
            podgruppa = "Общая"

        if subject not in subjects:
            subjects[subject] = {}

        vidzanat = lesson["NVIDZANAT"]
        if vidzanat not in subjects[subject]:
            subjects[subject][vidzanat] = {}

        if podgruppa not in subjects[subject][vidzanat]:
            subjects[subject][vidzanat][podgruppa] = []

        subjects[subject][vidzanat][podgruppa].append(lesson)

    md_output = []

    for subject, lessons_by_type in subjects.items():
        md_output.append(f"## {subject}")

        for vidzanat, lessons_by_podgruppa in lessons_by_type.items():
            if vidzanat == "лекция":
                type_name = "Лекции"
            elif vidzanat == "практическое занятие":
                type_name = "Практики"
            elif vidzanat == "лаб.работа":
                type_name = "Лабораторные работы"
            else:
                type_name = "Другие"

            md_output.append(f"### {type_name}")

            for podgruppa, lessons in lessons_by_podgruppa.items():
                if not combine_subgroups and podgruppa != "Общая" and len(lessons_by_podgruppa) > 1:
                    md_output.append(f"#### Подгруппа {podgruppa}")

                md_output.append("| №  | Дата  | Время | Кабинет | Преподаватель | Неделя |")
                md_output.append("|----|-------|-------|---------|---------------|--------|")

                sorted_lessons = sort_lessons_by_date(lessons)

                for lesson_counter, lesson in enumerate(sorted_lessons, 1):
                    dates = get_dates_by_week_day_and_pair(lesson["BEGINWEEK"], lesson["ENDWEEK"], lesson["DAYWEEK"], lesson["PARA"])

                    for date_str, time_str, week in dates:
                        aud = lesson["AUD"] if lesson["AUD"] != "-" else "-"
                        teacher = lesson.get("FIO", "Неизвестно")
                        md_output.append(f"| {lesson_counter} | {date_str} | {time_str} | {aud} | {teacher} | {week} |")

    return "\n".join(md_output)


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    current_week = get_current_week()
    return templates.TemplateResponse("schedule.html", {
        "request": request, 
        "gruppa": groupname, 
        "beginweek": 1, 
        "endweek": 1, 
        "combine_subgroups": False,
        "current_week": current_week
    })

@app.post("/schedule", response_class=HTMLResponse)
async def get_schedule_route(schedule_request: ScheduleRequest):
    try:
        print(f"Получены данные: {schedule_request}")
        
        schedule = []
        for week in range(schedule_request.beginweek, schedule_request.endweek + 1):
            week_schedule = get_schedule(schedule_request.gruppa, week, week)
            print(f"Неделя {week}: {week_schedule}")
            schedule.extend(week_schedule)

        markdown_content = generate_markdown_table(schedule, schedule_request.combine_subgroups)
        print(f"Сгенерирован Markdown: {markdown_content}")

        return markdown_content

    except Exception as e:
        print(f"Ошибка: {e}")
        raise HTTPException(status_code=500, detail=str(e))
